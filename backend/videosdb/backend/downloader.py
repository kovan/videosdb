import asyncio
import logging
# from google.cloud import firestore

from django.db import transaction
import youtube_transcript_api
from aiostream import async_, stream
from django.conf import settings
from videosdb.models import PersistentVideoData, Playlist, Tag, Video
from asgiref.sync import sync_to_async, async_to_sync


from .youtube_api import YoutubeAPI

logger = logging.getLogger(__name__)


class Downloader:

    # PUBLIC: -------------------------------------------------------------

    def __init__(self):
        logging.getLogger("asyncio").setLevel(logging.WARNING)

    def download_one(self, youtube_id):
        self.enqueue_videos([youtube_id])

    def download_all(self):
        all = Video.objects.all()
        self.enqueue_videos([v.youtube_id for v in all])

    def check_for_new_videos(self):

        def _download():

            videos = {}
            playlists = {}
            for item in asyncio.run(self._check_for_new_videos()):
                if not item:
                    continue
                logging.debug("Processing item " + str(item))
                if item["kind"] == "youtube#playlist":
                    playlists[item["id"]] = item
                elif item["kind"] == "youtube#video":
                    videos[item["id"]] = item
                else:
                    raise Exception("unknown item: " + str(item))

            return videos, playlists

        def _write_to_db(videos, playlists):

            Video.objects.all().delete()
            Playlist.objects.all().delete()
            Tag.objects.all().delete()

            # first videos:
            l = (Video(youtube_id=id, yt_data=video)
                 for id, video in videos.items())
            Video.objects.bulk_create(l)

            for video in Video.objects.all():
                video.create_tags()
                video.create_slug()
                video.save()

            # then playlists:
            l = (Playlist(youtube_id=id, yt_data=playlist)
                 for id, playlist in playlists.items())
            Playlist.objects.bulk_create(l)

            for id, playlist in playlists.items():
                playlist_obj = Playlist.objects.get(youtube_id=id)
                playlist_obj.create_slug()
                playlist_obj.save()

                # fill related videos:
                for item in playlist["items"]:
                    video_id = item["snippet"]["resourceId"]["videoId"]
                    try:
                        video = Video.objects.get(youtube_id=video_id)
                        playlist_obj.videos.add(video)
                    except Video.DoesNotExist as e:
                        pass

        videos, playlists = _download()
        with transaction.atomic():
            logging.info("Writing new data to database...")
            _write_to_db(videos, playlists)
            for data in PersistentVideoData.objects.all():
                try:
                    video = Video.objects.get(youtube_id=data.youtube_id)
                    video.data = data
                    video.save()
                except Video.DoesNotExist:
                    pass
# PRIVATE: -------------------------------------------------------------------

    async def _check_for_new_videos(self):
        # self.db = firestore.AsyncClient()
        self.yt_api = await YoutubeAPI.create(settings.YOUTUBE_KEY)
        logger.info("Checking for new videos...")

        try:
            return await self._sync_db_with_youtube()
            # self._fill_related_videos()

        except YoutubeAPI.YoutubeAPIError as e:
            # this usually raises when YT API quota has been exeeced (HTTP code 403)
            if e.status != 403:
                raise e
            else:
                logging.exception(e)

        # self._fill_transcripts()  # this does not use YT API quota
        logger.info("Checking for new videos done.")

    async def _sync_db_with_youtube(self):

        # async def _add_video_to_db(video, playlist_item=None):
        #     ref = self.db.collection("videos")
        #     await ref.document(video["id"]).set(video)

        # async def _add_playlist_to_db(playlist):

        #     ref = self.db.collection("playlists")
        #     await ref.document(playlist["id"]).set(playlist)

        async def _process_video(playlist_item):
            video_id = playlist_item["snippet"]["resourceId"]["videoId"]

            # some playlists include videos from other channels
            # for now exclude those videos
            # in the future maybe exclude whole playlist
            if playlist_item["snippet"]["channelId"] != settings.YOUTUBE_CHANNEL["id"]:
                return

            video = await self.yt_api.get_video_info(video_id)

            processed_videos.add(video_id)

            if not video:
                return

            # await _add_video_to_db(video, playlist_item)

            logger.info("Processing video: " + video_id)
            return video

        async def _process_playlist(playlist_id):

            playlist = await self.yt_api.get_playlist_info(playlist_id)
            if playlist["snippet"]["channelTitle"] != settings.YOUTUBE_CHANNEL["name"]:
                return

            if playlist["snippet"]["title"] == "Liked videos" or \
                    playlist["snippet"]["title"] == "Popular uploads":
                return

            logger.info("Processing playlist: " +
                        str(playlist["snippet"]["title"]))

            playlist_items = self.yt_api.list_playlist_videos(playlist_id)
            playlist["items"] = []
            async for playlist_item in playlist_items:
                video_id = playlist_item["snippet"]["resourceId"]["videoId"]
                if video_id in processed_videos:
                    continue

                tasks.append(asyncio.create_task(
                    _process_video(playlist_item)))
                playlist["items"].append(playlist_item)

            if playlist["snippet"]["title"] == "Uploads from " + \
                    playlist["snippet"]["channelTitle"]:
                return None

            return playlist

        async def asyncgenerator(item):
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
            asyncgenerator(all_uploads_playlist_id)
        )

        tasks = []
        processed_videos = set()  # just not to not process same video twice
        async with playlist_ids.stream() as streamer:
            async for id in streamer:
                tasks.append(asyncio.create_task(_process_playlist(id)))

        # start all:
        logging.info("Waiting for API results...")
        results = await asyncio.gather(*tasks)
        return results

    async def _fill_related_videos(self):
        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")
        async for video in self.db.collection("videos").stream():
            id = video["id"]["videoId"]
            related_videos = await self.yt_api.get_related_videos(id)

            # # for now skip videos from other channels:
            # if "snippet" in video and video["snippet"]["channelId"] \
            #         != settings.YOUTUBE_CHANNEL["id"]:
            #     continue

            await video.collection("related_videos").set(related_videos)

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
