import asyncio
import os
import aiounittest
import isodate
import json

import requests
from dotenv import load_dotenv
from videosdb.youtube_api import YoutubeAPI
from videosdb.downloader import DB, Downloader, put_item_at_front

import os
from unittest.mock import MagicMock, patch

import sys

BASE_DIR = os.path.dirname(sys.modules[__name__].__file__)
DATA_DIR = BASE_DIR + "/test_data"


def create_mock_httpx_response(filename, status_code=200):

    with open(DATA_DIR + "/" + filename) as ff:
        content = json.load(ff)

    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json = MagicMock(return_value=content)
    mock_response.raise_for_status = MagicMock()

    return mock_response


def create_mock_api_response(files, one=False):
    async def async_generator(items):
        for i in items:
            yield i
    items = []
    for file in files:
        with open(DATA_DIR + "/" + file) as f:
            content = json.load(f)
            items += content["items"]

    if one:
        if items:
            return items[0]
        else:
            return None
    return async_generator(items)


# @patch("videosdb.youtube_api.YoutubeAPI", new_callable=create_autospec(YoutubeAPI))
@patch("videosdb.youtube_api.httpx.AsyncClient.get", side_effect=NotImplementedError)
class DownloaderTest(aiounittest.AsyncTestCase):
    def get_event_loop(self):  # workaround for bug
        self.my_loop = asyncio.get_event_loop()
        return self.my_loop

    @classmethod
    def setUpClass(cls):
        load_dotenv("common/env/testing.txt")
        project = os.environ["FIREBASE_PROJECT"]
        config = os.environ["VIDEOSDB_CONFIG"]
        cls.db = DB.setup(project, config)

        cls.VIDEO_IDS = ['FBYoZ-FgC84', 'HADeWBBb1so', 'J-1WVf5hFIk', 'QEkHcPt-Vpw',
                         'ZhI-stDIlCE', 'ed7pFle2yM8', 'gavq4LM8XK0']
        cls.PLAYLIST_ID = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"
        cls.get_playlist_info_response = create_mock_api_response(
            ["playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json"], True)
        cls.list_playlist_items_response = create_mock_api_response([
            "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.1.json",
            "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.2.json"
        ])

    def setUp(self):
        # clear DB:
        requests.delete(
            "http://localhost:8080/emulator/v1/projects/%s/databases/(default)/documents" % os.environ["FIREBASE_PROJECT"])

        self.downloader = Downloader(MagicMock())

    @patch.object(YoutubeAPI, "get_playlist_info")
    @patch.object(YoutubeAPI, "list_playlist_items")
    async def test_download_playlist(self, list_playlist_items, get_playlist_info, httpx_get):
        get_playlist_info.return_value = self.get_playlist_info_response
        list_playlist_items.return_value = self.list_playlist_items_response

        playlist = await self.downloader._download_playlist(self.PLAYLIST_ID, "Sadhguru")

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

    @patch.object(YoutubeAPI, "get_video_info")
    async def test_create_video(self, mock, httpx_get):
        video_id = "HADeWBBb1so"

        mock.return_value = create_mock_api_response(
            ["video-%s.response.json" % video_id], True)

        video = await self.downloader._create_video(video_id)

        self.assertEqual(video["kind"], "youtube#video")
        self.assertEqual(video["id"], video_id)

        doc = await self.db.document("videos/" + video_id).get()
        self.assertTrue(doc.exists)

    def test_put_item_at_front(self, httpx_get):
        s = [3, 5, 6, 8, 1]
        self.assertEqual(put_item_at_front(s, 6), [8, 1, 3, 5, 6])
        self.assertEqual(put_item_at_front(s, 3), [5, 6, 8, 1, 3])
        self.assertEqual(put_item_at_front(s, 123), s)
        self.assertEqual(put_item_at_front(s, None), s)

    # @patch.object(YoutubeAPI, "get_video_info")
    # @patch.object(YoutubeAPI, "get_playlist_info")
    # @patch.object(YoutubeAPI, "list_playlist_items")
    # async def test_process_playlist_list(self, list_playlist_items, get_playlist_info, get_video_info, httpx_get):
    #     video_id = "HADeWBBb1so"

    #     new_state = await self.downloader._process_playlist_list(
    #         [self.PLAYLIST_ID], {}, "Sadhguru")

    #     self.assertEqual(new_state, {
    #         "lastPlaylistId": None,
    #         "lastVideoId": None
    #     })

    #     doc = await self.db.document("videos/" + video_id).get()
    #     self.assertTrue(doc.exists)

    #     pls = [doc.get("id") async for doc in self.db.collection("playlists").stream()]
    #     self.assertEqual(len(pls), 1)
    #     self.assertEqual(pls[0], self.PLAYLIST_ID)

    #     vids = [doc async for doc in self.db.collection("videos").stream()]
    #     self.assertEqual(len(vids), len(self.VIDEO_IDS))
    #     for video in vids:
    #         self.assertEqual([self.PLAYLIST_ID],
    #                          video.get("videosdb.playlists"))
