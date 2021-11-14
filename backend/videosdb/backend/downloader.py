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

        await item_ref.set(item)

    async def list_video_ids(self):
        video_ids = []
        async for video_doc in self.db.collection("videos").stream():
            video_ids.append(video_doc.get("id"))
        return video_ids


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


    async def _check_for_new_videos(self):

        self.yt_api = await YoutubeAPI.create(settings.YOUTUBE_KEY)
        # in seconds, for warnings, in prod this does nothing:
        asyncio.get_running_loop().slow_callback_duration = 3

        try:
            async with TaskGatherer():
                video_ids = await self._sync_db_with_youtube()

            async with TaskGatherer():
                await self._fill_related_videos(video_ids)
        except YoutubeAPI.QuotaExceededError as e:
            logger.exception(e)

        video_ids = await self.db.list_video_ids()
        async with TaskGatherer():
            await self._fill_transcripts(video_ids)

    async def _sync_db_with_youtube(self):

        async def _process_video(playlist_item):
            def _description_trimmed(description):
                if description:
                    return
                match = re.search(
                    settings.TRUNCATE_DESCRIPTION_AFTER, description)
                if match and match.start() != -1:
                    return description[:match.start()]
                return description

            video_id = playlist_item["snippet"]["resourceId"]["videoId"]
            if video_id in processed_videos:
                return
            if "DEBUG" in os.environ and len(processed_videos) > 10:
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

            # custom attributes:
            video["videosdb"] = {}
            video["videosdb"]["slug"] = uuslug.slugify(
                video["snippet"]["title"])
            video["videosdb"]["description_trimmed"] = _description_trimmed(
                video["snippet"]["description"])
            video["videosdb"]["duration_seconds"] = isodate.parse_duration(
                video["contentDetails"]["duration"]).total_seconds()

            create_task(self.db.set("videos", video_id, video))

            logger.debug("Processed video: " + video_id)

        async def _process_playlist(playlist_id):
            if playlist_id in processed_playlists:
                return
            if "DEBUG" in os.environ and len(processed_playlists) > 10:
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

            exclude_playlist = playlist["snippet"]["title"] == "Uploads from " + \
                playlist["snippet"]["channelTitle"]

            if not exclude_playlist:
                playlist["slug"] = uuslug.slugify(playlist["snippet"]["title"])
                await self.db.set("playlists", playlist["id"], playlist)

            async for item in self.yt_api.list_playlist_items(playlist_id):
                create_task(_process_video(item))
                if exclude_playlist:
                    continue

                items_col = self.db.db.collection("playlists").document(
                    playlist["id"]).collection("playlist_items")

                create_task(self.db.set(items_col, item["id"], item))

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
                create_task(_process_playlist(id))

        return processed_videos

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

    async def _fill_transcripts(self, video_ids):
        logger.info("Filling transcripts...")
        for video_id in video_ids:
            video_data_ref = self.db.db.collection(
                "persistent_video_datas").document(video_id)

            video_data_doc = await video_data_ref.get()

            video_data = video_data_doc.to_dict() if video_data_doc.exists else dict()

            if video_data.get("transcript") or video_data.get("transcript_available") is not None:
                continue
            try:
                video_data["transcript"] = get_video_transcript(video_id)
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
                create_task(video_data_ref.set(video_data, merge=True))
