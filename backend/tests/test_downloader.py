import os
import pytest
from unittest.mock import patch
from videosdb.downloader import DB, Downloader
from dotenv import load_dotenv


def setup_module():
    load_dotenv("common/env/testing.txt")


DATA_DIR = "backend/tests/test_data/"
# clear DB:
# requests.delete(
#     "http://localhost:8080/emulator/v1/projects/%s/databases/(default)/documents" % os.environ["FIREBASE_PROJECT"])


@pytest.fixture
def db():
    project = os.environ["FIREBASE_PROJECT"]
    config = os.environ["VIDEOSDB_CONFIG"]

    yield DB.setup(project, config)


@pytest.mark.asyncio
async def test_channel_infos(db):
    async for i in db.collection("channel_infos").stream():
        assert i.to_dict()
        assert i.get("kind") == "youtube#channel"


@pytest.mark.asyncio
async def test_meta(db):
    doc = await db.collection("meta").document("meta").get()
    assert doc.exists
    assert doc.get("lastUpdated")
    assert doc.get("videoIds")
    assert len(doc.get("videoIds")) > 0


@pytest.mark.asyncio
async def test_videos(db):
    DOC_ID = "0OWMAP1-NH4"
    doc = await db.collection("videos").document(DOC_ID).get()
    assert doc.exists

    d = doc.to_dict()
    assert d

    assert d.get("kind") == "youtube#video"

    assert "contentDetails" in d
    assert "id" in d
    assert "snippet" in d
    assert "statistics" in d
    assert "videosdb" in d
    v = d["videosdb"]
    assert v.get("descriptionTrimmed")
    assert v.get("durationSeconds") == 392
    assert v.get("slug") == "gurdjieff-the-rascal-saint-sadhguru-exclusive"
    assert "playlists" in v
    assert v["playlists"]
    assert v["playlists"][0] == "PL3uDtbb3OvDN6Od1Shk_X5TxibGQGbTVk"


@pytest.mark.asyncio
async def test_playlists(db):
    DOC_ID = "PL3uDtbb3OvDN6Od1Shk_X5TxibGQGbTVk"
    doc = await db.collection("playlists").document(DOC_ID).get()
    assert doc.exists
    d = doc.to_dict()
    assert d
    assert d.get("kind") == "youtube#playlist"
    assert "snippet" in d
    assert "videosdb" in d
    v = d["videosdb"]
    assert v.get("lastUpdated")
    assert v.get("slug") == "sadhguru-exclusive"
    assert v.get("videoCount") == 25


@pytest.mark.asyncio
async def test_cache(db):

    async for cache_item in db.collection("playlists").stream():
        assert cache_item.get("etag")
        async for page in cache_item.reference.collection("pages").stream():
            assert page


@pytest.mark.asyncio
async def test_download_playlist(db):
    plid = "PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU"
    downloader = Downloader()
    with open(DATA_DIR + "/playlist-PL3uDtbb3OvDMz7DAOBE0nT0F9o7SV5glU.response.json") as f:
        with patch("downloader.http.get") as mock:

            mock.return_value = f.read()

            playlist = await downloader._download_playlist(plid, "Sadhguru")
            assert playlist == {

            }
