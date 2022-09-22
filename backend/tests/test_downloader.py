import os
import isodate
import json
import pytest
import requests
from dotenv import load_dotenv
from videosdb.downloader import DB, Downloader

import os
from unittest.mock import AsyncMock, patch
import pytest

DATA_DIR = "backend/tests/test_data"


def setup_module():
    load_dotenv("common/env/testing.txt")
    # clear DB:

    requests.delete(
        "http://localhost:8080/emulator/v1/projects/%s/databases/(default)/documents" % os.environ["FIREBASE_PROJECT"])


@pytest.fixture
def db():
    project = os.environ["FIREBASE_PROJECT"]
    config = os.environ["VIDEOSDB_CONFIG"]

    yield DB.setup(project, config)


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


@pytest.mark.asyncio
async def test_cache(db):

    async for cache_item in db.collection("playlists").stream():
        assert cache_item.get("etag")
        async for page in cache_item.reference.collection("pages").stream():
            assert page


@pytest.mark.asyncio
@patch("videosdb.youtube_api.httpx.get")
async def test_download_playlist(mock_get):
    playlist_id = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"

    with open(DATA_DIR + "/playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json") as f:
        response = json.load(f)

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = response
    mock_get.return_value = mock_response

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


@pytest.mark.asyncio
@patch("videosdb.youtube_api.httpx.get")
async def test_create_video(mock_get, db):
    video_id = "HADeWBBb1so"
    with open(DATA_DIR + "/video-HADeWBBb1so.response.json") as f:
        response = json.load(f)

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = response
    mock_get.return_value = mock_response

    downloader = Downloader()
    video = await downloader._create_video(video_id)

    assert video["kind"] == "youtube#video"
    assert video["id"] == video_id

    doc = await db.document("videos/" + video_id).get()
    assert doc.exists
