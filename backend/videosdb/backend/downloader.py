from collections import namedtuple
from .youtube_api import YoutubeAPI, YoutubeDL, parse_youtube_id
import shutil
import re
import random
from django.conf import settings
from videosdb.models import Video, Category
from autologging import traced
from .ipfs import IPFS
import logging
import tempfile
import os
import youtube_transcript_api

logger = logging.getLogger(__name__)


_ntuple_diskusage = namedtuple('usage', 'total used free')


def disk_usage(path):
    """Return disk usage statistics about the given path.

    Returned valus is a named tuple with attributes 'total', 'used' and
    'free', which are the amount of total, used and free space, in bytes.
    """
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize


@traced(logging.getLogger(__name__))
class Downloader:
    def __init__(self):
        self.yt_api = YoutubeAPI(settings.YOUTUBE_KEY)

    def process_video(self, youtube_id, category_name=None):
        video, created = Video.objects.get_or_create(youtube_id=youtube_id)
        # if new video or missing info, download info:

        if not video.full_response:
            info = self.yt_api.get_video_info(video.youtube_id)
            if not info:
                video.excluded = True
            else:
                video.load_from_youtube_info(info)

        # some playlists include videos from other channels
        # for now exclude those videos
        # in the future maybe exclude whole playlist
        if video.channel_id != settings.YOUTUBE_CHANNEL["id"]:
            video.excluded = True

        if video.excluded:
            video.save()
            return

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
        try:
            self.enqueue_channel(channel_id)
        except YoutubeAPI.YoutubeAPIError as e:
            logging.exception(e)
        self.fill_transcripts()

    def fill_transcripts(self):
        videos = Video.objects.filter(excluded=False)
        for video in videos:
            if not video.transcript and video.transcript_available is None:
                try:
                    video.transcript = self.yt_api.get_video_transcript(
                        video.youtube_id)
                    video.transcript_available = True
                    logger.debug("Transcription downloaded")
                except youtube_transcript_api.TooManyRequests as e:
                    logger.warn(e)
                    video.transcript_available = None  # leave None so that it retries later
                    break
                except youtube_transcript_api.CouldNotRetrieveTranscript as e:
                    video.transcript_available = False
                finally:
                    video.save()

    @staticmethod
<<<<<<< HEAD
    def download_all_to_ipfs():
        ipfs = IPFS()
        yt_dl = YoutubeDL()
        ipfs.api.files.mkdir("/videos", parents=True)
        files = ipfs.api.files.ls("/videos")
        files_by_youtube_id = {}
        if files["Entries"]:
            for file in files["Entries"]:
                youtube_id = parse_youtube_id(file["Name"])
                if not youtube_id:
                    continue

                files_by_youtube_id[youtube_id] = file
        # 'Entries': [
        #     {'Size': 0, 'Hash': '', 'Name': 'Software', 'Type': 0}
        # ]
        videos = Video.objects.filter(excluded=False)
        for video in videos:
            if video.youtube_id in files_by_youtube_id:
                file = files_by_youtube_id[video.youtube_id]
                if not video.ipfs_hash:
                    video.ipfs_hash = file["Hash"]
                video.save()
                continue
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                try:
                    video.filename = yt_dl.download_video(
                        video.youtube_id)
                except YoutubeDL.UnavailableError as e:
                    logging.error(repr(e))
                    continue
                video.ipfs_hash = ipfs.add_file(
                    video.filename)
                video.save()

    @staticmethod
    def download_and_register_in_ipfs(overwrite_hashes = False):
        yt_dl = YoutubeDL()
        videos_dir = os.path.abspath(settings.VIDEO_FILES_DIR)
        if not os.path.exists(videos_dir):
            os.mkdir(videos_dir)
        ipfs = IPFS()

        files = ipfs.api.files.ls("/videos", opts=dict(long=True))
        files_in_ipfs = {}
        if files["Entries"]:
            for file in files["Entries"]:
                youtube_id = parse_youtube_id(file["Name"])
                if not youtube_id:
                    continue
                files_in_ipfs[youtube_id] = file

        files_in_disk = {}
        for file in os.listdir(videos_dir):
            youtube_id = parse_youtube_id(file)
            if not youtube_id:
                continue
            files_in_disk[youtube_id] = file

        # 'Entries': [
        #     {'Size': 0, 'Hash': '', 'Name': 'Software', 'Type': 0}
        # ]
        videos = Video.objects.filter(excluded=False).order_by("-duration")
        for video in videos:

            if video.youtube_id in files_in_ipfs:
                file = files_in_ipfs[video.youtube_id]

                logging.debug("Already in IPFS:  " + str(file))
                if not video.filename:
                    video.filename = file["Name"]
                if not video.ipfs_hash or overwrite_hashes:
                    logging.debug("writing hash")
                    video.ipfs_hash = file["Hash"]
                video.save()
                continue

            if not video.youtube_id in files_in_disk:
                logging.debug("Downloading " + video.youtube_id)
                with tempfile.TemporaryDirectory() as tmpdir:
                    os.chdir(tmpdir)
                    try:
                        video.filename = yt_dl.download_video(
                            video.youtube_id)
                    except YoutubeDL.UnavailableError as e:
                        logging.error(repr(e))
                        continue
                    video.save()
                    try:
                        shutil.move(video.filename, videos_dir)
                    except OSError as e:
                        logging.exception(e)
                        continue

            video.ipfs_hash = ipfs.add_file(videos_dir + "/" +
                                            video.filename,
                                            wrap_with_directory=True,
                                            nocopy=True)
            logging.debug("Added to IPFS: %s, %s" %
                          (video.filename, video.ipfs_hash))
            video.save()

        ipfs.update_dnslink()
