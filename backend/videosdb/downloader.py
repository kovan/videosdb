import logging
import os
import pprint
import random
import re
from abc import abstractmethod
from typing import Any

import anyio
import bleach
import fnc
import isodate
import youtube_transcript_api
from aiostream import stream
from autologging import traced
from google.cloud import firestore
from slugify import slugify
from videosdb.db import DB, CounterTypes
from videosdb.publisher import TwitterPublisher
from videosdb.youtube_api import YoutubeAPI, get_video_transcript

from videosdb.utils import QuotaExceeded, my_handler

logger = logging.getLogger(__name__)


class LockedItem:
    def __init__(self, item) -> None:
        self.lock = anyio.Lock()
        self.item = item

    async def __aenter__(self):
        await self.lock.acquire()
        return self.item

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()


@traced
class Task:

    def __init__(self, db, options=None, nursery=None):
        self.db = db
        self.options = options
        self.nursery = nursery

    @abstractmethod
    async def __call__(self, video):
        raise NotImplementedError()


@traced
class ExportToEmulatorTask(Task):

    def __init__(self, db, options=None, nursery=None):
        super().__init__(db, options, nursery)
        self.enabled = options and options.export_to_emulator_host
        if not self.enabled:
            return

        previous_emu = os.environ.get("FIRESTORE_EMULATOR_HOST")
        os.environ["FIRESTORE_EMULATOR_HOST"] = options.export_to_emulator_host

        self.emulator_client = DB.get_client()

        if previous_emu:
            logger.debug("Restoring emulator host")
            os.environ["FIRESTORE_EMULATOR_HOST"] = previous_emu
        else:
            del os.environ["FIRESTORE_EMULATOR_HOST"]

    async def __call__(self, video):
        if not self.enabled:
            return
        emulator_ref = self.emulator_client.collection(
            "videos").document(video["id"])
        await emulator_ref.set(video)

    async def export_pending_collections(self):
        if not self.enabled:
            return
        async for col in self.db._db.collections():
            if col == "videos":
                continue

            async for doc_ref in col.list_documents():
                doc = await doc_ref.get()
                emulator_ref = self.emulator_client.collection(
                    col.id).document(doc.id)
                await emulator_ref.set(doc.to_dict())


@traced
class PublishTask(Task):
    def __init__(self, db, options=None, nursery=None):
        super().__init__(db, options, nursery)
        self.enabled = options and options.enable_twitter_publishing
        if self.enabled:
            self.publisher = TwitterPublisher(db)

    async def __call__(self, video):
        if not self.enabled:
            return

        try:
            await self.publisher.publish_video(video)
        except Exception as e:
            # twitter errors show not stop the program
            logger.exception(e)


@traced
class RetrievePendingTranscriptsTask(Task):
    def __init__(self, db, options=None, nursery=None):
        super().__init__(db, options, nursery)
        self.enabled = options and options.enable_transcripts
        self.capacity_limiter = anyio.CapacityLimiter(10)

    async def __call__(self, video):
        if not self.enabled:
            return
        self.nursery.start_soon(self._handle_transcript,
                                video, name="Download transcript for video " + video["id"])

    async def _handle_transcript(self, video):

        current_status = fnc.get("videosdb.transcript_status", video)
        if current_status not in ("pending", None):
            return
        logger.info("Downloading transcript for video: " +
                    str(video["id"]) + " because its status is " + str(current_status))
        transcript, new_status = await self._download_transcript(video["id"], self.capacity_limiter)
        if new_status == current_status:
            return

        video |= {
            "videosdb": {
                "transcript_status": new_status,
                "transcript": transcript
            }
        }

        await self.db.set_noquota("videos/" + video["id"], video, merge=True)

    @staticmethod
    async def _download_transcript(video_id, capacity_limiter):
        try:
            transcript = await anyio.to_thread.run_sync(
                get_video_transcript, video_id, limiter=capacity_limiter)

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


