import asyncio
import logging
import os
import shutil
import tempfile
from collections import namedtuple
from django.db import transaction
import youtube_transcript_api
from aiostream import async_, stream
from django.conf import settings
from videosdb.models import PersistentVideoData, Playlist, Tag, Video
from asgiref.sync import sync_to_async, async_to_sync

from .ipfs import IPFS
from .youtube_api import YoutubeAPI, YoutubeDL, parse_youtube_id

logger = logging.getLogger(__name__)


class Downloader:

    # PUBLIC: -------------------------------------------------------------

    def __init__(self):
        self.yt_api = YoutubeAPI(settings.YOUTUBE_KEY)

    def download_one(self, youtube_id):
        self.enqueue_videos([youtube_id])

    def download_all(self):
        all = Video.objects.all()
        self.enqueue_videos([v.youtube_id for v in all])

    def check_for_new_videos(self):
        logger.info("Checking for new videos...")
        with transaction.atomic():
            try:
                asyncio.run(self._sync_db_with_youtube())
                self._reconnect_video_data()
                self._fill_related_videos()

            except YoutubeAPI.YoutubeAPIError as e:
                # this usually raises when YT API quota has been exeeced (HTTP code 403)
                if e.status != 403:
                    raise e
                else:
                    logging.exception(e)

        # self._fill_transcripts()  # this does not use YT API quota
        logger.info("Checking for new videos done.")

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
        videos = Video.objects.all().order_by("?")
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

# PRIVATE: -------------------------------------------------------------------

    def _reconnect_video_data(self):
        for data in PersistentVideoData.objects.all():
            try:
                video = Video.objects.get(youtube_id=data.youtube_id)
                video.data = data
                video.save()
            except Video.DoesNotExist:
                pass

    async def _sync_db_with_youtube(self):

        @sync_to_async
        def _prepare_db():
            for model in (Video, Playlist, Tag):
                model.objects.all().delete()

        @sync_to_async
        def _add_video_to_db(video, playlist=None):
            video, created = Video.objects.get_or_create(youtube_id=video["id"],
                                                         defaults={"yt_data": video})
            if not created:
                return

            if playlist:
                video.playlist_set.add(
                    Playlist.objects.get(youtube_id=playlist["id"]))
            logger.debug("New video: " + str(video))

        @sync_to_async
        def _add_playlist_to_db(playlist):

            playlist_obj, created = Playlist.objects.get_or_create(
                youtube_id=playlist["id"],
                defaults={"yt_data": playlist})

            if not created:
                return

            logger.debug("New playlist: " + str(playlist_obj))

        async def _process_video(video_id, playlist):
            video = await self.yt_api.get_video_info(video_id)

            if not video:
                return
            # some playlists include videos from other channels
            # for now exclude those videos
            # in the future maybe exclude whole playlist
            if video["channelId"] != settings.YOUTUBE_CHANNEL["id"]:
                return

            await _add_video_to_db(video, playlist)

            logger.debug("Processed video: " + video_id)

        async def _process_playlist(playlist_id):

            playlist = await self.yt_api.get_playlist_info(playlist_id)

            if playlist["channel_title"] != settings.YOUTUBE_CHANNEL["name"]:
                return
            if playlist["title"] == "Liked videos" or \
                    playlist["title"] == "Popular uploads":
                return

            logger.info("Processing playlist: " + str(playlist["title"]))

            playlist = playlist if playlist["title"] != "Uploads from " + \
                playlist["channel_title"] else None

            if playlist:
                await _add_playlist_to_db(playlist)

            videos = self.yt_api.list_playlist_videos(playlist_id)
            async for video in videos:
                asyncio.create_task(_process_video(video, playlist))

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

        await _prepare_db()

        # this triggers everything:
        async with playlist_ids.stream() as streamer:
            async for id in streamer:
                asyncio.create_task(_process_playlist(id))

    def _fill_related_videos(self):
        # order randomly and use remaining daily quota to download a few related lists:
        for video in Video.objects.all():
            related_videos = asyncio.run(self.yt_api.get_related_videos(
                video.youtube_id))

            for video_dict in related_videos:

                # for now skip videos from other channels:
                if "snippet" in video_dict and video_dict["snippet"]["channelId"] != settings.YOUTUBE_CHANNEL["id"]:
                    continue

                try:
                    id = video_dict["id"]["videoId"]
                    related_video = Video.objects.get(youtube_id=id)
                except Video.DoesNotExist:
                    continue

                video.related_videos.add(related_video)
                logger.info("Added new related video: %s to video %s" %
                            (related_video, video))

    def _fill_transcripts(self):
        for video in Video.objects.all().order_by("-yt_data__publishedAt"):
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
                logger.info(
                    "Transcription not available for video: " + str(video))
                video.transcript_available = False
            finally:
                video.save()
