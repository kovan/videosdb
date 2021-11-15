
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

    async def _check_for_new_videos(self):

        self.yt_api = await YoutubeAPI.create(settings.YOUTUBE_KEY)
        # in seconds, for warnings, in prod this does nothing:
        asyncio.get_running_loop().slow_callback_duration = 3

        try:
            async with TaskGatherer():
                video_ids = await self._sync_db_with_youtube()
            if not "DEBUG" in os.environ:
                async with TaskGatherer():  # separate so that it uses remaining quota
                    await self._fill_related_videos(video_ids)
        except YoutubeAPI.QuotaExceededError as e:
            logger.exception(e)

        async with TaskGatherer():
            # create_task(self._fill_transcripts())
            create_task(self.db.update_last_updated())

    async def _sync_db_with_youtube(self):

        async def _process_video(playlist_item):
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
                    if e.video_id.response.status_code == 429:
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

            video, (transcript, transcript_status) = await asyncio.gather(
                self.yt_api.get_video_info(video_id),
                _download_transcript(video_id)
            )
            if not video:
                return

            custom_attrs = dict()
            custom_attrs["slug"] = uuslug.slugify(
                video["snippet"]["title"])
            custom_attrs["descriptionTrimmed"] = _description_trimmed(
                video["snippet"]["description"])
            custom_attrs["durationSeconds"] = isodate.parse_duration(
                video["contentDetails"]["duration"]).total_seconds()
            custom_attrs["transcript"] = transcript
            custom_attrs["transcript_status"] = transcript_status

            video["videosdb"] = custom_attrs

            create_task(self.db.db.collection("videos").document(
                video_id).set(video, merge=True))

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

            if exclude_playlist:
                async for item in self.yt_api.list_playlist_items(playlist_id):
                    create_task(_process_video(item))
                return

            await self.db.set("playlists", playlist["id"], playlist)

            item_count = 0
            last_updated = date(1, 1, 1)
            async for item in self.yt_api.list_playlist_items(playlist_id):
                item_count += 1
                item_date = isodate.parse_date(
                    item["snippet"]["publishedAt"])

                if item_date > last_updated:
                    last_updated = item_date

                items_col = self.db.db.collection("playlists").document(
                    playlist["id"]).collection("playlist_items")

                create_task(self.db.set(items_col, item["id"], item))

            # custom attributes:
            custom_attrs = dict()
            custom_attrs["slug"] = uuslug.slugify(
                playlist["snippet"]["title"])
            custom_attrs["playlistItemsCount"] = item_count
            custom_attrs["lastUpdated"] = isodate.date_isoformat(
                last_updated)
            playlist["videosdb"] = custom_attrs

            create_task(self.db.set("playlists", playlist["id"], playlist))

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

    # async def _fill_transcripts(self):
    #     logger.info("Filling transcripts...")
    #     videos_col = self.db.db.collection("videos")
    #     query = videos_col.where(
    #         "videosdb.transcript_status", "not-in", ["downloaded", "unavailable"]).order_by("videosdb.transcript_status")
    #     res = await query.get()

    #     async for video_doc in query.stream():
    #         video = video_doc.to_dict()
    #         video_id = video["id"]
    #         video
    #         try:
    #             video["videosdb"]["transcript"] = get_video_transcript(
    #                 video_id)
    #             video["videosdb"]["transcript_status"] = "downloaded"
    #             logger.info(
    #                 "Transcription downloaded for video: " + str(video_id))
    #         except youtube_transcript_api.TooManyRequests as e:
    #             logger.warn(e)
    #             video["videosdb"]["transcript_status"] = "pending"
    #             break
    #         except youtube_transcript_api.CouldNotRetrieveTranscript as e:
    #             if e.video_id.response.status_code == 429:
    #                 video["videosdb"]["transcript_status"] = "pending"
    #                 logger.warn(e)
    #             else:
    #                 logger.info(
    #                     "Transcription not available for video: " + str(video_id))
    #                 video["videosdb"]["transcript_status"] = "unavailable"
    #         finally:
    #             create_task(videos_col.document(
    #                 video_id).set(video, merge=True))
