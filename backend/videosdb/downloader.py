import logging
import bleach
import os
import pprint
import re
import random
from datetime import datetime
import anyio
import fnc
import isodate
from aiostream import stream
from autologging import traced
from google.cloud import firestore
from google.oauth2 import service_account
from slugify import slugify
from videosdb.youtube_api import YoutubeAPI, get_video_transcript
import youtube_transcript_api
import sys

logger = logging.getLogger(__name__)


async def asyncgenerator(item):
    yield item


def _filter_exceptions(group: anyio.ExceptionGroup, exception_type, handler_func):
    unhandled_exceptions = []
    for e in group.exceptions:
        if type(e) == exception_type:
            handler_func(e)
        else:
            unhandled_exceptions.append(e)

    if unhandled_exceptions:
        raise anyio.ExceptionGroup(unhandled_exceptions)


class DB:
    @staticmethod
    def setup(project, config):
        BASE_DIR = os.path.dirname(sys.modules[__name__].__file__)
        creds_json_path = os.path.join(
            BASE_DIR, "keys/%s.json" % config.strip('"'))

        logger.info("Current project: " + project)
        db = firestore.AsyncClient(project=project,
                                   credentials=service_account.Credentials.from_service_account_file(
                                       creds_json_path))

        return db

    def __init__(self):
        project = os.environ["FIREBASE_PROJECT"]
        config = os.environ["VIDEOSDB_CONFIG"]
        self.db = self.setup(project, config)

    def meta_ref(self):
        return self.db.collection("meta").document("meta")

    async def init(self):
        # initialize meta table:
        doc = await self.meta_ref().get()
        if not doc.exists or "videoIds" not in doc.to_dict():
            await self.meta_ref().set(
                {"videoIds": list()}
            )
        return self

    async def update_last_updated(self):
        return await self.meta_ref().set({
            "lastUpdated": datetime.now().isoformat()
        }, merge=True)

    async def get_video_count(self):
        doc = await self.meta_ref().get()
        if doc.exists:
            return len(doc.get("videoIds"))
        else:
            return 0


class LockedDict:
    def __init__(self):
        self.lock = anyio.Lock()
        self.d = dict()


