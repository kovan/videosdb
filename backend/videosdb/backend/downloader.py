import itertools
import logging
import os
import random
import re
import shutil
import tempfile
from collections import namedtuple

import youtube_transcript_api
from autologging import traced
from django.conf import settings
from videosdb.models import Category, Video

from .ipfs import IPFS
from .youtube_api import YoutubeAPI, YoutubeDL, parse_youtube_id

logger = logging.getLogger(__name__)


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

        if created:
            logger.info("New video found: " + str(video))

        if category_name:
            category, created = Category.objects.get_or_create(
                name=category_name)
            video.categories.add(category)
            if created:
                logger.info("New category found: " + str(video))

        return video

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

            logger.info("Processing playlist: " + str(playlist["title"]))

            video_ids = self.yt_api.list_playlist_videos(playlist["id"])

            if playlist["title"] == "Uploads from " + playlist["channel_title"]:
                self.enqueue_videos(video_ids)
            else:
                self.enqueue_videos(video_ids, playlist["title"])

        channel_info = list(self.yt_api.get_channel_info(
            channel_id))[0]

        logger.info("Processing channel: " +
                    str(channel_info["snippet"]["title"]))

        all_uploads_playlist = self.yt_api.get_playlist_info(
            channel_info["contentDetails"]["relatedPlaylists"]["uploads"])
        playlists1 = self.yt_api.list_channnelsection_playlists(channel_id)
        playlists2 = self.yt_api.list_channel_playlists(channel_id)
        playlists = itertools.chain(
            [all_uploads_playlist], playlists1, playlists2)

        processed_playlists_ids = []
        for playlist in playlists:
            if playlist in processed_playlists_ids:
                continue
            process_playlist(playlist)
            processed_playlists_ids.append(playlist)

    def download_one(self, youtube_id):
        self.enqueue_videos([youtube_id])

    def download_all(self):
        all = Video.objects.filter(excluded=False)
        self.enqueue_videos([v.youtube_id for v in all])

    def check_for_new_videos(self):
        logger.info("Checking for new videos...")
        channel_id = settings.YOUTUBE_CHANNEL["id"]
        try:
            # order here is important because we don't want the quota
            # to be exhausted while crawling the channel
            self.enqueue_channel(channel_id)
            self.fill_related_videos()
            # this usually raises when YT API quota has been exeeced:
        except YoutubeAPI.YoutubeAPIError as e:
            logging.exception(e)

        self.fill_transcripts()
        logger.info("Checking for new videos done.")

    def fill_related_videos(self):
        # order randomly and use remaining daily quota to download a few related lists:
        for video in Video.objects.filter(excluded=False).order_by("?"):
            if video.related_videos.count() > 0:
                continue

            related_videos = self.yt_api.get_related_videos(video.youtube_id)
            for video_dict in related_videos:
                # for now skip videos from other channels:
                if video_dict["snippet"]["channelId"] != settings.YOUTUBE_CHANNEL["id"]:
                    continue
                related_video = self.process_video(video_dict["id"]["videoId"])
                if not related_video:
                    continue

                video.related_videos.add(related_video)
                logger.info("Added new related video: %s to video %s" %
                            (related_video, video))

    def fill_transcripts(self):
        for video in Video.objects.filter(excluded=False).order_by("-yt_published_date"):
            if video.transcript or video.transcript_available is not None:
                continue
            try:
                video.transcript = self.yt_api.get_video_transcript(
                    video.youtube_id)
                video.transcript_available = True
                logger.info(
                    "Transcription downloaded for video: " + str(video))
            except youtube_transcript_api.TooManyRequests as e:
                logger.warn(e)
                video.transcript_available = None  # leave None so that it retries later
                break
            except youtube_transcript_api.CouldNotRetrieveTranscript as e:
                video.transcript_available = False
            finally:
                video.save()

    @staticmethod
    def download_and_register_in_ipfs(overwrite_hashes=False):
        yt_dl = YoutubeDL()
        videos_dir = os.path.abspath(settings.VIDEO_FILES_DIR)
        if not os.path.exists(videos_dir):
            os.mkdir(videos_dir)
        ipfs = IPFS()

        files = ipfs.api.files.ls("/videos", opts=dict(long=True))
        files_in_ipfs = {}
        if files["Entries"]:
            for file in files["Entries"]:
                if file["Name"].lower().endswith(".mp4"):
                    youtube_id = parse_youtube_id(file["Name"])
                    if not youtube_id or youtube_id in files_in_ipfs:
                        raise Exception()
                    files_in_ipfs[youtube_id] = file

        files_in_disk = {}
        for file in os.listdir(videos_dir):
            youtube_id = parse_youtube_id(file)
            if file.endswith(".part"):
                continue
            if not youtube_id or youtube_id in files_in_disk:
                raise Exception()
            files_in_disk[youtube_id] = file

        # 'Entries': [
        #     {'Size': 0, 'Hash': '', 'Name': 'Software', 'Type': 0}
        # ]
        videos = Video.objects.filter(excluded=False).order_by("?")
        for video in videos:

            if not video.youtube_id in files_in_disk:
                logging.debug("Downloading " + video.youtube_id)
                with tempfile.TemporaryDirectory() as tmpdir:
                    os.chdir(tmpdir)
                    try:
                        video.filename = yt_dl.download_video(
                            video.youtube_id)
                    except YoutubeDL.UnavailableError as e:
                        continue
                    video.save()
                    try:
                        shutil.move(video.filename, videos_dir)
                    except OSError as e:
                        logging.exception(e)
                        continue
            file = files_in_disk.get(video.youtube_id)
            if file and file != video.filename:
                video.filename = file

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

            logging.debug("Adding to IPFS: ID:%s, title: %s, Filename: %s, Hash: %s" %
                          (video.youtube_id, video.title, video.filename, video.ipfs_hash))
            video.ipfs_hash = ipfs.add_file(videos_dir + "/" +
                                            video.filename,
                                            wrap_with_directory=True,
                                            nocopy=True)

            video.save()

        ipfs.update_dnslink()
