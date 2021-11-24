
from abc import abstractmethod
from datetime import date, datetime
import asyncio
import functools
import logging
import os
import isodate
import re
import uuslug

from google.cloud import firestore
import youtube_transcript_api
from aiostream import stream


from .youtube_api import YoutubeAPI, get_video_transcript

logger = logging.getLogger(__name__)

YT_CHANNEL_NAME = os.environ.get("YT_CHANNEL_NAME", "Sadhguru")
YT_CHANNEL_ID = os.environ.get("YT_CHANNEL_ID", "UCcYzLCs3zrQIBVHYA1sK2sw")


async def asyncgenerator(item):
    yield item


class DB:

    @classmethod
    async def create(cls):
        obj = cls()
        obj.db = firestore.AsyncClient()

        # initialize meta table:
        doc_ref = obj.db.collection("meta").document("meta")
        doc = await doc_ref.get()
        if not doc.exists or "videoIds" not in doc.to_dict():
            await doc_ref.set({"videoIds": list()})
        return obj

    async def set(self, collection, id, item):
        if type(collection) == str:
            collection = self.db.collection(collection)

        item_ref = collection.document(id)

        logger.debug("Writing item to db: " + str(id))

        return await item_ref.set(item)

    async def add_video_id_to_video_index(self, video_id):
        await self.db.collection("meta").document("meta").update({
            "videoIds": firestore.ArrayUnion([video_id])
        })

        # async def list_video_ids(self):
        #     video_ids = []
        #     async for video_doc in self.db.collection("videos").stream():
        #         video_ids.append(video_doc.get("id"))
        #     return video_ids

        # async def increase_video_counter(self, video_count):

        #     # because Firestore doesn't have something like SELECT COUNT(*)

        #     await self.db.collection("meta").document(
        #         "meta").update({
        #             "videoCount": firestore.FieldValue.increment(1)
        #         })

    async def update_last_updated(self):
        return await self.db.collection("meta").document(
            "meta").set({"lastUpdated": datetime.now().isoformat()}, merge=True)

    async def add_playlist_to_video(self, video_id, playlist):
        await self.db.collection("videos").document(video_id).update({
            "videosdb.playlists": firestore.ArrayUnion([playlist])
        })


class TaskGatherer():
    def __init__(self):
        self.tasks = dict()

    async def __aenter__(self):
        return self

    def create_task(self, key, coroutine):
        return self.tasks.setdefault(
            key, asyncio.create_task(coroutine, name=str(key)))

    async def gather(self):
        return await asyncio.gather(*self.tasks.values())

    async def __aexit__(self, type, value, traceback):
        return await self.gather()


class Downloader:

    # PUBLIC: -------------------------------------------------------------

    def check_for_new_videos(self):
        logging.getLogger("asyncio").setLevel(logging.WARNING)

        logger.info("Sync start")
        asyncio.run(self._check_for_new_videos())
        logger.info("Sync finished")


# PRIVATE: -------------------------------------------------------------------


    async def _check_for_new_videos(self):

        self.api = await YoutubeAPI.create()
        self.db = await DB.create()
        # in seconds, for warnings, in prod this does nothing:
        asyncio.get_running_loop().slow_callback_duration = 3

        try:
            await self._sync_db_with_youtube()
        except YoutubeAPI.QuotaExceededError as e:
            logger.exception(e)

        await self.db.update_last_updated()

        # wait for pending tasks to finish:
        await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})

    async def _sync_db_with_youtube(self):

        channel_id = YT_CHANNEL_ID
        channel_info = await self.api.get_channel_info(
            channel_id)

        logger.info("Processing channel: " +
                    str(channel_info["snippet"]["title"]))

        all_uploads_playlist_id = channel_info["contentDetails"]["relatedPlaylists"]["uploads"]

        playlist_ids = stream.merge(
            self.api.list_channnelsection_playlist_ids(channel_id),
            self.api.list_channel_playlist_ids(channel_id),
        )
        if not "DEBUG" in os.environ:
            playlist_ids = stream.merge(asyncgenerator(
                all_uploads_playlist_id), playlist_ids)

        global_video_ids = {
            "processed": set(),
            "valid": set()
        }

        async with playlist_ids.stream() as streamer:
            async with _PlaylistProcessor(
                    self.db, self.api, global_video_ids) as pp:
                async for id in streamer:
                    await pp.enqueue_playlist(id)

        if not "DEBUG" in os.environ:
            # separate so that it uses remaining quota
            await self._fill_related_videos(global_video_ids["valid"])

    async def _fill_related_videos(self, video_ids):

        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")

        async with TaskGatherer() as tg:
            for video_id in video_ids:
                for related in await self.api.get_related_videos(video_id):
                    # for now skip videos from other channels:
                    if "snippet" in related and related["snippet"]["channelId"] \
                            != YT_CHANNEL_ID:
                        continue

                    collection = self.db.db.collection("videos").document(video_id)\
                        .collection("related_videos")
                    tg.create_task(related["id"]["videoId"], self.db.set(
                        collection, related["id"]["videoId"], related))

                    logger.info("Added new related videos to video %s" %
                                (video_id))


class _BaseProcessor(TaskGatherer):
    def __init__(self, db, api):
        self.db = db
        self.api = api
        super().__init__()