@traced
class VideoProcessor:
    def __init__(self, db, api, channel_id) -> None:
        self._db = db
        self._api = api
        self._channel_id = channel_id
        self._video_to_playlist_list = LockedItem(dict())

    # entrypoint:
    async def close(self):
        async with anyio.create_task_group() as tg:
            async with self._video_to_playlist_list as videos:
                video_ids = list(videos.keys())
                random.shuffle(video_ids)
                for video_id in video_ids:
                    playlists = videos[video_id]
                    tg.start_soon(self._create_video, video_id,
                                  playlists, name=f"Create video {video_id}")

    async def add_video(self, video_id, playlist_id):
        logger.debug(
            f"Processing playlist item video {video_id}, playlist {playlist_id}")

        async with self._video_to_playlist_list as videos:
            if video_id not in videos.keys():
                videos[video_id] = []
            videos[video_id].append(playlist_id)

    async def _create_video(self, video_id, playlists):
        video = {}
        try:
            _, downloaded_video = await self._api.get_video_info(video_id)
            if downloaded_video:
                video |= downloaded_video
        except Exception as e:
            # keep going so that we write whatever we have (playlists)
            my_handler(YoutubeAPI.YTQuotaExceeded, e, logger.error)

        if not video:
            return

        video["videosdb"] = {}

        if downloaded_video:
            # some playlists include videos from other channels
            # for now exclude those videos
            # in the future maybe exclude whole playlist

            if fnc.get("snippet.channelId", video) != self._channel_id:
                return

            video["videosdb"] |= {
                "slug":  slugify(video["snippet"]["title"]),
                "descriptionTrimmed": bleach.linkify(video["snippet"]["description"]),
                "durationSeconds": isodate.parse_duration(
                    video["contentDetails"]["duration"]).total_seconds(),

            }

            video["snippet"]["publishedAt"] = isodate.parse_datetime(
                video["snippet"]["publishedAt"])

            for stat, value in video["statistics"].items():
                video["statistics"][stat] = int(value)

        if playlists:
            video["videosdb"]["playlists"] = firestore.ArrayUnion(playlists)

        await self._db.set("videos/" + video["id"], video, merge=True)

        logger.info("Wrote video: %s" % video["id"])

        return video


