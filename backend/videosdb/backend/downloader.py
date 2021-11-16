
from datetime import date, datetime
import asyncio
import logging
import os
import isodate
import re
import uuslug

from google.cloud import firestore
import youtube_transcript_api
from aiostream import stream
from django.conf import settings
from asyncio import create_task

from .youtube_api import YoutubeAPI, get_video_transcript

logger = logging.getLogger(__name__)


class DB:
    def __init__(self):
        self.db = firestore.AsyncClient()

    async def set(self, collection, id, item):
        if type(collection) == str:
            collection = self.db.collection(collection)

        item_ref = collection.document(id)

        logger.debug("Writing item to db: " + str(id))

        return await item_ref.set(item)

    async def list_video_ids(self):
        video_ids = []
        async for video_doc in self.db.collection("videos").stream():
            video_ids.append(video_doc.get("id"))
        return video_ids

    async def update_video_counter(self, video_count):
        # "hack" to list documents fast an cheaply,
        # because Firestore doesn't have something like SELECT COUNT(*)

        return await self.db.collection("meta").document(
            "meta").set({"videoCount": video_count}, merge=True)

    async def update_last_updated(self):
        return await self.db.collection("meta").document(
            "meta").set({"lastUpdated": datetime.now().isoformat()}, merge=True)


class TaskGatherer:
    async def __aenter__(self):
        pass

    async def __aexit__(self, type, value, traceback):
        await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})


class Downloader:

    # PUBLIC: -------------------------------------------------------------

    def __init__(self):
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        self.db = DB()

    def check_for_new_videos(self):

        logger.info("Sync start")
        asyncio.run(self._check_for_new_videos())
        logger.info("Sync finished")