class _VideoProcessor(_BaseProcessor):
    def __init__(self, db, api):
        super().__init__(db, api)

    @staticmethod
    async def _download_transcript(video_id):
        try:
            transcript = await asyncio.to_thread(
                get_video_transcript, video_id)

            logger.info(
                "Transcription downloaded for video: " + str(video_id))
            return transcript, "downloaded"
        except youtube_transcript_api.TooManyRequests as e:
            logger.warn(e)
            return None, "pending"
        except youtube_transcript_api.CouldNotRetrieveTranscript as e:
            # weird but that's how the lib works:
            if (hasattr(e, "video_id")
                and hasattr(e.video_id, "response")
                    and e.video_id.response.status_code == 429):
                logger.warn(e)
                return None, "pending"
            else:
                logger.info(
                    "Transcription not available for video: " + str(video_id))
                return None, "unavailable"

    @ staticmethod
    def _description_trimmed(description):
        if not description:
            return
        match = re.search("#Sadhguru", description)
        if match and match.start() != -1:
            return description[:match.start()]
        return description

    async def _create_video(self, playlist_item):

        video_id = playlist_item["snippet"]["resourceId"]["videoId"]

        # some playlists include videos from other channels
        # for now exclude those videos
        # in the future maybe exclude whole playlist
        if playlist_item["snippet"]["channelId"] != YT_CHANNEL_ID:
            return

        video = await self.api.get_video_info(video_id)
        if not video:
            return

        old_video_doc = await self.db.db.collection("videos").document(video_id).get()

        custom_attrs = dict()

        if old_video_doc.exists:
            old_video = old_video_doc.to_dict()
            if (not "transcript_status" in old_video["videosdb"]
                    or old_video["videosdb"]["transcript_status"] == "pending"):
                transcript, new_status = await self._download_transcript(video_id)
                custom_attrs["transcript_status"] = new_status
                if transcript:
                    custom_attrs["transcript"] = transcript

        custom_attrs["slug"] = uuslug.slugify(
            video["snippet"]["title"])
        custom_attrs["descriptionTrimmed"] = self._description_trimmed(
            video["snippet"]["description"])
        custom_attrs["durationSeconds"] = isodate.parse_duration(
            video["contentDetails"]["duration"]).total_seconds()

        video["videosdb"] = custom_attrs
        video["snippet"]["publishedAt"] = isodate.parse_datetime(
            video["snippet"]["publishedAt"])
        for stat, value in video["statistics"].items():
            video["statistics"][stat] = int(value)

        await self.db.db.collection("videos").document(
            video_id).set(video)

        await self.db.add_video_id_to_video_index(video_id)

        logger.info("Processed video: " + video_id)

        return video

    async def enqueue_video(self, playlist_item):

        if "DEBUG" in os.environ and len(self.tasks) > 100:
            return

        video_id = playlist_item["snippet"]["resourceId"]["videoId"]
        if video_id in self.tasks:
            return

        self.create_task(video_id, self._create_video(playlist_item))


class _PlaylistProcessor(_BaseProcessor):
    def __init__(self, db, api, global_video_ids):
        self.global_video_ids = global_video_ids
        super().__init__(db, api)

    async def _process_playlist(self, playlist_id):

        playlist = await self.api.get_playlist_info(playlist_id)
        if playlist["snippet"]["channelTitle"] != YT_CHANNEL_NAME:
            return

        if playlist["snippet"]["title"] == "Liked videos" or \
                playlist["snippet"]["title"] == "Popular uploads":
            return

        logger.info("Found playlist: %s (ID: %s)" % (
                    str(playlist["snippet"]["title"]), playlist["id"]))

        video_processor = _VideoProcessor(self.db, self.api)
        async for item in self.api.list_playlist_items(playlist_id):
            video_id = item["snippet"]["resourceId"]["videoId"]
            if video_id in self.global_video_ids["processed"]:
                continue

            self.global_video_ids["processed"].add(video_id)
            await video_processor.enqueue_video(item)

        exclude_playlist = playlist["snippet"]["title"] == "Uploads from " + \
            playlist["snippet"]["channelTitle"]

        if exclude_playlist:
            await video_processor.gather()
            return

        playlist["videosdb"] = dict()
        playlist["videosdb"]["slug"] = uuslug.slugify(
            playlist["snippet"]["title"])

        video_count = 0
        last_updated = None

        for video in await video_processor.gather():
            if not video:
                continue

            self.global_video_ids["valid"].add(video["id"])
            playlist_trimmed = {
                "id": playlist["id"],
                "slug": playlist["videosdb"]["slug"],
                "title": playlist["snippet"]["title"]
            }
            asyncio.create_task(
                self.db.add_playlist_to_video(video["id"], playlist_trimmed))

            video_count += 1
            video_date = video["snippet"]["publishedAt"]
            if not last_updated or video_date > last_updated:
                last_updated = video_date

        playlist["videosdb"]["videoCount"] = video_count
        playlist["videosdb"]["lastUpdated"] = last_updated

        await self.db.set("playlists", playlist["id"], playlist)

    async def enqueue_playlist(self, playlist_id):
        if playlist_id in self.tasks:
            return

        if "DEBUG" in os.environ and len(self.tasks) > 10:
            return

        self.create_task(playlist_id, self._process_playlist(playlist_id))
