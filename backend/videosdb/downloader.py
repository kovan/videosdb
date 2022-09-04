import pprint
import signal
import anyio
from datetime import datetime
import random
import sys
import logging
import os
import isodate
import re
from slugify import slugify

from google.cloud import firestore
from google.oauth2 import service_account
import youtube_transcript_api
from aiostream import stream

from videosdb.youtube_api import YoutubeAPI, get_video_transcript

BASE_DIR = os.path.dirname(sys.modules[__name__].__file__)

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

    def __init__(self):
        project = os.environ["VIDEOSDB_FIREBASE_PROJECT"]
        config = os.environ["VIDEOSDB_CONFIG"]
        creds_json_path = os.path.join(
            BASE_DIR, "keys/%s.json" % config.strip('"'))

        logger.info("Current project: " + project)
        self.db = firestore.AsyncClient(project=project,
                                        credentials=service_account.Credentials.from_service_account_file(
                                            creds_json_path))
        # client_info = {
        #     "initial_ops_per_second": 10,
        #     "max_ops_per_second": 10
        # }

    async def init(self):
        # initialize meta table:
        doc_ref = self.db.collection("meta").document("meta")
        doc = await doc_ref.get()
        if not doc.exists or "videoIds" not in doc.to_dict():
            await doc_ref.set({"videoIds": list()})
        return self

    async def update_last_updated(self):
        return await self.db.collection("meta").document(
            "meta").set({"lastUpdated": datetime.now().isoformat()}, merge=True)

    async def get_video_count(self):
        doc = await self.db.collection("meta").document("meta").get()
        if doc.exists:
            return len(doc.to_dict()["videoIds"])
        else:
            return 0

    async def get_etag(self, collection, id):
        doc_ref = await self.db.collection(
            collection).document(id).get()

        return doc_ref.to_dict()["etag"] if doc_ref.exists else None

    class Doc:

        def __init__(self, doc_ref):
            self.doc_ref = doc_ref

        async def __aenter__(self):
            doc = await self.doc_ref.get()
            self.dict = doc.to_dict()
            return self.dict

        async def __aexit__(self, exc_type, exc, tb):
            await self.doc_ref.set(self.dict, merge=True)


def _print_debug_info(*streams):
    tasks = anyio.get_running_tasks()
    print('Running tasks:' + str(len(tasks)))
    pprint.pprint(tasks)
    for stream in streams:
        print(str(stream.statistics()))


async def _signal_handler(*streams):
    with anyio.open_signal_receiver(signal.SIGHUP, signal.SIGTERM) as signals:
        async for signum in signals:
            if signum == signal.SIGHUP:
                _print_debug_info(streams)
            elif signum == signal.SIGTERM:
                return


