# import os
# from unittest.mock import patch
# import pytest
# from dotenv import load_dotenv
# from videosdb.downloader import DB
# from videosdb.youtube_api import YoutubeAPI


# def setup_module():
#     load_dotenv("common/env/testing.txt")


# @pytest.fixture
# def db():
#     project = os.environ["FIREBASE_PROJECT"]
#     config = os.environ["VIDEOSDB_CONFIG"]

#     yield DB.setup(project, config)


# @pytest.fixture
# def api(db):
#     api = YoutubeAPI(db)
#     yield api


# @pytest.mark.asyncio
# async def test_cache_exception_not_cached(db, api):
#     # mock = AsyncMock(side_effect=YoutubeAPI.QuotaExceededError(403))
#     # mock = create_autospec(httpx.Response(403))
#     DOC_ID = "playlistItems?part=snippet&playlistId=PL3uDtbb3OvDOwkTziO4n6UscjbmUV0ABR"
#     doc_ref = db.collection("cache").document(DOC_ID)
#     await doc_ref.delete()

#     with patch("videosdb.youtube_api.YoutubeAPI._request_base", side_effect=YoutubeAPI.QuotaExceeded(403)):
#         try:
#             async for i in await api.list_playlist_items("PL3uDtbb3OvDOwkTziO4n6UscjbmUV0ABR"):
#                 pass
#         except YoutubeAPI.QuotaExceeded:
#             pass

#     doc = await doc_ref.get()

#     assert not doc.exists


# @ pytest.mark.asyncio
# async def test_cache_write(db, api):
#     DOC_ID = "search?part=snippet&type=video&relatedToVideoId=hGxRl0h4jgE"
#     doc_ref = db.collection("cache").document(DOC_ID)
#     await doc_ref.delete()
#     result = await api._request_one("/search", {
#         "part": "snippet",
#         "type": "video",
#         "relatedToVideoId": "hGxRl0h4jgE"
#     })

#     doc = await doc_ref.get()
#     assert doc.exists

#     async for page in doc_ref.collection("pages").stream():
#         assert page.get("etag")