class Downloader:

    # PUBLIC: -------------------------------------------------------------
    def __init__(self, exclude_transcripts=False):

        if "FIRESTORE_EMULATOR_HOST" in os.environ:
            logger.info("USING EMULATOR")
        else:
            logger.info("USING LIVE DATABASE")
        # for k, v in os.environ.items():
        #     logger.debug('- %s = "%s"' % (k, v))

        logger.debug("ENVIRONMENT:")
        logger.debug(pprint.pformat(os.environ))
        self.exclude_transcripts = exclude_transcripts
        if exclude_transcripts:
            logger.debug("Excluding transcripts")
        self.YT_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]
        self.db = DB()
        self.api = YoutubeAPI(self.db.db)
        self.streams = []
        self.video_ids = LockedDict()  # video_id -> set() of playlist_ids

    async def init(self):
        await self.db.init()
        self.capacity_limiter = anyio.CapacityLimiter(10)

    async def check_for_new_videos(self):
        logger.info("Sync start")
        async with anyio.create_task_group() as global_scope:
            await self.init()
            global_scope.start_soon(self._print_debug_info,
                                    name="Debug info")

            # retrieve playlists:
            try:
                await self._retrieve_playlists()

                # create videos
                async with anyio.create_task_group() as video_creators:
                    async with self.video_ids.lock:
                        for video_id, playlist_ids in self.video_ids.d.items():
                            video_creators.start_soon(
                                self._create_video, video_id, list(
                                    playlist_ids)
                            )
            except YoutubeAPI.QuotaExceededError as e:
                logger.error(e)
            except anyio.ExceptionGroup as group:
                _filter_exceptions(
                    group, YoutubeAPI.QuotaExceededError, logger.error)

            # retrieve pending transcripts
            if not self.exclude_transcripts:
                logger.debug("Retrieving transcripts")
                async for video in self.db.db.collection("videos").stream():
                    global_scope.start_soon(
                        self._handle_transcript, video, name="Download transcript")

            # update videoid list
            async with self.video_ids.lock:
                await self.db.meta_ref().set({
                    "videoIds": list(self.video_ids.d.keys())
                })

            await anyio.wait_all_tasks_blocked()
            await self.api.aclose()
            await self.db.update_last_updated()
            global_scope.cancel_scope.cancel()

        logger.info("Sync finished")

    async def _retrieve_playlists(self):
        logger.info("Currently there are %s videos in the DB",
                    await self.db.get_video_count())

        playlist_sender, playlist_receiver = anyio.create_memory_object_stream()
        self.streams = [
            playlist_receiver,
            playlist_sender
        ]

        async with anyio.create_task_group() as processors:
            processors.start_soon(self._playlist_retriever,
                                  playlist_sender, name="Playlist retriever")
            processors.start_soon(self._playlist_processor,
                                  playlist_receiver, name="Playlist receiver")

    @traced
    async def _playlist_retriever(self, playlist_sender):
        with playlist_sender:

            channel_id = self.YT_CHANNEL_ID
            channel_info = await self.api.get_channel_info(channel_id)

            logger.info("Processing channel: " +
                        str(channel_info["snippet"]["title"]))
            self.YT_CHANNEL_NAME = str(channel_info["snippet"]["title"])

            await self.db.db.collection("channel_infos").document(channel_id).set(channel_info, merge=True)

            all_uploads_playlist_id = channel_info["contentDetails"]["relatedPlaylists"]["uploads"]

            if "DEBUG" in os.environ:
                playlist_ids = stream.iterate(
                    self.api.list_channelsection_playlist_ids(channel_id)
                )

            else:
                playlist_ids = stream.merge(
                    asyncgenerator(all_uploads_playlist_id),
                    self.api.list_channelsection_playlist_ids(channel_id),
                    self.api.list_channel_playlist_ids(channel_id)
                )

            async with playlist_ids.stream() as streamer:
                async for playlist_id in streamer:
                    await playlist_sender.send(playlist_id)

    @traced
    async def _playlist_processor(self, playlist_receiver):
        processed_playlist_ids = set()

        async with anyio.create_task_group() as nursery:
            async for playlist_id in playlist_receiver:
                if playlist_id in processed_playlist_ids:
                    continue
                nursery.start_soon(
                    self._process_playlist, playlist_id, name="PL " + playlist_id)

                processed_playlist_ids.add(playlist_id)

    @traced
    async def _process_playlist(self, playlist_id):
        playlist = await self.api.get_playlist_info(playlist_id)

        if not playlist:
            return

        if playlist["snippet"]["channelTitle"] != self.YT_CHANNEL_NAME:
            return

        playlist = playlist if playlist["snippet"]["title"] != "Uploads from " + \
            playlist["snippet"]["channelTitle"] else None

        items = []
        result = await self.api.list_playlist_items(playlist_id)

        async for item in result:
            if item["snippet"]["channelId"] != self.YT_CHANNEL_ID:
                continue
            items.append(item)

        await self._create_playlist(playlist, playlist_id, items)

    @traced
    async def _create_playlist(self, playlist, playlist_id, items):
        video_count = 0
        last_updated = None

        for item in items:
            new_video = False
            video_id = item["snippet"]["resourceId"]["videoId"]
            async with self.video_ids.lock:
                if video_id not in self.video_ids.d:
                    self.video_ids.d[video_id] = set()
                    new_video = True
                if playlist:  # exclude dummy playlists
                    self.video_ids.d[video_id].add(playlist_id)

            video_count += 1
            video_date = isodate.parse_datetime(
                item["snippet"]["publishedAt"])
            if not last_updated or video_date > last_updated:
                last_updated = video_date

        if not playlist:  # exclude dummy playlists
            return

        playlist["videosdb"] = dict()
        playlist["videosdb"]["slug"] = slugify(
            playlist["snippet"]["title"])
        playlist["videosdb"]["videoCount"] = video_count
        playlist["videosdb"]["lastUpdated"] = last_updated

        await self.db.db.collection("playlists").document(playlist["id"]).set(playlist, merge=True)
        logger.info("Created playlist: " + playlist["snippet"]["title"])

    @traced
    async def _create_video(self, video_id, playlist_ids):
        video = await self.api.get_video_info(video_id)

        if not video:
            return
        # some playlists include videos from other channels
        # for now exclude those videos
        # in the future maybe exclude whole playlist

        if video["snippet"]["channelId"] != self.YT_CHANNEL_ID:
            return

        custom_attrs = dict()

        custom_attrs["slug"] = slugify(
            video["snippet"]["title"])
        custom_attrs["descriptionTrimmed"] = bleach.linkify(
            video["snippet"]["description"])
        custom_attrs["durationSeconds"] = isodate.parse_duration(
            video["contentDetails"]["duration"]).total_seconds()
        custom_attrs["playlists"] = playlist_ids

        video["videosdb"] = custom_attrs
        video["snippet"]["publishedAt"] = isodate.parse_datetime(
            video["snippet"]["publishedAt"])
        for stat, value in video["statistics"].items():
            video["statistics"][stat] = int(value)

        await self.db.db.collection("videos").document(
            video_id).set(video, merge=True)

        logger.info("Created video: %s (%s)" %
                    (video_id, video["snippet"]["title"]))

        return video

    @traced
    async def _fill_related_videos(self):

        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")

        async with anyio.create_task_group():
            meta_doc = await self.db.meta_ref().get()
            randomized_ids = meta_doc.get("videoIds")
            random.shuffle(randomized_ids)
            for video_id in randomized_ids:
                related_videos = await self.api.get_related_videos(video_id)

                for related in related_videos:
                    # for now skip videos from other channels:
                    if "snippet" in related and related["snippet"]["channelId"] \
                            != self.YT_CHANNEL_ID:
                        continue

                    await self.db.db.collection("videos").document(video_id).update({
                        "videosdb.related_videos": firestore.ArrayUnion([related["id"]["videoId"]])
                    })

                    logger.info("Added new related videos to video %s" %
                                video_id)

    async def _handle_transcript(self, video):
        if not video.exists:
            return

        v = video.to_dict()
        current_status = fnc.get("videosdb.transcript_status", v)
        if current_status not in ("pending", None):
            return
        logger.info("Downloading transcript for video: " +
                    str(v["id"]) + " because its status is " + str(current_status))
        transcript, new_status = await self._download_transcript(v["id"])
        if new_status == current_status:
            return

        new_data = {
            "videosdb": {
                "transcript_status": new_status,
                "transcript": transcript
            }
        }
        await self.db.db.collection("videos").document(
            v["id"]).set(new_data, merge=True)

    async def _download_transcript(self, video_id):
        try:
            with anyio.fail_after(60):
                transcript = await anyio.to_thread.run_sync(
                    get_video_transcript, video_id, limiter=self.capacity_limiter)

            return transcript, "downloaded"
        except youtube_transcript_api.TooManyRequests as e:
            logger.warning(str(e))
            logger.warning("New status: pending")
            return None, "pending"
        except youtube_transcript_api.CouldNotRetrieveTranscript as e:
            # weird but that's how the lib works:
            if (hasattr(e, "video_id")
                and hasattr(e.video_id, "response")
                    and e.video_id.response.status_code == 429):
                logger.warning(str(e))
                logger.warning("New status: pending")
                return None, "pending"
            else:
                logger.info(
                    "Transcription not available for video: " + str(video_id))
                logger.info(str(e))
                logger.info("New status: unavailable")
                return None, "unavailable"

    @staticmethod
    def _description_trimmed(description):
        if not description:
            return
        match = re.search("#Sadhguru", description)
        if match and match.start() != -1:
            return description[:match.start()]
        return description

    async def _print_debug_info(self):
        while True:
            tasks = anyio.get_running_tasks()
            logger.debug('Running tasks:' + str(len(tasks)))
            logger.debug(pprint.pformat(tasks))

            for stream in self.streams:
                logger.debug(str(stream.statistics()))

            logger.debug(str(self.video_ids.lock.statistics()))

            await anyio.sleep(30)
