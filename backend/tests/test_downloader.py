import datetime
from google.api_core.datetime_helpers import DatetimeWithNanoseconds
import asyncio
import pprint
from httpx import Response
import respx
import os
import aiounittest
import json
from google.cloud import firestore
from dotenv import load_dotenv
from videosdb.downloader import Downloader
from videosdb.db import DB
import os
import logging
import sys
from videosdb.publisher import TwitterPublisher

from videosdb.youtube_api import YoutubeAPI

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(sys.modules[__name__].__file__)
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


class MockedAPIMixin:

    def setUp(self):

        self.get_event_loop()
        self.my_loop.run_until_complete(self._clear_db())
        self.mocked_api.start()
        self.addCleanup(self.mocked_api.stop)

    async def _clear_db(self):
        logger.debug("clearing db")
        async for col in self.db.collections():
            await self.db.recursive_delete(col)

    @classmethod
    def setUpClass(cls):
        load_dotenv("common/env/testing.txt")
        if "FIRESTORE_EMULATOR_HOST" not in os.environ:

            os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:46456"

        logger.debug(pprint.pformat(os.environ))

        # DB.wait_for_port(60.0)

        project = os.environ["FIREBASE_PROJECT"]
        config = os.environ["VIDEOSDB_CONFIG"]
        cls.db = DB.setup(project, config)
        cls.mocked_api = respx.mock(base_url=YoutubeAPI.get_root_url(),
                                    assert_all_called=False)
        cls.createMocks()

    @classmethod
    def createMocks(cls):
        playlists = cls.mocked_api.get(path="/playlists", name="playlists")
        with open(DATA_DIR + "/playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json") as f:
            playlists.return_value = Response(200, json=json.load(f))

        playlistItems = cls.mocked_api.get(
            path="/playlistItems", name="playlistItems")

        side_effects = []
        with open(DATA_DIR + "/playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.1.json") as f:
            side_effects.append(Response(200, json=json.load(f)))
        with open(DATA_DIR + "/playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.2.json") as f:
            side_effects.append(Response(200, json=json.load(f)))
        playlistItems.side_effect = side_effects

        videos = cls.mocked_api.get(path="/videos",  name="videos")
        with open(DATA_DIR + "/video-HADeWBBb1so.response.json") as f:
            videos.return_value = Response(200, json=json.load(f))


class DownloaderTest(MockedAPIMixin, PatchedTestCase):
    VIDEO_IDS = ['ZhI-stDIlCE', 'ed7pFle2yM8', 'J-1WVf5hFIk',
                 'FBYoZ-FgC84', 'QEkHcPt-Vpw', 'HADeWBBb1so', 'gavq4LM8XK0']
    PLAYLIST_ID = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"

    @respx.mock
    async def test_process_playlist_ids(self):
        video_id = "HADeWBBb1so"

        await Downloader()._process_playlist_ids(
            [self.PLAYLIST_ID], "Sadhguru")

        self.assertEqual(self.mocked_api["playlists"].call_count, 1)
        self.assertEqual(self.mocked_api["playlistItems"].call_count, 2)

        doc = await self.db.document("videos/" + video_id).get()
        self.assertTrue(doc.exists)

        pls = [doc.get("id") async for doc in self.db.collection("playlists").stream()]
        self.assertEqual(len(pls), 1)
        self.assertEqual(pls[0], self.PLAYLIST_ID)

        vids = [doc async for doc in self.db.collection("videos").stream()]
        self.assertEqual(len(vids), len(self.VIDEO_IDS))
        for video in vids:
            self.assertEqual([self.PLAYLIST_ID],
                             video.get("videosdb.playlists"))

        # check that one playlist is processed correctly:

        playlist = (await self.db.document("playlists/" + self.PLAYLIST_ID).get()).to_dict()
        self.assertEqual(playlist["kind"], "youtube#playlist")
        self.assertEqual(playlist["id"], self.PLAYLIST_ID)

        self.assertEqual(playlist["videosdb"], {
            'slug': 'how-to-be-really-successful-sadhguru-answers',
            'videoCount': 7,
            'lastUpdated': DatetimeWithNanoseconds(2022, 7, 6, 12, 18, 45, tzinfo=datetime.timezone.utc),
            'videoIds': self.VIDEO_IDS
        })

        # check that one video is processed correctly:
        video_id = "HADeWBBb1so"

        video = (await self.db.document("videos/" + video_id).get()).to_dict()
        self.assertEqual(video["kind"], "youtube#video")
        self.assertEqual(video["id"], video_id)
        self.assertEqual(video["videosdb"]["playlists"], [self.PLAYLIST_ID])
        self.assertEqual(video["videosdb"]["slug"],
                         "fate-god-luck-or-effort-what-decides-your-success-sadhguru")
        self.assertIn("descriptionTrimmed", video["videosdb"])
        self.assertEqual(video["videosdb"]["durationSeconds"], 470.0)
        self.assertIn("statistics", video)

    async def test_firestore_behavior(self):
        a = await self.db.document("videos/" + "asdfsdf").set({
            "videosdb": {
                "playlists": firestore.ArrayUnion(["sdjfpoasdjf"])
            }
        }, merge=True)
        b = await self.db.document("videos/" + "asdfsdf").set({
            "videosdb": {
                "playlists": firestore.ArrayUnion(["sdfsdf"])
            }
        }, merge=True)

        c = await self.db.document("videos/" + "asdfsdf").get()
        self.assertEqual(
            {'videosdb': {'playlists': ['sdjfpoasdjf', 'sdfsdf']}}, c.to_dict())

    async def test_transcript_downloading(self):
        with open(DATA_DIR + "/video-HADeWBBb1so.response.json") as f:
            video = json.load(f)["items"][0]

        d = Downloader()
        await d.init()
        await d._handle_transcript(video)

        self.assertIn("transcript", video["videosdb"])
        self.assertIn("transcript_status", video["videosdb"])


# class PublisherTest(PatchedTestCase):
#     async def test_hello_twitter(self):
#         with open(DATA_DIR + "/video-HADeWBBb1so.response.json") as f:
#             video = json.load(f)["items"][0]

#         video |= {
#             "videosdb": {
#                 "slug": "this-is-a-slug-for-testing"
#             }
#         }

#         p = TwitterPublisher()
#         r = await p.publish_video(video)
#         print(r)
