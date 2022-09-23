import os
import isodate
import json

import requests
from dotenv import load_dotenv
from videosdb.downloader import DB, Downloader, put_item_at_front

import os
from unittest.mock import AsyncMock, MagicMock, patch

import aiounittest
import sys

BASE_DIR = os.path.dirname(sys.modules[__name__].__file__)
DATA_DIR = BASE_DIR + "/test_data"


def mock_httpx_responses_from_files(filenames):

    retvals = []
    for f in filenames:
        with open(DATA_DIR + "/" + f) as ff:
            retvals.append(json.load(ff))

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(side_effect=retvals)
    mock_response.raise_for_status = MagicMock()

    return mock_response


class DownloaderTest(aiounittest.AsyncTestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv("common/env/testing.txt")
        project = os.environ["FIREBASE_PROJECT"]
        config = os.environ["VIDEOSDB_CONFIG"]
        cls.db = DB.setup(project, config)
        cls.VIDEO_IDS = ['FBYoZ-FgC84', 'HADeWBBb1so', 'J-1WVf5hFIk', 'QEkHcPt-Vpw',
                         'ZhI-stDIlCE', 'ed7pFle2yM8', 'gavq4LM8XK0']
        cls.PLAYLIST_ID = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"

    def setUp(self):
        # clear DB:
        requests.delete(
            "http://localhost:8080/emulator/v1/projects/%s/databases/(default)/documents" % os.environ["FIREBASE_PROJECT"])

        self.downloader = Downloader(MagicMock())

    @patch("videosdb.youtube_api.httpx.AsyncClient.get")
    async def test_download_playlist(self, mock_get):

        mock_get.return_value = mock_httpx_responses_from_files(
            ["playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json",
             "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.1.json",
             "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.2.json"
             ])

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

    @patch("videosdb.youtube_api.httpx.get")
    async def test_create_video(self, mock_get):
        video_id = "HADeWBBb1so"

        mock_get.return_value = mock_httpx_responses_from_files(
            ["video-HADeWBBb1so.response.json"])

        video = await self.downloader._create_video(video_id)

        self.assertEqual(video["kind"], "youtube#video")
        self.assertEqual(video["id"], video_id)

        doc = await self.db.document("videos/" + video_id).get()
        self.assertTrue(doc.exists)

    def test_put_item_at_front(self):
        s = [3, 5, 6, 8, 1]
        self.assertEqual(put_item_at_front(s, 6), [8, 1, 3, 5, 6])

    @patch("videosdb.youtube_api.httpx.get")
    async def test_process_playlist_list(self, mock_get):
        video_id = "HADeWBBb1so"
        mock_get.return_value = mock_httpx_responses_from_files(
            ["playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json",
             "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.1.json",
             "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.2.json"
             ])

        new_state = await self.downloader._process_playlist_list(
            [self.PLAYLIST_ID], {}, "Sadhguru")

        self.assertEqual(new_state, {
            "lastPlaylistId": None,
            "lastVideoId": None
        })

        doc = await self.db.document("videos/" + video_id).get()
        self.assertTrue(doc.exists)

        pls = [doc.get("id") async for doc in self.db.collection("playlists").stream()]
        self.assertEqual(len(pls), 1)
        self.assertEqual(pls[0], self.PLAYLIST_ID)

        vids = [doc async for doc in self.db.collection("videos").stream()]
        self.assertEqual(len(vids), len(self.VIDEO_IDS))
        for video in vids:
            self.assertEquals([self.PLAYLIST_ID],
                              video.get("videosdb.playlists"))


# @pytest.mark.asyncio
# async def test_channel_infos(db):
#     async for i in db.collection("channel_infos").stream():
#         self.assertEqual(i.to_dict()
#         self.assertEqual(i.get("kind") == "youtube#channel"


# @pytest.mark.asyncio
# async def test_meta(db):
#     doc = await db.collection("meta").document("meta").get()
#     self.assertEqual(doc.exists
#     self.assertEqual(doc.get("lastUpdated")
#     self.assertEqual(doc.get("videoIds")
#     self.assertEqual(len(doc.get("videoIds")) > 0


# @pytest.mark.asyncio
# async def test_videos(db):
#     DOC_ID = "0OWMAP1-NH4"
#     doc = await db.collection("videos").document(DOC_ID).get()
#     self.assertEqual(doc.exists

#     d = doc.to_dict()
#     self.assertEqual(d

#     self.assertEqual(d.get("kind") == "youtube#video"

#     self.assertEqual("contentDetails" in d
#     self.assertEqual("id" in d
#     self.assertEqual("snippet" in d
#     self.assertEqual("statistics" in d
#     self.assertEqual("videosdb" in d
#     v = d["videosdb"]
#     self.assertEqual(v.get("descriptionTrimmed")
#     self.assertEqual(v.get("durationSeconds") == 392
#     self.assertEqual(v.get("slug") == "gurdjieff-the-rascal-saint-sadhguru-exclusive"
#     self.assertEqual("playlists" in v
#     self.assertEqual(v["playlists"]
#     self.assertEqual(v["playlists"][0] == "PL3uDtbb3OvDN6Od1Shk_X5TxibGQGbTVk"


# @pytest.mark.asyncio
# async def test_playlists(db):
#     DOC_ID = "PL3uDtbb3OvDN6Od1Shk_X5TxibGQGbTVk"
#     doc = await db.collection("playlists").document(DOC_ID).get()
#     self.assertEqual(doc.exists
#     d = doc.to_dict()
#     self.assertEqual(d
#     self.assertEqual(d.get("kind") == "youtube#playlist"
#     self.assertEqual("snippet" in d
#     self.assertEqual("videosdb" in d
#     v = d["videosdb"]
#     self.assertEqual(v.get("lastUpdated")
#     self.assertEqual(v.get("slug") == "sadhguru-exclusive"
#     self.assertEqual(v.get("videoCount") == 25


# @pytest.mark.asyncio
# async def test_cache(db):

#     async for cache_item in db.collection("playlists").stream():
#         self.assertEqual(cache_item.get("etag")
#         async for page in cache_item.reference.collection("pages").stream():
#             self.assertEqual(page
