import asyncio
import logging
import os

from google.cloud import firestore
from django.db import transaction
import youtube_transcript_api
from aiostream import async_, stream
from django.conf import settings
from videosdb.models import PersistentVideoData, Playlist, Tag, Video
from asgiref.sync import sync_to_async, async_to_sync


from .youtube_api import YoutubeAPI

logger = logging.getLogger(__name__)


class DB:
    def __init__(self):
        self.db = firestore.AsyncClient()

    async def set(self, collection, id, item, deferred=False):
        if type(collection) == str:
            collection = self.db.collection(collection)

        item_doc = collection.document(id)
        item_ref = await item_doc.get(["etag"])

        # not modified
        if item_ref.exists and item_ref.get("etag") == item["etag"]:
            return

        logger.debug("Writing item to db: " + str(id))

        if deferred:
            asyncio.create_task(item_doc.set(item))
        else:
            await item_doc.set(item)

    async def add_playlist_to_db(self, playlist, playlist_items):
        await self.set("playlists", playlist["id"], playlist)

        for item in playlist_items:
            items_col = self.db.collection("playlists").document(
                playlist["id"]).collection("playlist_items")

            await self.set(items_col, item["id"], item)


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

    async def _check_for_new_videos(self):

        self.yt_api = await YoutubeAPI.create(settings.YOUTUBE_KEY)
        # in seconds, for warnings, in prod this does nothing:
        asyncio.get_running_loop().slow_callback_duration = 3

        try:
            await self._sync_db_with_youtube()
            await self._fill_related_videos()
        except YoutubeAPI.YoutubeAPIError as e:
            # this usually raises when YT API quota has been exeeced (HTTP code 403)
            if e.status != 403:
                raise e
            else:
                logger.exception(e)

        await self._fill_transcripts()

    async def _sync_db_with_youtube(self):

        async def _process_video(playlist_item):
            video_id = playlist_item["snippet"]["resourceId"]["videoId"]
            if video_id in processed_videos:
                return
            if "DEBUG" in os.environ and len(processed_videos) > 100:
                return

            processed_videos.add(video_id)

            # some playlists include videos from other channels
            # for now exclude those videos
            # in the future maybe exclude whole playlist
            if playlist_item["snippet"]["channelId"] != settings.YOUTUBE_CHANNEL["id"]:
                return

            video = await self.yt_api.get_video_info(video_id)
            if not video:
                return

            await self.db.set("videos", video_id, video, True)

            logger.debug("Processing video: " + video_id)

        async def _process_playlist(playlist_id):
            if playlist_id in processed_playlists:
                return
            if "DEBUG" in os.environ and len(processed_playlists) > 100:
                return

            processed_playlists.add(playlist_id)

            playlist = await self.yt_api.get_playlist_info(playlist_id)
            if playlist["snippet"]["channelTitle"] != settings.YOUTUBE_CHANNEL["name"]:
                return

            if playlist["snippet"]["title"] == "Liked videos" or \
                    playlist["snippet"]["title"] == "Popular uploads":
                return

            logger.info("Found playlist: %s (ID: %s)" % (
                        str(playlist["snippet"]["title"]), playlist["id"]))

            playlist_items = [item async for item in self.yt_api.list_playlist_items(playlist_id)]

            if playlist["snippet"]["title"] != "Uploads from " + \
                    playlist["snippet"]["channelTitle"]:

                await self.db.add_playlist_to_db(playlist, playlist_items)

            for playlist_item in playlist_items:
                asyncio.create_task(_process_video(playlist_item))

        async def asyncgenerator(item):
            yield item

        channel_id = settings.YOUTUBE_CHANNEL["id"]
        channel_info = await self.yt_api.get_channel_info(
            channel_id)

        logger.info("Processing channel: " +
                    str(channel_info["snippet"]["title"]))

        all_uploads_playlist_id = channel_info["contentDetails"]["relatedPlaylists"]["uploads"]

        playlist_ids = stream.merge(
            asyncgenerator(all_uploads_playlist_id),
            self.yt_api.list_channnelsection_playlist_ids(channel_id),
            self.yt_api.list_channel_playlist_ids(channel_id)
        )

        processed_videos = set()  # just not to not process same video twice
        processed_playlists = set()  # same

        async with playlist_ids.stream() as streamer:
            async for id in streamer:
                asyncio.create_task(_process_playlist(id))

        await asyncio.gather(*asyncio.all_tasks() - {asyncio.current_task()})

    async def _fill_related_videos(self):

        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")
        async for video in self.db.db.collection("videos").stream():
            video_id = video.get("id")
            for related in await self.yt_api.get_related_videos(video_id):
                # for now skip videos from other channels:
                if "snippet" in related and related["snippet"]["channelId"] \
                        != settings.YOUTUBE_CHANNEL["id"]:
                    continue

                collection = self.db.db.collection("videos").document(video_id)\
                    .collection("related_videos")
                await self.db.set(collection, related["id"]["videoId"], related)

                logger.info("Added new related videos to video %s" %
                            (video_id))

    async def _fill_transcripts(self):
        logger.info("Filling transcripts.")
        async for video in self.db.db.collection("videos").stream():
            video_id = video.get("id")
            video_data_ref = self.db.db.collection(
                "persistent_video_datas").document(video_id)

            video_data_doc = await video_data_ref.get()

            video_data = video_data_doc.to_dict() if video_data_doc.exists else dict()

            if video_data.get("transcript") or video_data.get("transcript_available") is not None:
                continue
            try:
                video_data["transcript"] = self.yt_api.get_video_transcript(
                    video_id)
                video_data["transcript_available"] = True
                logger.info(
                    "Transcription downloaded for video: " + str(video_id))
            except youtube_transcript_api.TooManyRequests as e:
                logger.warn(e)
                # leave None so that it retries later
                video_data["transcript_available"] = None
                break
            except youtube_transcript_api.CouldNotRetrieveTranscript as e:
                logger.info(
                    "Transcription not available for video: " + str(video_id))
                video_data["transcript_available"] = False
            finally:
                await video_data_ref.set(video_data, merge=True)
