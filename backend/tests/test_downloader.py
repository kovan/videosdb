import pytest
import os
from videosdb.backend.downloader import Downloader


# @pytest.fixture
# async def api():

def setup_module(module):

    os.environ.setdefault(
        "YOUTUBE_API_URL", "http://127.0.0.1:2000/youtube/v3")
    os.environ.setdefault(
        "YOUTUBE_API_KEY", "AIzaSyDM-rEutI1Mr6_b1Uz8tofj2dDlwcOzkjs")
    os.environ.setdefault("DEBUG", "1")
    os.environ.setdefault("LOGLEVEL", "DEBUG")
    os.environ.setdefault("PYTHONDEVMODE", "1")
    os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:6001")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "worpdress-279321")


def test_downloader():
    downloader = Downloader()
    downloader.check_for_new_videos()
