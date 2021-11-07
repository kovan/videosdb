import asyncio
import logging


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

    async def add_or_update(self, collection, item):
        if type(collection) == str:
            collection = self.db.collection(collection)

        logger.debug("Writing item to db: " + str(item["id"]))
        item_doc = collection.document(item["id"])
        item_ref = await item_doc.get(["etag"])

        # not modified
        if item_ref.exists and item_ref.get("etag") == item["etag"]:
            logger.debug("Item %s Not modified" % item["id"])
            return

        await item_doc.set(item)

    async def add_playlist_to_db(self, playlist, playlist_items):
        await self.add_or_update("playlists", playlist)

        async for item in playlist_items:
            items_col = self.db.collection("playlists").document(
                playlist["id"]).collection("playlist_items")

            self.add_or_update(items_col, item)


class Downloader:

    # PUBLIC: -------------------------------------------------------------

    def __init__(self):
        logging.getLogger("asyncio").setLevel(logging.WARNING)
        self.db = DB()

    def download_one(self, youtube_id):
        self.enqueue_videos([youtube_id])

    def download_all(self):
        all = Video.objects.all()
        self.enqueue_videos([v.youtube_id for v in all])

    def check_for_new_videos(self):

        with transaction.atomic():
            Video.objects.all().delete()
            Playlist.objects.all().delete()
            Tag.objects.all().delete()

            logger.info("Sync start")
            self._check_for_new_videos()  # this is async
            logger.info("Sync finished")

            for data in PersistentVideoData.objects.all():
                try:
                    video = Video.objects.get(youtube_id=data.youtube_id)
                    video.data = data
                    video.save()
                except Video.DoesNotExist:
                    pass

        self._fill_related_videos()
        self._fill_transcripts()


# PRIVATE: -------------------------------------------------------------------

    @async_to_sync
    async def _check_for_new_videos(self):

        self.yt_api = await YoutubeAPI.create(settings.YOUTUBE_KEY)

        try:
            await self._sync_db_with_youtube()

        except YoutubeAPI.YoutubeAPIError as e:
            # this usually raises when YT API quota has been exeeced (HTTP code 403)
            if e.status != 403:
                raise e
            else:
                logger.exception(e)

    async def _sync_db_with_youtube(self):

        async def _process_video(playlist_item, playlist):
            video_id = playlist_item["snippet"]["resourceId"]["videoId"]
            if video_id in processed_videos:
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

            await self.db.add_or_update("videos", video)

            logger.debug("Processing video: " + video_id)

        async def _process_playlist(playlist_id):
            if playlist_id in processed_playlists:
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

            playlist_items = self.yt_api.list_playlist_items(playlist_id)

            await self.db.add_playlist_to_db(playlist, playlist_items)

            if playlist["snippet"]["title"] == "Uploads from " + \
                    playlist["snippet"]["channelTitle"]:
                playlist = None

            async for playlist_item in playlist_items:
                tasks.append(asyncio.create_task(
                    _process_video(playlist_item, playlist)))

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

        tasks = []
        processed_videos = set()  # just not to not process same video twice
        processed_playlists = set()  # same

        async with playlist_ids.stream() as streamer:
            async for id in streamer:
                tasks.append(asyncio.create_task(_process_playlist(id)))

        await asyncio.gather(*tasks)

    def _fill_related_videos(self):
        @async_to_sync
        async def get_related_videos(video_id):
            return await self.yt_api.get_related_videos(video_id)

        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")
        for video in Video.objects.all():
            related_videos = get_related_videos(video.youtube_id)

            for related in related_videos:
                # for now skip videos from other channels:
                if "snippet" in related and related["snippet"]["channelId"] \
                        != settings.YOUTUBE_CHANNEL["id"]:
                    continue

                related_obj = Video.objects.get(youtube_id=related["id"])
                video.related_videos.add(related_obj)

                logger.info("Added new related videos to video %s" %
                            (video))

    def _fill_transcripts(self):
        for video in Video.objects.all():
            video_data = video.data
            if video_data.transcript or video_data.transcript_available is not None:
                continue
            try:
                video_data.transcript = self.yt_api.get_video_transcript(
                    video.youtube_id)
                video_data.transcript_available = True
                logger.info(
                    "Transcription downloaded for video: " + str(video))
            except youtube_transcript_api.TooManyRequests as e:
                logger.warn(e)
                video_data.transcript_available = None  # leave None so that it retries later
                break
            except youtube_transcript_api.CouldNotRetrieveTranscript as e:
                logger.info(
                    "Transcription not available for video: " + str(video))
                video_data.transcript_available = False
            finally:
                video_data.save()
