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

    def setUp(self):
        load_dotenv("common/env/testing.txt")
        # clear DB:

        requests.delete(
            "http://localhost:8080/emulator/v1/projects/%s/databases/(default)/documents" % os.environ["FIREBASE_PROJECT"])
        project = os.environ["FIREBASE_PROJECT"]
        config = os.environ["VIDEOSDB_CONFIG"]

        self.db = DB.setup(project, config)

    @patch("videosdb.youtube_api.httpx.AsyncClient.get")
    async def test_download_playlist(self, mock_get):
        playlist_id = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"

        mock_get.return_value = mock_httpx_responses_from_files(
            ["playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json",
             "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.1.json",
             "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.2.json"
             ])

        downloader = Downloader()
        playlist = await downloader._download_playlist(playlist_id, "Sadhguru")

        assert playlist["kind"] == "youtube#playlist"
        assert playlist["id"] == playlist_id

        assert playlist["videosdb"] == {
            'slug': 'how-to-be-really-successful-sadhguru-answers',
            'videoCount': 7,
            'lastUpdated': isodate.parse_datetime("2022-07-06T12:18:45+00:00"),
            'videoIds': ['FBYoZ-FgC84', 'HADeWBBb1so', 'J-1WVf5hFIk', 'QEkHcPt-Vpw', 'ZhI-stDIlCE', 'ed7pFle2yM8', 'gavq4LM8XK0']
        }

        doc = await self.db.document("playlists/" + playlist_id).get()
        assert doc.exists

    @patch("videosdb.youtube_api.httpx.get")
    async def test_create_video(self, mock_get):
        video_id = "HADeWBBb1so"

        mock_get.return_value = mock_httpx_responses_from_files(
            ["video-HADeWBBb1so.response.json"])

        downloader = Downloader()
        video = await downloader._create_video(video_id)

        assert video["kind"] == "youtube#video"
        assert video["id"] == video_id

        doc = await self.db.document("videos/" + video_id).get()
        assert doc.exists

    def test_put_item_at_front(self):
        s = [3, 5, 6, 8, 1]
        assert put_item_at_front(s, 6) == [8, 1, 3, 5, 6]

    # @patch("videosdb.youtube_api.httpx.get")
    # async def test_process_playlist_list(self, mock_get):
    #     playlist_id = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"
    #     video_id = "HADeWBBb1so"
    #     mock_get.return_value = mock_httpx_responses_from_files(
    #         ["playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json",
    #          "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.1.json",
    #          "playlistItems-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.2.json"
    #          ])

    #     downloader = Downloader()

    #     new_state = downloader._process_playlist_list(
    #         [playlist_id], {}, "Sadhguru")

    #     doc = await self.db.document("videos/" + video_id).get()
    #     assert doc.exists

    #     doc = await self.db.document("playlists/" + playlist_id).get()
    #     assert doc.exists


# @pytest.mark.asyncio
# async def test_channel_infos(db):
#     async for i in db.collection("channel_infos").stream():
#         assert i.to_dict()
#         assert i.get("kind") == "youtube#channel"


# @pytest.mark.asyncio
# async def test_meta(db):
#     doc = await db.collection("meta").document("meta").get()
#     assert doc.exists
#     assert doc.get("lastUpdated")
#     assert doc.get("videoIds")
#     assert len(doc.get("videoIds")) > 0


# @pytest.mark.asyncio
# async def test_videos(db):
#     DOC_ID = "0OWMAP1-NH4"
#     doc = await db.collection("videos").document(DOC_ID).get()
#     assert doc.exists

#     d = doc.to_dict()
#     assert d

#     assert d.get("kind") == "youtube#video"

#     assert "contentDetails" in d
#     assert "id" in d
#     assert "snippet" in d
#     assert "statistics" in d
#     assert "videosdb" in d
#     v = d["videosdb"]
#     assert v.get("descriptionTrimmed")
#     assert v.get("durationSeconds") == 392
#     assert v.get("slug") == "gurdjieff-the-rascal-saint-sadhguru-exclusive"
#     assert "playlists" in v
#     assert v["playlists"]
#     assert v["playlists"][0] == "PL3uDtbb3OvDN6Od1Shk_X5TxibGQGbTVk"


# @pytest.mark.asyncio
# async def test_playlists(db):
#     DOC_ID = "PL3uDtbb3OvDN6Od1Shk_X5TxibGQGbTVk"
#     doc = await db.collection("playlists").document(DOC_ID).get()
#     assert doc.exists
#     d = doc.to_dict()
#     assert d
#     assert d.get("kind") == "youtube#playlist"
#     assert "snippet" in d
#     assert "videosdb" in d
#     v = d["videosdb"]
#     assert v.get("lastUpdated")
#     assert v.get("slug") == "sadhguru-exclusive"
#     assert v.get("videoCount") == 25


# @pytest.mark.asyncio
# async def test_cache(db):

#     async for cache_item in db.collection("playlists").stream():
#         assert cache_item.get("etag")
#         async for page in cache_item.reference.collection("pages").stream():
#             assert page
