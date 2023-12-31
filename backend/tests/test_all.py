# type: ignore
import asyncio
#import memory_profiler
import unittest
from unittest.mock import MagicMock

from google.cloud import firestore
import datetime
import json
import logging
import os
import pprint
import sys
import requests
import aiounittest
import anyio
import redis.asyncio as redis
import respx
from dotenv import load_dotenv
from google.api_core.datetime_helpers import DatetimeWithNanoseconds
from httpx import Response
from videosdb.db import DB
from videosdb.downloader import Downloader, ExportToEmulatorTask, RetrievePendingTranscriptsTask, VideoProcessor
from videosdb.publisher import TwitterPublisher
from videosdb.youtube_api import Cache, YoutubeAPI
import tracemalloc

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(str(sys.modules[__name__].__file__))
DATA_DIR = BASE_DIR + "/test_data"


class PatchedTestCase(aiounittest.AsyncTestCase):

    def get_event_loop(self):  # workaround for bug
        self.my_loop = asyncio.get_event_loop()
        return self.my_loop

    def setUp(self):
        self.get_event_loop()
        self.my_loop.run_until_complete(self.myAsyncSetUp())

    async def myAsyncSetUp(self):
        pass


def read_file(file):
    with open(f"{DATA_DIR}/{file}") as f:
        return json.load(f)


