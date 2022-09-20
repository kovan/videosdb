import logging
import bleach
import os
import pprint
from google.cloud import firestore
import re
import random
from datetime import datetime
import anyio
import fnc
import isodate
from aiostream import stream
from autologging import traced
import google.api_core.exceptions
from slugify import slugify
from videosdb.youtube_api import YoutubeAPI, get_video_transcript
from videosdb.db import DB
import youtube_transcript_api


logger = logging.getLogger(__name__)


def _filter_exceptions(group: anyio.ExceptionGroup, exception_types, handler_func):
    unhandled_exceptions = []
    for e in group.exceptions:
        if type(e) in exception_types:
            handler_func(e)
        else:
            unhandled_exceptions.append(e)

    if unhandled_exceptions:
        raise anyio.ExceptionGroup(unhandled_exceptions)


class Downloader:

    # PUBLIC: -------------------------------------------------------------
    def __init__(self, options=None):

        if "FIRESTORE_EMULATOR_HOST" in os.environ:
            logger.info("USING EMULATOR")
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

            meta_doc = await self.db.get("meta/meta")
            last_playlist_id = None
            processed_video_ids = set()
            try:

                channel_id = self.YT_CHANNEL_ID
                channel_info = await self._retrieve_channel(channel_id)
                all_uploads_playlist_id = channel_info["contentDetails"]["relatedPlaylists"]["uploads"]
                channel_name = str(channel_info["snippet"]["title"])

                if "DEBUG" in os.environ:
                    playlists_ids_stream = stream.iterate(
                        self.api.list_channelsection_playlist_ids(channel_id)
                    )
                else:
                    playlists_ids_stream = stream.merge(
                        self.api.list_channelsection_playlist_ids(channel_id),
                        self.api.list_channel_playlist_ids(channel_id)
                    )

                processed_playlist_ids = set()
                excluded_video_ids = set()

                playlist_ids = set()
                async with playlists_ids_stream.stream() as streamer:
                    async for playlist_id in streamer:
                        playlist_ids.add(playlist_id)

                playlist_ids = list(playlist_ids)
                playlist_ids.sort()

                last_playlist_id = meta_doc.to_dict().get("lastPlaylistId")

                # start from where we left it:
                if last_playlist_id:
                    try:
                        i = playlist_ids.index(last_playlist_id)
                        playlist_ids = playlist_ids[i:] + playlist_ids[:i]
                    except ValueError:
                        pass

                # main iterations:
                for playlist_id in playlist_ids:

                    if playlist_id in processed_playlist_ids:
                        continue
                    processed_playlist_ids.add(playlist_id)
                    last_playlist_id = playlist_id

                    playlist = await self._download_playlist(playlist_id, channel_name)
                    if not playlist:
                        continue

                    if playlist_id != all_uploads_playlist_id:
                        await self._create_playlist(playlist)

                    # create videos:
                    for video_id in playlist["videosdb"]["videoIds"]:
                        if video_id not in processed_video_ids:
                            processed_video_ids.add(video_id)
                            video = await self._create_video(video_id, [playlist_id])
                            if not video:
                                excluded_video_ids.add(video_id)
                                continue

                        if video_id in excluded_video_ids:
                            continue

                        await self.db.update("videos/" + video_id, {
                            "videosdb.playlists":
                            firestore.ArrayUnion([playlist_id])
                        })

                if self.options.fill_related_videos and "DEBUG" not in os.environ:
                    # separate so that it uses remaining quota
                    await self._fill_related_videos()

                # retrieve pending transcripts
                if not self.options.exclude_transcripts:
                    logger.info("Retrieving transcripts")
                    async for video in self.db.stream("videos"):
                        global_scope.start_soon(
                            self._handle_transcript, video, name="Download transcript")

            except Exception as e:
                if type(e) in self.QUOTA_EXCEPTIONS:
                    logger.error(e)
                else:
                    raise e
            except anyio.ExceptionGroup as group:
                _filter_exceptions(
                    group, self.QUOTA_EXCEPTIONS, logger.error)
            finally:
                new_meta = {
                    "lastUpdated": datetime.now().isoformat(),
                    "lastPlaylistId": last_playlist_id,
                }
                if processed_video_ids:
                    new_meta["videoIds"] = firestore.ArrayUnion(
                        list(processed_video_ids))
                await self.db.update("meta/meta", new_meta)

            await anyio.wait_all_tasks_blocked()

            global_scope.cancel_scope.cancel()

        logger.info("Sync finished")

    @ traced
    async def _retrieve_channel(self, channel_id):

        channel_info = await self.api.get_channel_info(channel_id)

        logger.info("Processing channel: " +
                    str(channel_info["snippet"]["title"]))

        await self.db.set("channel_infos/" + channel_id, channel_info, merge=True)
        return channel_info

    @ traced
    async def _download_playlist(self, playlist_id, channel_name):
        playlist = await self.api.get_playlist_info(playlist_id)

        if not playlist:
            return

        if playlist["snippet"]["channelTitle"] != channel_name:
            return

        result = await self.api.list_playlist_items(playlist_id)

        video_count = 0
        last_updated = None
        video_ids = []

        async for item in result:
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
                "slug": slugify(playlist["snippet"]["title"]),
                "videoCount": video_count,
                "lastUpdated": last_updated,
                "lastRetrieved": datetime.now().isoformat(),
                "videoIds": video_ids
            }
        }

        return playlist

    @traced
    async def _create_playlist(self, playlist):
        if not playlist:
            return

        await self.db.set("playlists/" + playlist["id"], playlist, merge=True)
        logger.info("Created playlist: " + playlist["snippet"]["title"])

    @traced
    async def _create_video(self, video_id, playlist_ids=None):
        video = await self.api.get_video_info(video_id)

        if not video:
            return
        # some playlists include videos from other channels
        # for now exclude those videos
        # in the future maybe exclude whole playlist

        if video["snippet"]["channelId"] != self.YT_CHANNEL_ID:
            return

        video |= {
            "videosdb": {
                "slug":  slugify(video["snippet"]["title"]),
                "descriptionTrimmed": bleach.linkify(video["snippet"]["description"]),
                "durationSeconds": isodate.parse_duration(
                    video["contentDetails"]["duration"]).total_seconds(),
                "playlists": playlist_ids if playlist_ids else [],
                "lastRetrieved": datetime.now().isoformat()
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

    @traced
    async def _fill_related_videos(self):

        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")

        async with anyio.create_task_group():
            meta_doc = await self.db.get("meta/meta")
            randomized_ids = meta_doc.get("videoIds")
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

            await anyio.sleep(30)
