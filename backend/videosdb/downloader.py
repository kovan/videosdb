

from async_generator import aclosing
import anyio
from datetime import date, datetime
import asyncio

import logging
import os
import isodate
import re
from slugify import slugify


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

    async def add_video_id_to_video_index(self, video_id):
        await self.db.collection("meta").document("meta").update({
            "videoIds": firestore.ArrayUnion([video_id])
        })

    async def regenerate_video_index(self):
        ids = []
        async for video in self.db.collection("videos").stream():
            ids.append(video.to_dict()["id"])

        await self.db.collection("meta").document("meta").update({
            "videoIds": ids
        })

    async def update_last_updated(self):
        return await self.db.collection("meta").document(
            "meta").set({"lastUpdated": datetime.now().isoformat()}, merge=True)

    async def add_playlist_to_video(self, video_id, playlist):
        await self.db.collection("videos").document(video_id).update({
            "videosdb.playlists": firestore.ArrayUnion([playlist])
        })

    async def ensure_all_videos_belong_to_channel(self):
        async for video in self.db.collection("videos").stream():
            video_obj = video.to_dict()
            if video_obj["snippet"]["channelId"] != YT_CHANNEL_ID:
                print("Channel mismatch, expected %s, found %s" %
                      (YT_CHANNEL_ID, video_obj["snippet"]["channelId"]))
                await self.db.collection("videos").document(video_obj["id"]).delete()


class Downloader:

    # PUBLIC: -------------------------------------------------------------

    def check_for_new_videos(self):
        logger.info("Sync start")
        anyio.run(self.check_for_new_videos_async)
        logger.info("Sync finished")

    async def check_for_new_videos_async(self):
        self.api = await YoutubeAPI.create()
        self.db = await DB.create()

        try:
            await self._start()

            if not "DEBUG" in os.environ:
                # separate so that it uses remaining quota
                await self._fill_related_videos()
        except YoutubeAPI.QuotaExceededError as e:
            logger.exception(e)
        finally:
            await self.api.aclose()
        await self.db.update_last_updated()

    async def _start(self):
        video_sender, video_receiver = anyio.create_memory_object_stream()
        playlist_sender, playlist_receiver = anyio.create_memory_object_stream()
        async with anyio.create_task_group() as nursery:
            nursery.start_soon(self._playlist_retriever, playlist_sender)
            nursery.start_soon(self._playlist_processor,
                               playlist_receiver, video_sender)
            nursery.start_soon(self._video_processor, video_receiver)

    async def _playlist_retriever(self, playlist_sender):
        channel_id = YT_CHANNEL_ID
        channel_info = await self.api.get_channel_info(
            channel_id)

        logger.info("Processing channel: " +
                    str(channel_info["snippet"]["title"]))

        all_uploads_playlist_id = channel_info["contentDetails"]["relatedPlaylists"]["uploads"]

        if "DEBUG" in os.environ:
            playlist_ids = stream.iterate(
                self.api.list_channnelsection_playlist_ids(channel_id)
            )

        else:
            playlist_ids = stream.merge(
                asyncgenerator(all_uploads_playlist_id),
                self.api.list_channnelsection_playlist_ids(channel_id),
                self.api.list_channel_playlist_ids(channel_id)
            )

        with playlist_sender:
            async with aclosing(playlist_ids.stream()) as aiter:
                async for playlist_id in aiter:
                    await playlist_sender.send(playlist_id)

    async def _playlist_processor(self, playlist_receiver, video_sender):
        processed_playlist_ids = set()
        with video_sender:
            async with anyio.create_task_group() as nursery:
                async for playlist_id in playlist_receiver:
                    if playlist_id in processed_playlist_ids:
                        continue
                    nursery.start_soon(
                        self._process_playlist, playlist_id, video_sender)

                    processed_playlist_ids.add(playlist_id)

    async def _video_processor(self, video_receiver):
        processed_video_ids = set()
        async with anyio.create_task_group() as nursery:
            async for video_id, playlist_id in video_receiver:
                if video_id not in processed_video_ids:
                    result = await self._create_video(video_id)
                    if result:
                        processed_video_ids.add(video_id)

                if playlist_id and video_id in processed_video_ids:
                    await self.db.add_playlist_to_video(video_id, playlist_id)

    async def _process_playlist(self, playlist_id, video_sender):
        playlist = await self.api.get_playlist_info(playlist_id)
        if playlist["snippet"]["channelTitle"] != YT_CHANNEL_NAME:
            return

        playlist = playlist if playlist["snippet"]["title"] != "Uploads from " + \
            playlist["snippet"]["channelTitle"] else None

        items = []
        async for item in self.api.list_playlist_items(playlist_id):
            if item["snippet"]["channelId"] != YT_CHANNEL_ID:
                continue
            video_id = item["snippet"]["resourceId"]["videoId"]
            items.append(item)
            await video_sender.send((video_id, playlist_id))

        if playlist:
            await self._create_playlist(playlist, items)

    async def _create_playlist(self, playlist, items):
        video_count = 0
        last_updated = None

        for item in items:
            video_count += 1
            video_date = isodate.parse_datetime(
                item["snippet"]["publishedAt"])
            if not last_updated or video_date > last_updated:
                last_updated = video_date

        playlist["videosdb"] = dict()
        playlist["videosdb"]["slug"] = slugify(
            playlist["snippet"]["title"])
        playlist["videosdb"]["videoCount"] = video_count
        playlist["videosdb"]["lastUpdated"] = last_updated

        await self.db.db.collection("playlists").document(playlist["id"]).set(playlist)
        logger.info("Created playlist: " + playlist["snippet"]["title"])

    async def _create_video(self, video_id):

        video = await self.api.get_video_info(video_id)
        if not video:
            return
        # some playlists include videos from other channels
        # for now exclude those videos
        # in the future maybe exclude whole playlist

        if video["snippet"]["channelId"] != YT_CHANNEL_ID:
            return

        old_video_doc = await self.db.db.collection("videos").document(video_id).get()

        custom_attrs = dict()

        if (not old_video_doc.exists or
            not "transcript_status" in old_video_doc.to_dict()["videosdb"] or
                old_video_doc.to_dict()["videosdb"]["transcript_status"] == "pending"):
            transcript, new_status = await self._download_transcript(video_id)
            custom_attrs["transcript_status"] = new_status
            if transcript:
                custom_attrs["transcript"] = transcript

        custom_attrs["slug"] = slugify(
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
            video_id).set(video, merge=True)

        await self.db.add_video_id_to_video_index(video_id)

        logger.info("Created video: " + video["snippet"]["title"])

        return video

    async def _fill_related_videos(self):

        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")

        async with anyio.create_task_group() as tg:
            meta_doc = await self.db.db.collection("meta").document("meta").get()
            for video_id in meta_doc.to_dict()["videoIds"]:
                for related in await self.api.get_related_videos(video_id):
                    # for now skip videos from other channels:
                    if "snippet" in related and related["snippet"]["channelId"] \
                            != YT_CHANNEL_ID:
                        continue

                    await self.db.db.collection("videos").document(video_id).update({
                        "videosdb.related_videos": firestore.ArrayUnion([related["id"]["videoId"]])
                    })

                    logger.info("Added new related videos to video %s" %
                                (video_id))

    async def _download_transcript(self, video_id):
        try:
            transcript = await anyio.to_thread.run_sync(
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
