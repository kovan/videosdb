# type: ignore
import asyncio
import datetime
import json
import logging
import os
import pprint
import sys

import aiounittest
import anyio
import redis.asyncio as redis
import respx
from dotenv import load_dotenv
from google.api_core.datetime_helpers import DatetimeWithNanoseconds
from httpx import Response
from videosdb.db import DB
from videosdb.downloader import Downloader, RetrievePendingTranscriptsTask, VideoProcessor
from videosdb.publisher import TwitterPublisher
from videosdb.youtube_api import Cache, YoutubeAPI

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(str(sys.modules[__name__].__file__))
DATA_DIR = BASE_DIR + "/test_data"


def read_response_files(video_ids):
    raw_responses = {}
    with open(DATA_DIR + "/playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json") as f:
        raw_responses["playlists"] = json.load(f)
    with open(DATA_DIR + "/playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.1.json") as f:
        raw_responses["playlistItems.1"] = json.load(f)
    with open(DATA_DIR + "/playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.2.json") as f:
        raw_responses["playlistItems.2"] = json.load(f)

    raw_responses["videos"] = {}
    for vid in video_ids:
        with open(f"{DATA_DIR}/video-{vid}.response.json") as f:
            raw_responses["videos"][vid] = json.load(f)

    return raw_responses


class PatchedTestCase(aiounittest.AsyncTestCase):

    def get_event_loop(self):  # workaround for bug
        self.my_loop = asyncio.get_event_loop()
        return self.my_loop

    def setUp(self):
        self.get_event_loop()
        self.my_loop.run_until_complete(self.myAsyncSetUp())

    async def myAsyncSetUp(self):
        pass


