from .youtube_api import YoutubeAPI, YoutubeDL

from django.conf import settings
from videosdb.models import Video, Category
from autologging import traced
from .ipfs import IPFS
import logging
import tempfile
import os
import youtube_transcript_api

logger = logging.getLogger(__name__)


@traced(logging.getLogger(__name__))
class Downloader:
    def __init__(self):
        self.yt_api = YoutubeAPI(settings.YOUTUBE_KEY)

    def process_video(self, youtube_id, category_name=None):
        video, created = Video.objects.get_or_create(youtube_id=youtube_id)
        # if new video or missing info, download info:
        info = self.yt_api.get_video_info(video.youtube_id)
        if info:
            video.load_from_youtube_info(info)
        else:
            video.excluded = True

        # some playlists include videos from other channels
        # for now exclude those videos
        # in the future maybe exclude whole playlist
        if video.channel_id != settings.YOUTUBE_CHANNEL["id"]:
            video.excluded = True

        if video.excluded:
            video.save()
            return

        if not video.transcript and video.transcript_available is None:
            try:
                video.transcript = self.yt_api.get_video_transcript(
                    video.youtube_id)
                video.transcript_available = True
                logger.debug("Transcription downloaded")
            except youtube_transcript_api.TooManyRequests as e:
                logger.warn(e)
                video.transcript_available = None  # leave None so that it retries later
            except youtube_transcript_api.CouldNotRetrieveTranscript as e:
                logger.info(e)
                video.transcript_available = False

        if category_name:
            category, created = Category.objects.get_or_create(
                name=category_name)
            video.categories.add(category)

        video.save()

    def enqueue_videos(self, video_ids, category_name=None):

        # threads = []
        # for i in range(len(video_ids)):
        #     thread = self.loop.create_task(
        #         process_video(video_ids[i], category_name))
        #     threads.append(thread)
        # self.loop.run_until_complete(asyncio.gather(*threads))
        for yid in video_ids:
            self.process_video(yid, category_name)

    def enqueue_channel(self, channel_id):
        def process_playlist(playlist):

            if playlist["channel_title"] != settings.YOUTUBE_CHANNEL["name"]:
                return
            if playlist["title"] == "Liked videos" or \
                    playlist["title"] == "Popular uploads":
                return

            video_ids = self.yt_api.list_playlist_videos(playlist["id"])

            if playlist["title"] == "Uploads from " + playlist["channel_title"]:
                self.enqueue_videos(video_ids)
            else:
                self.enqueue_videos(video_ids, playlist["title"])

        playlists = self.yt_api.list_playlists(channel_id)
        for playlist in playlists:
            process_playlist(playlist)

        # threads = []
        # for i in range(len(playlists)):
        #     thread = self.loop.create_task(
        #         process_playlist(playlists[i]))
        #     threads.append(thread)
        # self.loop.run_until_complete(asyncio.gather(*threads))

    def download_one(self, youtube_id):
        self.enqueue_videos([youtube_id])

    def download_all(self):
        all = Video.objects.filter(excluded=False)
        self.enqueue_videos([v.youtube_id for v in all])

    def check_for_new_videos(self):
        channel_id = settings.YOUTUBE_CHANNEL["id"]
        self.enqueue_channel(channel_id)

    def download_pending(self):
        videos = Video.objects.filter(excluded=False)
        self.enqueue_videos([v.youtube_id for v in videos if not v.title])

    def download_all_to_ipfs(self):
        ipfs = IPFS()
        yt_dl = YoutubeDL()
        videos = Video.objects.filter(excluded=False)
        for video in videos:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                video.filename = yt_dl.download_video(
                    video.youtube_id)
                video.ipfs_hash = ipfs.add_file(video.filename)
