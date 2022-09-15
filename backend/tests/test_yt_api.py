import pytest
import os
from videosdb.youtube_api import YoutubeAPI
from videosdb.downloader import DB
from dotenv import load_dotenv


def setup_module():
    load_dotenv("common/env/testing.txt")


@pytest.fixture
def db():
    project = os.environ["FIREBASE_PROJECT"]
    config = os.environ["VIDEOSDB_CONFIG"]

    yield DB.setup(project, config)


@pytest.fixture
def api(db):
    api = YoutubeAPI(db)
    yield api


@pytest.mark.asyncio
async def test_cache_exception(db:  DB, api: YoutubeAPI):

    async for i in await api.list_playlist_items("PL3uDtbb3OvDOwkTziO4n6UscjbmUV0ABR"):
        pass

    DOC_ID = "playlistItems?part=snippet&playlistId=PL3uDtbb3OvDOwkTziO4n6UscjbmUV0ABR"
    doc = await db.collection("cache").document(DOC_ID).get()

    assert not doc.exists


@pytest.mark.asyncio
async def test_cache_write(db, api):
    pass


@pytest.mark.asyncio
async def test_cache_read(db, api):
    pass
