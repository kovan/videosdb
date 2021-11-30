import pytest
import logging
import asyncio
import os
from videosdb.downloader import Downloader, gather_all_tasks
from google.cloud import firestore
from videosdb.youtube_api import YoutubeAPI

# @pytest.fixture
# async def api():


def setup_module(module):
    logging.getLogger("videosdb.downloader").setLevel(logging.DEBUG)
    os.environ.setdefault(
        "YOUTUBE_API_URL", "http://127.0.0.1:2000/youtube/v3")
    os.environ.setdefault(
        "YOUTUBE_API_KEY", "AIzaSyDM-rEutI1Mr6_b1Uz8tofj2dDlwcOzkjs")
    # os.environ.setdefault("DEBUG", "1")
    os.environ.setdefault("LOGLEVEL", "DEBUG")
    os.environ.setdefault("PYTHONDEVMODE", "1")
    os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:6001")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "worpdress-279321")


@pytest.fixture
def db():
    yield firestore.AsyncClient()


@pytest.fixture
def downloader():
    yield Downloader()


@pytest.fixture
async def api():
    yield await YoutubeAPI.create()


# def test_downloader():
#     downloader = Downloader()
#     downloader.check_for_new_videos()


# def test_not_array_too_large_to_be_used_in_query(db):
#     query = db.collection('videos')
#     query = query.where(
#         'videosdb.playlists',
#         'array-contains',
#         this.category
#     )
@pytest.mark.asyncio
async def test_download(db, downloader):

    async for pl in db.collection("playlists").stream():
        asyncio.create_task(pl.reference.delete())
    await gather_all_tasks()

    await downloader.check_for_new_videos_async()

    async for pl in db.collection("playlists").stream():
        pl = pl.to_dict()
        assert pl["id"]
        assert pl["videosdb"]["lastUpdated"]
        assert pl["videosdb"]["slug"]
        assert pl["videosdb"]["videoCount"]