@ traced
class Downloader:

    # PUBLIC: -------------------------------------------------------------
    def __init__(self, options=None, db=None, redis_db_n=None):

        logger.debug("ENVIRONMENT:")
        logger.debug(pprint.pformat(os.environ))
        self.options = options

        self.YT_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]
        self.db = db if db else DB()
        self.api = YoutubeAPI(self.db, redis_db_n=redis_db_n)

    async def init(self):
        await self.db.init()

    async def check_for_new_videos(self):
        logger.info("Sync start")
        async with anyio.create_task_group() as global_nursery:
            await self.init()
            global_nursery.start_soon(self._print_debug_info,
                                      name="Debug info")

            try:
                await self._phase1()
                await self._phase2()
            finally:
                await self._print_debug_info(True)

            # await anyio.wait_all_tasks_blocked()
            global_nursery.cancel_scope.cancel()

        logger.info("Sync finished")

    async def _phase1(self):
        # Phase 1:
        video_processor = VideoProcessor(
            self.db, self.api, self.YT_CHANNEL_ID)
        try:
            channel = await self._create_channel(self.YT_CHANNEL_ID)
            if not channel:
                return
            playlist_ids = await self._retrieve_all_playlist_ids(self.YT_CHANNEL_ID)
            await self._process_playlist_ids(playlist_ids, channel["snippet"]["title"], video_processor)
            await video_processor.close()
        except Exception as e:
            my_handler(QuotaExceeded, e, logger.error)

    async def _phase2(self):
        # Phase 2: does not use Youtube quota:
        async with anyio.create_task_group() as phase2_nursery:
            args = self.db, self.options, phase2_nursery

            export_to_emulator_task = ExportToEmulatorTask(*args)
            tasks = [
                RetrievePendingTranscriptsTask(*args),
                PublishTask(*args),
                export_to_emulator_task
            ]

            await self._final_video_iteration(tasks)
            await export_to_emulator_task.export_pending_collections()

    async def _final_video_iteration(self, phase2_tasks):
        final_video_ids = LockedItem(set())
        logger.info("Init phase 2")

        async for video_ref in self.db.list_documents("videos"):
            video = await video_ref.get()  # type: ignore
            video_dict = video.to_dict()
            video_id = video_dict.get("id")
            if not video_id:
                continue

            async with final_video_ids as video_ids:
                video_ids.add(video_id)

            for task in phase2_tasks:
                await task(video_dict)

        ids = final_video_ids.item
        if ids:
            await self.db.set_noquota("meta/video_ids", {
                "videoIds": firestore.ArrayUnion(list(ids))
            })

        logger.info("Final video list length: " + str(len(ids)))
        return ids

    async def _process_playlist_ids(self, playlist_ids, channel_name, video_processor):

        async with anyio.create_task_group() as phase1:
            random.shuffle(playlist_ids)
            # main iterations:
            for playlist_id in playlist_ids:
                phase1.start_soon(
                    self._process_playlist,
                    playlist_id,
                    channel_name,
                    video_processor,
                    phase1,
                    name="Playlist %s processor" % playlist_id
                )

    async def _process_playlist(self,
                                playlist_id,
                                channel_name,
                                video_processor,
                                task_group):

        logger.info("Processing playlist " + playlist_id)

        _, playlist = await self.api.get_playlist_info(playlist_id)
        if not playlist:
            return

        if playlist["snippet"]["channelTitle"] != channel_name:
            return

        _, playlist_items = await self.api.list_playlist_items(playlist_id)
        # if not _:
        #     return

        await self._create_playlist(playlist, playlist_items)
        # create videos:
        video_ids = playlist["videosdb"]["videoIds"]
        random.shuffle(video_ids)

        for video_id in video_ids:
            task_group.start_soon(
                video_processor.add_video,
                video_id,
                playlist_id,
                name="Add video %s" % video_id
            )

    async def _retrieve_all_playlist_ids(self, channel_id):
        _, ids = await self.api.list_channelsection_playlist_ids(channel_id)
        _, ids2 = await self.api.list_channel_playlist_ids(channel_id)
        if "DEBUG" in os.environ:
            playlists_ids_stream = stream.iterate(ids)
        else:
            playlists_ids_stream = stream.merge(ids, ids2)

        playlist_ids = set()
        async with playlists_ids_stream.stream() as streamer:
            async for playlist_id in streamer:
                playlist_ids.add(playlist_id)

        logger.info("Retrieved all playlist IDs.")
        return list(playlist_ids)

    async def _create_channel(self, channel_id):

        _, channel_info = await self.api.get_channel_info(channel_id)
        if not channel_info:
            return

        logger.info("Processing channel: " +
                    str(channel_info["snippet"]["title"]))

        await self.db.set("channel_infos/" + channel_id, channel_info, merge=True)
        return channel_info

    async def _create_playlist(self, playlist, playlist_items):

        video_count = 0
        last_updated = None
        video_ids = []

        async for item in playlist_items:
            if item["snippet"]["channelId"] != self.YT_CHANNEL_ID:
                continue
            video_ids.append(
                item["snippet"]["resourceId"]["videoId"])
            video_count += 1
            video_date = isodate.parse_datetime(
                item["snippet"]["publishedAt"])
            if not last_updated or video_date > last_updated:
                last_updated = video_date

        playlist |= {
            "videosdb": {
                "videoCount": video_count,
                "lastUpdated": last_updated,
                "videoIds": video_ids,
                "slug": slugify(playlist["snippet"]["title"])
            }
        }
        await self.db.set("playlists/" + playlist["id"], playlist, merge=True)
        logger.info("Wrote playlist: " + playlist["snippet"]["title"])

    # async def _fill_related_videos(self):

    #     # use remaining YT API daily quota to download a few related video lists:
    #     logger.info("Filling related videos info.")

    #     doc = await self.db.get("meta/video_ids")
    #     randomized_ids = doc.get("videoIds")
    #     random.shuffle(randomized_ids)
    #     for video_id in randomized_ids:
    #         related_videos = await self.api.get_related_videos(video_id)

    #         for related in related_videos:
    #             # for now skip videos from other channels:
    #             if "snippet" in related and related["snippet"]["channelId"] \
    #                     != self.YT_CHANNEL_ID:
    #                 continue

    #             await self.db.update("videos/" + video_id, {
    #                 "videosdb.related_videos": firestore.ArrayUnion([related["id"]["videoId"]])
    #             })

    #             logger.info("Added new related videos to video %s" %
    #                         video_id)

    @ staticmethod
    def _description_trimmed(description):
        if not description:
            return
        match = re.search("#Sadhguru", description)
        if match and match.start() != -1:
            return description[:match.start()]
        return description

    async def _print_debug_info(self, once=False):
        while True:
            tasks = anyio.get_running_tasks()
            logger.info('Running tasks:' + str(len(tasks)))
            logger.info(pprint.pformat(tasks))
            stats = await self.api.cache.stats()
            logger.info("Cache stats: ")
            logger.info(pprint.pformat(stats))

            if once:
                return
            await anyio.sleep(30)
