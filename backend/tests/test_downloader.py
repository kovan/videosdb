import asyncio
from httpx import Response
import respx
import os
import aiounittest
import isodate
import json

import requests
from dotenv import load_dotenv
from videosdb.downloader import Downloader, put_item_at_front
from videosdb.db import DB

import os

import sys


BASE_DIR = os.path.dirname(sys.modules[__name__].__file__)
DATA_DIR = BASE_DIR + "/test_data"


class MockedAPIMixin:
    @classmethod
    def setUpClass(cls):
        load_dotenv("common/env/testing.txt")
        project = os.environ["FIREBASE_PROJECT"]
        config = os.environ["VIDEOSDB_CONFIG"]
        cls.db = DB.setup(project, config)
        cls.mocked_api = respx.mock(base_url="https://www.googleapis.com/youtube/v3",
                                    assert_all_called=False)

        playlists = cls.mocked_api.get(path="/playlists", name="playlists")
        playlists.return_value = Response(200, json=json.load(
            open(DATA_DIR + "/playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json")))

        playlistItems = cls.mocked_api.get(
            path="/playlistItems", name="playlistItems")
        playlistItems.side_effect = [
            Response(200, json=json.load(
                open(DATA_DIR + "/playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.1.json"))),
            Response(200, json=json.load(
                open(DATA_DIR + "/playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.2.json"))),
        ]

        videos = cls.mocked_api.route(
            method="GET", path="/videos",  name="videos")
        videos.return_value = Response(200, json=json.load(
            open(DATA_DIR + "/video-HADeWBBb1so.response.json")))

        cls.VIDEO_IDS = ['FBYoZ-FgC84', 'HADeWBBb1so', 'J-1WVf5hFIk', 'QEkHcPt-Vpw',
                         'ZhI-stDIlCE', 'ed7pFle2yM8', 'gavq4LM8XK0']
        cls.PLAYLIST_ID = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"

    def setUp(self):
        # clear DB:
        requests.delete(
            "http://localhost:8080/emulator/v1/projects/%s/databases/(default)/documents" % os.environ["FIREBASE_PROJECT"])

        self.mocked_api.start()
        self.addCleanup(self.mocked_api.stop)

    def get_event_loop(self):  # workaround for bug
        self.my_loop = asyncio.get_event_loop()
        return self.my_loop


class DownloaderTest(MockedAPIMixin, aiounittest.AsyncTestCase):
    def test_put_item_at_front(self):
        s = [3, 5, 6, 8]
        self.assertEqual(put_item_at_front(s, 6), [6, 8, 3, 5])
        self.assertEqual(put_item_at_front(s, 8), [8, 3, 5, 6])
        self.assertEqual(put_item_at_front(s, 123), s)
        self.assertEqual(put_item_at_front(s, None), s)

    @respx.mock
    async def test_create_video(self):
        video_id = "HADeWBBb1so"

        # mock.return_value = create_mock_api_response(
        #     ["video-%s.response.json" % video_id], True)

        video = await Downloader()._create_video(video_id, [self.PLAYLIST_ID])

        mock = self.mocked_api["videos"]
        self.assertEqual(mock.call_count, 1)

        self.assertEqual(video["kind"], "youtube#video")
        self.assertEqual(video["id"], video_id)
        self.assertEqual(video["videosdb"]["playlists"], [self.PLAYLIST_ID])
        self.assertEqual(video["videosdb"]["slug"],
                         "fate-god-luck-or-effort-what-decides-your-success-sadhguru")
        self.assertIn("descriptionTrimmed", video["videosdb"])
        self.assertEqual(video["videosdb"]["durationSeconds"], 470.0)
        self.assertIn("statistics", video)

        doc = await self.db.document("videos/" + video_id).get()
        self.assertTrue(doc.exists)

    @respx.mock
    async def test_download_playlist(self):

        playlist = await Downloader()._download_playlist(self.PLAYLIST_ID, "Sadhguru")

        self.assertEqual(self.mocked_api["playlists"].call_count, 1)
        self.assertEqual(self.mocked_api["playlistItems"].call_count, 2)

        self.assertEqual(playlist["kind"], "youtube#playlist")
        self.assertEqual(playlist["id"], self.PLAYLIST_ID)

        self.assertEqual(playlist["videosdb"], {
            'slug': 'how-to-be-really-successful-sadhguru-answers',
            'videoCount': 7,
            'lastUpdated': isodate.parse_datetime("2022-07-06T12:18:45+00:00"),
            'videoIds': self.VIDEO_IDS
        })

        doc = await self.db.document("playlists/" + self.PLAYLIST_ID).get()
        self.assertTrue(doc.exists)