class Downloader:

    # PUBLIC: -------------------------------------------------------------
    def __init__(self, exclude_transcripts=False):
        logger.debug("ENVIRONMENT:")
        logger.debug(str(os.environ))
        self.exclude_transcripts = exclude_transcripts
        if exclude_transcripts:
            logger.debug("Excluding transcripts")
        self.YT_CHANNEL_ID = os.environ["YOUTUBE_CHANNEL_ID"]
        self.valid_video_ids = set()
        self.db = DB()
        self.api = YoutubeAPI()
        # signal.signal(signal.SIGHUP, handler)
        # signal.signal(signal.SIGINT, handler)

    async def init(self):
        await self.db.init()
        self.api = await YoutubeAPI.create(self.db.db)

    def check_for_new_videos(self):
        logger.info("Sync start")
        anyio.run(self.check_for_new_videos_async)
        logger.info("Sync finished")

    async def check_for_new_videos_async(self):
        await self.init()

        try:
            await self._start()

        except YoutubeAPI.QuotaExceededError as e:
            logger.error(e)
        except anyio.ExceptionGroup as group:
            _filter_exceptions(
                group, YoutubeAPI.QuotaExceededError, logger.error)
        finally:
            await anyio.wait_all_tasks_blocked()
            # await self.api.aclose()
            await self.db.update_last_updated()

    async def _start(self):
        logger.info("Currently there are %s videos in the DB",
                    await self.db.get_video_count())

        video_sender, video_receiver = anyio.create_memory_object_stream()
        playlist_sender, playlist_receiver = anyio.create_memory_object_stream()

        async with anyio.create_task_group() as global_scope:
            global_scope.start_soon(_signal_handler,
                                    video_receiver, video_receiver, playlist_sender, playlist_receiver,
                                    name="Signal handler")
            async with anyio.create_task_group() as processors:
                processors.start_soon(self._playlist_retriever,
                                      playlist_sender, name="Playlist retriever")
                processors.start_soon(self._playlist_processor,
                                      playlist_receiver, video_sender, name="Playlist receiver")
                processors.start_soon(self._video_processor,
                                      video_receiver, name="Video receiver")

            if "DEBUG" not in os.environ:
                # separate so that it uses remaining quota
                await self._fill_related_videos()
            global_scope.cancel_scope.cancel()

    async def _playlist_retriever(self, playlist_sender):
        with playlist_sender:

            channel_id = self.YT_CHANNEL_ID
            result, channel_info = await self._get_with_etag("channel_infos", self.api.get_channel_info, channel_id)

            if result == 304:  # Not modified
                return

            logger.info("Processing channel: " +
                        str(channel_info["snippet"]["title"]))
            self.YT_CHANNEL_NAME = str(channel_info["snippet"]["title"])
            await self.db.db.collection("channel_infos").document(channel_id).set(channel_info)

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

    async def _playlist_processor(self, playlist_receiver, video_sender):
        processed_playlist_ids = set()
        with video_sender:
            async with anyio.create_task_group() as nursery:
                async for playlist_id in playlist_receiver:
                    if playlist_id in processed_playlist_ids:
                        continue
                    nursery.start_soon(
                        self._process_playlist, playlist_id, video_sender, name="PL " + playlist_id)

                    processed_playlist_ids.add(playlist_id)

    async def _video_processor(self, video_receiver):

        # One stream per video, because when a video is found in a new playlist,
        # the video has to already exist in the DB for the playlist to be added.
        # This way, DB operations on a video are always in sequential order.
        video_streams = dict()
        async with anyio.create_task_group() as nursery:
            try:
                async with anyio.create_task_group() as nursery2:
                    async for video_id, playlist_id in video_receiver:
                        logger.debug("Processing " +
                                     video_id + " " + playlist_id)
                        if video_id not in video_streams:
                            snd_stream, rcv_stream = anyio.create_memory_object_stream()
                            nursery.start_soon(
                                self._process_video, rcv_stream, name="VID " + video_id)
                            video_streams[video_id] = snd_stream
                            task = {
                                "action": "create",
                                "video_id": video_id
                            }
                            await video_streams[video_id].send(task)

                        if playlist_id:
                            task = {
                                "action": "add_playlist",
                                "video_id": video_id,
                                "playlist_id": playlist_id
                            }

                            nursery2.start_soon(
                                video_streams[video_id].send, task, name="VID_TASK " + str(task))
            finally:
                for stream in video_streams.values():
                    stream.close()

                meta_doc = self.db.db.collection("meta").document("meta")
                async with DB.Doc(meta_doc) as meta:
                    ids = set(meta["videoIds"])
                    ids.update(self.valid_video_ids)
                    meta["videoIds"] = list(ids)

    async def _process_video(self, task_receiver):
        breaking = False
        self_video_id = None
        playlist_ids = []

        try:

            async for task in task_receiver:

                if breaking:
                    continue

                with anyio.fail_after(10):
                    if task["action"] == "create":
                        result = await self._create_video(task["video_id"])
                        if not result:
                            breaking = True
                            continue
                        self_video_id = task["video_id"]

                    elif task["action"] == "add_playlist":
                        playlist_ids.append(task["playlist_id"])

                    else:
                        raise ValueError()
        finally:
            if not self_video_id:
                return
            await self.db.db.collection("videos").document(self_video_id).set({
                "videosdb": {
                    "playlists": playlist_ids
                }
            }, merge=True)
            logger.debug("Wrote playlist info for video: " +
                         str(self_video_id))

    async def _process_playlist(self, playlist_id, video_sender):
        playlist = await self.api.get_playlist_info(playlist_id)
        if not playlist:
            return

        if playlist["snippet"]["channelTitle"] != self.YT_CHANNEL_NAME:
            return

        playlist = playlist if playlist["snippet"]["title"] != "Uploads from " + \
            playlist["snippet"]["channelTitle"] else None

        items = []
        async for item in self.api.list_playlist_items(playlist_id):
            if item["snippet"]["channelId"] != self.YT_CHANNEL_ID:
                continue
            video_id = item["snippet"]["resourceId"]["videoId"]
            items.append(item)
            await video_sender.send((video_id, playlist_id))

        if playlist:
            await self._create_playlist(playlist, items)

    async def _create_playlist(self, playlist, items):
        video_count = 0
        last_updated = None

        for item in items:
            video_count += 1
            video_date = isodate.parse_datetime(
                item["snippet"]["publishedAt"])
            if not last_updated or video_date > last_updated:
                last_updated = video_date

        playlist["videosdb"] = dict()
        playlist["videosdb"]["slug"] = slugify(
            playlist["snippet"]["title"])
        playlist["videosdb"]["videoCount"] = video_count
        playlist["videosdb"]["lastUpdated"] = last_updated

        await self.db.db.collection("playlists").document(playlist["id"]).set(playlist)
        logger.info("Created playlist: " + playlist["snippet"]["title"])

    async def _create_video(self, video_id):
        video = await self.api.get_video_info(video_id)
        if not video:
            return
        # some playlists include videos from other channels
        # for now exclude those videos
        # in the future maybe exclude whole playlist

        if video["snippet"]["channelId"] != self.YT_CHANNEL_ID:
            return

        old_video_doc = await self.db.db.collection("videos").document(video_id).get()

        custom_attrs = dict()

        old_video = old_video_doc.to_dict() if old_video_doc.exists else None

        if not self.exclude_transcripts:
            if (not old_video or
                "videosdb" not in old_video or
                "transcript_status" not in old_video["videosdb"] or
                    old_video["videosdb"]["transcript_status"] == "pending"):
                transcript, new_status = await self._download_transcript(video_id)
                custom_attrs["transcript_status"] = new_status
                if transcript:
                    custom_attrs["transcript"] = transcript

        custom_attrs["slug"] = slugify(
            video["snippet"]["title"])
        custom_attrs["descriptionTrimmed"] = self._description_trimmed(
            video["snippet"]["description"])
        custom_attrs["durationSeconds"] = isodate.parse_duration(
            video["contentDetails"]["duration"]).total_seconds()

        video["videosdb"] = custom_attrs
        video["snippet"]["publishedAt"] = isodate.parse_datetime(
            video["snippet"]["publishedAt"])
        for stat, value in video["statistics"].items():
            video["statistics"][stat] = int(value)

        await self.db.db.collection("videos").document(
            video_id).set(video, merge=True)

        self.valid_video_ids.add(video["id"])
        logger.info("Created video: " + video["snippet"]["title"])

        return video

    async def _fill_related_videos(self):

        # use remaining YT API daily quota to download a few related video lists:
        logger.info("Filling related videos info.")

        async with anyio.create_task_group():
            meta_doc = await self.db.db.collection("meta").document("meta").get()
            randomized_ids = meta_doc.to_dict()["videoIds"]
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

    async def _get_with_etag(self, collection, api_func, id):
        etag = await self.db.get_etag(collection, id)
        result = await api_func(id, etag)

        if type(result) == int:
            return result, None
        return 200, result

    @staticmethod
    async def _download_transcript(video_id):
        try:
            logger.info(
                "Downloading transcript for video: " + str(video_id))
            with anyio.fail_after(60):
                transcript = await anyio.to_thread.run_sync(
                    get_video_transcript, video_id)

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
                logger.info(str(e) + " New status: unavailable")
                return None, "unavailable"

    @staticmethod
    def _description_trimmed(description):
        if not description:
            return
        match = re.search("#Sadhguru", description)
        if match and match.start() != -1:
            return description[:match.start()]
        return description