# PRIVATE: -------------------------------------------------------------------


    class _Results():
        def __init__(self):
            self.lock = asyncio.Lock()
            self.video_ids = set()
            self.playlist_ids = set()
            self.videos_to_playlist_ids = dict()

    async def _check_for_new_videos(self):

        self.yt_api = await YoutubeAPI.create(settings.YOUTUBE_KEY)
        # in seconds, for warnings, in prod this does nothing:
        asyncio.get_running_loop().slow_callback_duration = 3

        try:
            async with TaskGatherer():
                results = await self._sync_db_with_youtube()
            if not "DEBUG" in os.environ:
                async with TaskGatherer():  # separate so that it uses remaining quota
                    await self._fill_related_videos(results.video_ids)
        except YoutubeAPI.QuotaExceededError as e:
            logger.exception(e)

        await self.db.update_last_updated()

    async def _sync_db_with_youtube(self):

        async def _process_video(results, playlist_item):

            async def _create_video(playlist_item):

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
                        if hasattr(e.video_id, "response") and e.video_id.response.status_code == 429:
                            logger.warn(e)
                            return None, "pending"
                        else:
                            logger.info(
                                "Transcription not available for video: " + str(video_id))
                            return None, "unavailable"

                def _description_trimmed(description):
                    if not description:
                        return
                    match = re.search(
                        settings.TRUNCATE_DESCRIPTION_AFTER, description)
                    if match and match.start() != -1:
                        return description[:match.start()]
                    return description

                video_id = playlist_item["snippet"]["resourceId"]["videoId"]

                # some playlists include videos from other channels
                # for now exclude those videos
                # in the future maybe exclude whole playlist
                if playlist_item["snippet"]["channelId"] != settings.YOUTUBE_CHANNEL["id"]:
                    return

                video, old_video_doc = await asyncio.gather(
                    self.yt_api.get_video_info(video_id),
                    self.db.db.collection("videos").document(video_id).get()
                )
                if not video:
                    return

                custom_attrs = dict()

                if old_video_doc.exists:
                    old_video = old_video_doc.to_dict()
                    if (not "transcript_status" in old_video
                            or old_video["transcript_status"] == "pending"):
                        transcript, new_status = await _download_transcript(video_id)
                        custom_attrs["transcript_status"] = new_status
                        if transcript:
                            custom_attrs["transcript"] = transcript

                custom_attrs["slug"] = uuslug.slugify(
                    video["snippet"]["title"])
                custom_attrs["descriptionTrimmed"] = _description_trimmed(
                    video["snippet"]["description"])
                custom_attrs["durationSeconds"] = isodate.parse_duration(
                    video["contentDetails"]["duration"]).total_seconds()

                video["videosdb"] = custom_attrs

                await self.db.db.collection("videos").document(
                    video_id).set(video)

                logger.debug("Processed video: " + video_id)

            if "DEBUG" in os.environ and len(results.video_ids) > 100:
                return

            video_id = playlist_item["snippet"]["resourceId"]["videoId"]

            async with results.lock:
                if video_id in results.video_ids:
                    created = True
                else:
                    created = False
                    results.video_ids.add(video_id)

            if not created:
                await _create_video(playlist_item)

            return video_id

        async def _process_playlist(results, playlist_id):
            async with results.lock:
                if playlist_id in results.playlist_ids:
                    return
                else:
                    results.playlist_ids.add(playlist_id)

            if "DEBUG" in os.environ and len(results.playlist_ids) > 10:
                return

            playlist = await self.yt_api.get_playlist_info(playlist_id)
            if playlist["snippet"]["channelTitle"] != settings.YOUTUBE_CHANNEL["name"]:
                return

            if playlist["snippet"]["title"] == "Liked videos" or \
                    playlist["snippet"]["title"] == "Popular uploads":
                return

            logger.info("Found playlist: %s (ID: %s)" % (
                        str(playlist["snippet"]["title"]), playlist["id"]))

            exclude_playlist = playlist["snippet"]["title"] == "Uploads from " + \
                playlist["snippet"]["channelTitle"]

            if exclude_playlist:
                tasks = []
                async for item in self.yt_api.list_playlist_items(playlist_id):
                    tasks.append(create_task(_process_video(results, item)))
                return await asyncio.gather(*tasks)

            await self.db.set("playlists", playlist["id"], playlist)

            # this goes before call to _process_video, so that slug is stored with the video:
            playlist["videosdb"] = dict()
            playlist["videosdb"]["slug"] = uuslug.slugify(
                playlist["snippet"]["title"])

            item_count = 0
            last_updated = date(1, 1, 1)
            tasks = []
            async for item in self.yt_api.list_playlist_items(playlist_id):
                video_id = item["snippet"]["resourceId"]["videoId"]
                item_count += 1
                item_date = isodate.parse_date(
                    item["snippet"]["publishedAt"])

                if item_date > last_updated:
                    last_updated = item_date
                async with results.lock:
                    results.videos_to_playlist_ids.get(
                        video_id, list()).append(playlist)
                task = create_task(_process_video(results, item))
                tasks.append(task)

            playlist["videosdb"]["videoCount"] = item_count
            playlist["videosdb"]["lastUpdated"] = isodate.date_isoformat(
                last_updated)

            await self.db.set("playlists", playlist["id"], playlist)
            return await asyncio.gather(*tasks)

        async def asyncgenerator(item):
            if "DEBUG" in os.environ:
                return
            yield item

        channel_id = settings.YOUTUBE_CHANNEL["id"]
        channel_info = await self.yt_api.get_channel_info(
            channel_id)

        logger.info("Processing channel: " +
                    str(channel_info["snippet"]["title"]))

        all_uploads_playlist_id = channel_info["contentDetails"]["relatedPlaylists"]["uploads"]

        playlist_ids = stream.merge(
            self.yt_api.list_channnelsection_playlist_ids(channel_id),
            self.yt_api.list_channel_playlist_ids(channel_id),
            asyncgenerator(all_uploads_playlist_id),
        )

        results = Downloader._Results()

        playlist_tasks = []
        async with playlist_ids.stream() as streamer:
            async for id in streamer:
                playlist_tasks.append(create_task(
                    _process_playlist(results, id)))

        await asyncio.gather(*playlist_tasks)

        async with results.lock:
            for video_id, playlists in results.videos_to_playlist_ids.items():
                for playlist in playlists:
                    create_task(self.db.db.collection("videos").document(
                        video_id).update({"playlists": firestore.ArrayUnion([playlist])}))

        return results

    async def _fill_related_videos(self, video_ids):

        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")

        for video_id in video_ids:
            for related in await self.yt_api.get_related_videos(video_id):
                # for now skip videos from other channels:
                if "snippet" in related and related["snippet"]["channelId"] \
                        != settings.YOUTUBE_CHANNEL["id"]:
                    continue

                collection = self.db.db.collection("videos").document(video_id)\
                    .collection("related_videos")
                create_task(self.db.set(
                    collection, related["id"]["videoId"], related))

                logger.info("Added new related videos to video %s" %
                            (video_id))