class DownloaderTest(PatchedTestCase):
    VIDEO_IDS = {'ZhI-stDIlCE', 'ed7pFle2yM8', 'J-1WVf5hFIk',
                 'FBYoZ-FgC84', 'QEkHcPt-Vpw', 'HADeWBBb1so', 'gavq4LM8XK0'}
    PLAYLIST_ID = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"
    ALL_VIDEOS_PLAYLIST_ID = "UUcYzLCs3zrQIBVHYA1sK2sw"
    VIDEO_ID = "HADeWBBb1so"
    EMULATOR_HOST = "127.0.0.1:46456"

    YT_CHANNEL_ID = "UCcYzLCs3zrQIBVHYA1sK2sw"

    def setUp(self):
        self.get_event_loop()
        self.my_loop.run_until_complete(self._clear_dbs())
        self.mocked_api.start()
        self.addCleanup(self.mocked_api.stop)

        self.mydb = DB()
        self.downloader = Downloader(
            db=self.mydb, redis_db_n=1, channel_id=self.YT_CHANNEL_ID)
        self.video_processor = VideoProcessor(
            self.mydb, YoutubeAPI(self.mydb), self.YT_CHANNEL_ID)

    async def _clear_dbs(self):
        requests.delete(
            f"http://{self.EMULATOR_HOST}/emulator/v1/projects/demo-project/databases/(default)/documents")
        await self.redis.flushdb()

    @classmethod
    def setUpClass(cls):
        load_dotenv("common/env/testing.txt")
        if "FIRESTORE_EMULATOR_HOST" not in os.environ:

            os.environ["FIRESTORE_EMULATOR_HOST"] = cls.EMULATOR_HOST

        logger.debug(pprint.pformat(os.environ))

        # DB.wait_for_port(60.0)

        cls.redis = redis.Redis(db=1)
        cls.db = DB.get_client()
        cls.createMocks()

    @classmethod
    def createMocks(cls):

        cls.mocked_api = respx.mock(base_url=YoutubeAPI.get_root_url(),
                                    assert_all_called=False)

        cls.mocked_api.route(
            path="/channels",
            name="channels"
        ).mock(
            Response(200, json=read_file(
                f"channel-{cls.YT_CHANNEL_ID}.response.json"))
        )

        cls.mocked_api.route(
            path="/channelSections",
            name="channelSections"
        ).mock(
            Response(200, json=read_file(
                f"channelSections-{cls.YT_CHANNEL_ID}.response.json"))
        )

        cls.mocked_api.route(
            path="/playlists",
            name="playlists",
            params={"id": cls.PLAYLIST_ID}
        ).mock(
            return_value=Response(200, json=read_file(
                f"playlist-{cls.PLAYLIST_ID}.response.json"))

        )

        cls.mocked_api.route(
            path="/playlists",
            name="playlistAllVideos",
            params={"id": cls.ALL_VIDEOS_PLAYLIST_ID}
        ).mock(
            return_value=Response(200, json=read_file(
                f"playlist-{cls.ALL_VIDEOS_PLAYLIST_ID}.response.json"))
        )

        cls.mocked_api.route(
            path="/playlists",
            name="playlistForChannel",
            params={"channelId": cls.YT_CHANNEL_ID}
        ).mock(
            return_value=Response(200, json=read_file(
                f"playlist-empty.response.json"))
        )

        cls.mocked_api.route(
            path="/playlistItems",
            name="playlistItems",
            params={"playlistId": cls.PLAYLIST_ID}
        ).mock(
            side_effect=[
                Response(200, json=read_file(
                    f"playlistItems-{cls.PLAYLIST_ID}.response.0.json")),
                Response(200, json=read_file(
                    f"playlistItems-{cls.PLAYLIST_ID}.response.1.json"))
            ]
        )

        cls.mocked_api.route(
            path="/playlistItems",
            name="playlistItemsAllVideos",
            params={"playlistId": cls.ALL_VIDEOS_PLAYLIST_ID}
        ).mock(
            return_value=Response(200, json=read_file(
                f"playlistItems-{cls.ALL_VIDEOS_PLAYLIST_ID}.response.json")),

        )

        for vid in cls.VIDEO_IDS:
            cls.mocked_api.route(
                path="/videos",
                params={"id": vid}
            ).mock(
                return_value=Response(200, json=read_file(
                    f"video-{vid}.response.json"))
            )

    @ respx.mock
    async def test_all(self):

        await self.downloader.check_for_new_videos()

        self.assertEqual(self.mocked_api["playlists"].call_count, 1)
        self.assertEqual(self.mocked_api["playlistForChannel"].call_count, 1)
        self.assertEqual(self.mocked_api["playlistItems"].call_count, 2)
        self.assertEqual(self.mocked_api["playlistAllVideos"].call_count, 1)
        self.assertEqual(
            self.mocked_api["playlistItemsAllVideos"].call_count, 1)
        self.assertEqual(
            self.mocked_api["channelSections"].call_count, 1)
        self.assertEqual(
            self.mocked_api["channels"].call_count, 1)

        pls = [doc.get("id") async for doc in self.db.collection("playlists").stream()]
        self.assertEqual(len(pls), 1)
        self.assertEqual(pls[0], self.PLAYLIST_ID)

        # check that VideoProcessor works correctly:

        excluded_video_id = 'FBYoZ-FgC84'
        videos = [doc async for doc in self.db.collection("videos").stream()]
        self.assertEqual(len(videos), 6)

        for video in videos:
            self.assertIn(video.get("id"), self.VIDEO_IDS)
            for plid in video.get("videosdb.playlists"):
                self.assertIn(
                    plid, [self.PLAYLIST_ID])
            self.assertNotEqual(video.get("id"), excluded_video_id)
            self.assertIn("slug", video.get("videosdb"))

        # check that one playlist is processed correctly:

        playlist = (await self.db.document("playlists/" + self.PLAYLIST_ID).get()).to_dict()
        self.assertEqual(playlist["kind"], "youtube#playlist")
        self.assertEqual(playlist["id"], self.PLAYLIST_ID)

        videosdb_dict = playlist["videosdb"]
        self.assertEqual(
            videosdb_dict["slug"], 'how-to-be-really-successful-sadhguru-answers')
        self.assertEqual(videosdb_dict["videoCount"], 7)
        self.assertEqual(videosdb_dict["lastUpdated"], DatetimeWithNanoseconds(
            2022, 7, 6, 12, 18, 45, tzinfo=datetime.timezone.utc))
        self.assertEqual(set(videosdb_dict["videoIds"]), self.VIDEO_IDS)

        # check that one video is processed correctly:
        self.VIDEO_ID = "HADeWBBb1so"

        video = (await self.db.document("videos/" + self.VIDEO_ID).get()).to_dict()
        self.assertEqual(video["kind"], "youtube#video")
        self.assertEqual(video["id"], self.VIDEO_ID)
        self.assertEqual(set(video["videosdb"]["playlists"]),
                         {self.PLAYLIST_ID})
        self.assertEqual(video["videosdb"]["slug"],
                         "fate-god-luck-or-effort-what-decides-your-success-sadhguru")
        self.assertIn("descriptionTrimmed", video["videosdb"])
        self.assertEqual(video["videosdb"]["durationSeconds"], 470.0)
        self.assertTrue(isinstance(
            video["snippet"]["publishedAt"], datetime.datetime))
        self.assertIn("statistics", video)

        # check that cache pages were written

        cache_id = Cache.key_func("/playlistItems", {
            "part": "snippet",
            "playlistId": "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"
        })
        cached = json.loads(await self.redis.get(cache_id))
        self.assertEqual(cached["etag"], "WMsDqOm6raLZmN3legOjPB7T3XI")
        self.assertEqual(cached["n_pages"], 2)
        cached_page_0 = json.loads(await self.redis.get(cache_id + "_page_0"))
        cached_page_1 = json.loads(await self.redis.get(cache_id + "_page_1"))
        self.assertEqual(
            cached_page_0["etag"], read_file(f"playlistItems-{self.PLAYLIST_ID}.response.0.json")["etag"])
        self.assertEqual(
            cached_page_1["etag"], read_file(f"playlistItems-{self.PLAYLIST_ID}.response.1.json")["etag"])

    async def test_export_to_emulator(self):
        video = read_file(f"video-{self.VIDEO_ID}.response.json")["items"][0]
        test_path = "test_collection/test_document"
        test_doc_ref = self.db.document(test_path)
        test_doc_dict = {
            "this is a test": True
        }
        await test_doc_ref.set(test_doc_dict)

        mock = MagicMock()
        mock.export_to_emulator_host = self.EMULATOR_HOST
        async with anyio.create_task_group() as tg:

            task = ExportToEmulatorTask(
                self.mydb,
                mock,
                nursery=tg)

            self.assertTrue(task.enabled)
            self.assertIsNotNone(task.emulator_client)

            await task(video)

            await task.export_pending_collections()

            exported_doc_ref = task.emulator_client.document(test_path)
            exported_doc_dict = (await exported_doc_ref.get()).to_dict()
            self.assertEqual(
                exported_doc_dict,
                test_doc_dict
            )

        # async def test_transcript_downloading(self):

        #     video = self.raw_responses["videos"][self.VIDEO_ID]["items"][0]

        #     async with anyio.create_task_group() as tg:
        #         task = RetrievePendingTranscriptsTask(
        #             self.mydb, nursery=tg)
        #         task.enabled = True
        #         await task(video)

        #     self.assertIn("transcript", video["videosdb"])
        #     self.assertIn("transcript_status", video["videosdb"])


# @memory_profiler.profile
def main():
    tracemalloc.start()
    snapshot = tracemalloc.take_snapshot()
    try:
        unittest.main()
    except KeyboardInterrupt as e:
        snapshot2 = tracemalloc.take_snapshot()
        print("Took snapshot")


if __name__ == "__main__":
    print("Running tests...")
    main()