class DownloaderTest(PatchedTestCase):
    VIDEO_IDS = {'ZhI-stDIlCE', 'ed7pFle2yM8', 'J-1WVf5hFIk',
                 'FBYoZ-FgC84', 'QEkHcPt-Vpw', 'HADeWBBb1so', 'gavq4LM8XK0'}
    PLAYLIST_ID = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"

    VIDEO_ID = "HADeWBBb1so"

    def setUp(self):

        self.get_event_loop()
        self.my_loop.run_until_complete(self._clear_dbs())
        self.mocked_api.start()
        self.addCleanup(self.mocked_api.stop)

        self.YT_CHANNEL_ID = "UCcYzLCs3zrQIBVHYA1sK2sw"
        self.mydb = DB(prefix="test_")
        self.downloader = Downloader(db=self.mydb, redis_db_n=1)
        self.video_processor = VideoProcessor(
            self.mydb, YoutubeAPI(self.mydb), self.YT_CHANNEL_ID)

    async def _clear_dbs(self):
        async for col in self.db.collections():
            await self.db.recursive_delete(col)
        await self.redis.flushdb()

    @classmethod
    def setUpClass(cls):
        load_dotenv("common/env/testing.txt")
        if "FIRESTORE_EMULATOR_HOST" not in os.environ:

            os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:46456"

        logger.debug(pprint.pformat(os.environ))

        # DB.wait_for_port(60.0)

        cls.redis = redis.Redis(db=1)
        cls.db = DB.get_client()
        cls.createMocks()

    @classmethod
    def createMocks(cls):
        cls.raw_responses = read_response_files(cls.VIDEO_IDS)
        cls.mocked_api = respx.mock(base_url=YoutubeAPI.get_root_url(),
                                    assert_all_called=False)

        cls.mocked_api.route(
            path="/playlists",
            name="playlists"
        ).mock(
            Response(200, json=cls.raw_responses["playlists"])
        )

        cls.mocked_api.route(
            path="/playlistItems",
            name="playlistItems"
        ).mock(
            side_effect=[
                Response(200, json=cls.raw_responses["playlistItems.1"]),
                Response(200, json=cls.raw_responses["playlistItems.2"])
            ]
        )

        for vid in cls.VIDEO_IDS:
            cls.mocked_api.route(
                path="/videos",
                params={"id": vid}
            ).mock(
                return_value=Response(
                    200, json=cls.raw_responses["videos"][vid])
            )

    @ respx.mock
    async def test_process_playlist_ids(self):

        await self.downloader._process_playlist_ids(
            [self.PLAYLIST_ID], "Sadhguru", self.video_processor)

        self.assertEqual(self.mocked_api["playlists"].call_count, 1)
        self.assertEqual(self.mocked_api["playlistItems"].call_count, 2)

        pls = [doc.get("id") async for doc in self.db.collection("test_playlists").stream()]
        self.assertEqual(len(pls), 1)
        self.assertEqual(pls[0], self.PLAYLIST_ID)

        # check that VideoProcessor works correctly:
        await self.video_processor.close()

        self.assertEqual(
            self.video_processor._excluded_video_ids.item, {"FBYoZ-FgC84"})
        self.assertEqual(self.video_processor._video_to_playlist_list.item, {
            'FBYoZ-FgC84': [],
            'HADeWBBb1so': [self.PLAYLIST_ID],
            'QEkHcPt-Vpw': [self.PLAYLIST_ID],
            'ZhI-stDIlCE': [self.PLAYLIST_ID],
            'ed7pFle2yM8': [self.PLAYLIST_ID],
            'gavq4LM8XK0': [self.PLAYLIST_ID],
            'J-1WVf5hFIk': [self.PLAYLIST_ID]
        })
        videos = [doc async for doc in self.db.collection("test_videos").stream()]

        for video in videos:
            self.assertIn(video.get("id"), self.VIDEO_IDS)
            self.assertEqual([self.PLAYLIST_ID],
                             video.get("videosdb.playlists"))
            self.assertIn("slug", video.get("videosdb"))

        # check that one playlist is processed correctly:

        playlist = (await self.db.document("test_playlists/" + self.PLAYLIST_ID).get()).to_dict()
        self.assertEqual(playlist["kind"], "youtube#playlist")
        self.assertEqual(playlist["id"], self.PLAYLIST_ID)

        vdb = playlist["videosdb"]
        self.assertEqual(
            vdb["slug"], 'how-to-be-really-successful-sadhguru-answers')
        self.assertEqual(vdb["videoCount"], 7)
        self.assertEqual(vdb["lastUpdated"], DatetimeWithNanoseconds(
            2022, 7, 6, 12, 18, 45, tzinfo=datetime.timezone.utc))
        self.assertEqual(set(vdb["videoIds"]), self.VIDEO_IDS)

        # check that one video is processed correctly:
        self.VIDEO_ID = "HADeWBBb1so"

        video = (await self.db.document("test_videos/" + self.VIDEO_ID).get()).to_dict()
        self.assertEqual(video["kind"], "youtube#video")
        self.assertEqual(video["id"], self.VIDEO_ID)
        self.assertEqual(video["videosdb"]["playlists"], [self.PLAYLIST_ID])
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
            cached_page_0["etag"], self.raw_responses["playlistItems.1"]["etag"])
        self.assertEqual(
            cached_page_1["etag"], self.raw_responses["playlistItems.2"]["etag"])

        # check that pages were used:

    # async def test_firestore_behavior(self):
    #     a = await self.db.document("test_videos/" + "asdfsdf").set({
    #         "videosdb": {
    #             "playlists": firestore.ArrayUnion(["sdjfpoasdjf"])
    #         }
    #     }, merge=True)
    #     b = await self.db.document("test_videos/" + "asdfsdf").set({
    #         "videosdb": {
    #             "playlists": firestore.ArrayUnion(["sdfsdf"])
    #         }
    #     }, merge=True)

    #     c = await self.db.document("test_videos/" + "asdfsdf").get()
    #     self.assertEqual(
    #         {'videosdb': {'playlists': ['sdjfpoasdjf', 'sdfsdf']}}, c.to_dict())

    # async def test_transcript_downloading(self):

    #     video = self.raw_responses["videos"][self.VIDEO_ID]["items"][0]

    #     async with anyio.create_task_group() as tg:
    #         task = RetrievePendingTranscriptsTask(
    #             self.mydb, nursery=tg)
    #         task.enabled = True
    #         await task(video)

    #     self.assertIn("transcript", video["videosdb"])
    #     self.assertIn("transcript_status", video["videosdb"])
