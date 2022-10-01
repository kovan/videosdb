import logging
import bleach
import os
import pprint
from google.cloud import firestore
import re
import random
import anyio
import fnc
import isodate
from aiostream import stream
from autologging import traced
import google.api_core.exceptions
from slugify import slugify
from videosdb.utils import _contains_exceptions
from videosdb.youtube_api import YoutubeAPI, get_video_transcript
from videosdb.db import DB
from videosdb.youtube_api import YoutubeAPI

import youtube_transcript_api


logger = logging.getLogger(__name__)


class LockedItems:
    def __init__(self, items) -> None:
        self.lock = anyio.Lock()
        self.items = items


class Downloader:

    # PUBLIC: -------------------------------------------------------------
    def __init__(self, options=None):

        if "FIRESTORE_EMULATOR_HOST" in os.environ:
            logger.info("EMULATOR ACTIVE: %s",
                        os.environ["FIRESTORE_EMULATOR_HOST"])
        else:
            logger.info("USING LIVE DATABASE")
        # for k, v in os.environ.items():
        #     logger.debug('- %s = "%s"' % (k, v))

        logger.debug("ENVIRONMENT:")
        logger.debug(pprint.pformat(os.environ))
        self.options = options

        self.YT_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]
        self.db = DB()
        self.api = YoutubeAPI(self.db)
        self.QUOTA_EXCEPTIONS = (
            DB.QuotaExceeded,
            YoutubeAPI.QuotaExceeded,
            google.api_core.exceptions.ResourceExhausted
        )

    async def init(self):
        await self.db.init()
        self.capacity_limiter = anyio.CapacityLimiter(10)

    async def check_for_new_videos(self):
        logger.info("Sync start")
        async with anyio.create_task_group() as global_scope:
            await self.init()
            global_scope.start_soon(self._print_debug_info,
                                    name="Debug info")

            channel = await self._create_channel(self.YT_CHANNEL_ID)
            playlist_ids = await self._retrieve_all_playlist_ids(self.YT_CHANNEL_ID)

            await self._process_playlist_ids(playlist_ids, channel["snippet"]["title"])

            await anyio.wait_all_tasks_blocked()
            global_scope.cancel_scope.cancel()

        logger.info("Sync finished")

    @traced
    async def _process_playlist_ids(self, playlist_ids, channel_name):
        processed_video_ids = LockedItems(set())
        excluded_video_ids = LockedItems(set())
        processed_playlist_ids = LockedItems(set())
        try:
            async with anyio.create_task_group() as task_group:
                random.shuffle(playlist_ids)
                # main iterations:
                for playlist_id in playlist_ids:
                    task_group.start_soon(
                        self._process_playlist,
                        playlist_id,
                        channel_name,
                        task_group,
                        processed_video_ids,
                        excluded_video_ids,
                        processed_playlist_ids,
                        name="Playlist %s processor" % playlist_id
                    )

            # retrieve pending transcripts
            if self.options and not self.options.exclude_transcripts:
                logger.info("Retrieving transcripts")

                async with anyio.create_task_group() as transcript_downloaders:
                    async for video in self.db.stream("videos"):
                        transcript_downloaders.start_soon(
                            self._handle_transcript, video, name="Download transcript")

        except Exception as e:
            if _contains_exceptions(self.QUOTA_EXCEPTIONS, e):
                logger.error(e)
            else:
                raise e

        async with processed_video_ids.lock:
            if len(processed_video_ids.items):
                ids = list(processed_video_ids.items)
                await self.db.noquota_set("meta/video_ids", {
                    "videoIds": firestore.ArrayUnion(ids)
                })

    async def _process_playlist(self,
                                playlist_id,
                                channel_name,
                                task_group,
                                processed_video_ids,
                                excluded_video_ids,
                                processed_playlist_ids):

        async with processed_playlist_ids.lock:
            if playlist_id in processed_playlist_ids.items:
                return
            processed_playlist_ids.items.add(playlist_id)

        modified, playlist = await self.api.get_playlist_info(playlist_id)
        if not playlist:
            return

        if playlist["snippet"]["channelTitle"] != channel_name:
            return

        modified, playlist_items = await self.api.list_playlist_items(playlist_id)
        if not modified:
            return

        await self._create_playlist(playlist, playlist_items)
        # create videos:
        video_ids = playlist["videosdb"]["videoIds"]
        random.shuffle(video_ids)

        for video_id in video_ids:
            task_group.start_soon(
                self._process_video,
                video_id,
                playlist_id,
                processed_video_ids,
                excluded_video_ids,
                name="Video %s processor" % video_id
            )

    @ traced
    async def _process_video(self, video_id, playlist_id, processed_video_ids, excluded_video_ids):
        new = False
        async with processed_video_ids.lock:
            if video_id not in processed_video_ids.items:
                processed_video_ids.items.add(video_id)
                new = True

        if new:
            modified, video = await self.api.get_video_info(video_id)
            if not modified:
                return

            video = await self._create_video(video, [playlist_id])
            if not video:
                async with excluded_video_ids.lock:
                    excluded_video_ids.items.add(video_id)
                return

        async with excluded_video_ids.lock:
            if video_id in excluded_video_ids.items:
                return

        await self.db.set("videos/" + video_id, {
            "videosdb": {
                "playlists": firestore.ArrayUnion([playlist_id])
            }
        }, merge=True)

    @ traced
    async def _retrieve_all_playlist_ids(self, channel_id):
        modified, ids = await self.api.list_channelsection_playlist_ids(channel_id)
        modified, ids2 = await self.api.list_channel_playlist_ids(channel_id)
        if "DEBUG" in os.environ:
            playlists_ids_stream = stream.iterate(ids)
        else:
            playlists_ids_stream = stream.merge(ids, ids2)

        playlist_ids = set()
        async with playlists_ids_stream.stream() as streamer:
            async for playlist_id in streamer:
                playlist_ids.add(playlist_id)

        return list(playlist_ids)

    @ traced
    async def _create_channel(self, channel_id):

        modified, channel_info = await self.api.get_channel_info(channel_id)

        logger.info("Processing channel: " +
                    str(channel_info["snippet"]["title"]))

        await self.db.set("channel_infos/" + channel_id, channel_info, merge=True)
        return channel_info

    @ traced
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
        logger.info("Created playlist: " + playlist["snippet"]["title"])

    @ traced
    async def _create_video(self, video, playlist_ids=None):

        if not video:
            return
        # some playlists include videos from other channels
        # for now exclude those videos
        # in the future maybe exclude whole playlist

        if video["snippet"]["channelId"] != self.YT_CHANNEL_ID:
            return

        video_id = video["id"]
        playlist_ids = playlist_ids if playlist_ids else []

        video |= {
            "videosdb": {
                "slug":  slugify(video["snippet"]["title"]),
                "descriptionTrimmed": bleach.linkify(video["snippet"]["description"]),
                "durationSeconds": isodate.parse_duration(
                    video["contentDetails"]["duration"]).total_seconds(),
                "playlists": playlist_ids
            }
        }

        video["publishedAt"] = isodate.parse_datetime(
            video["snippet"]["publishedAt"])

        for stat, value in video["statistics"].items():
            video["statistics"][stat] = int(value)

        await self.db.set("videos/" + video_id, video, merge=True)

        logger.info("Created video: %s (%s)" %
                    (video_id, video["snippet"]["title"]))

        return video

    @ traced
    async def _fill_related_videos(self):

        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")

        doc = await self.db.get("meta/video_ids")
        randomized_ids = doc.get("videoIds")
        random.shuffle(randomized_ids)
        for video_id in randomized_ids:
            related_videos = await self.api.get_related_videos(video_id)

            for related in related_videos:
                # for now skip videos from other channels:
                if "snippet" in related and related["snippet"]["channelId"] \
                        != self.YT_CHANNEL_ID:
                    continue

                await self.db.update("videos/" + video_id, {
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
        await self.db.set("videos/" + v["id"], new_data, merge=True)

    async def _download_transcript(self, video_id):
        try:
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

    @ staticmethod
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

            await anyio.sleep(30)
