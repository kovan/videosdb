import pytest
import os
from videosdb.youtube_api import YoutubeAPI

YOUTUBE_KEY_TESTING = "AIzaSyDM-rEutI1Mr6_b1Uz8tofj2dDlwcOzkjs"


@pytest.fixture
async def api():
    os.environ.setdefault(
        "YOUTUBE_API_URL", "http://127.0.0.1:2000/youtube/v3")
    yield await YoutubeAPI.create(YOUTUBE_KEY_TESTING)


# @pytest.mark.asyncio
# async def test_list_playlist_items(api):
#     items = api.list_playlist_items("UUcYzLCs3zrQIBVHYA1sK2sw")
#     async for item in items:
#         assert item is not None
