import os
import json
import shutil
import email
import logging
import httplib2
from pprint import pprint
from django.core.files import File

from django.conf import settings
from django.test import TestCase, override_settings, tag
from unittest.mock import create_autospec, patch, Mock
from django.utils import timezone
from .models import Video, Playlist, Tag
from .backend.downloader import Downloader
from .backend.youtube_api import YoutubeAPI
from .backend.ipfs import IPFS

logger = logging.getLogger(__name__)


# @override_settings(MEDIA_ROOT="test_media")
# def _create_test_video():
#     v = Video()
#     v.youtube_id = "id1"
#     v.excluded = False
#     v.full_response = json.loads(open(TEST_VIDEO_INFO).read())
#     v.yt_data.publishedAt = timezone.now()

#     f = settings.BASE_DIR + "/videosdb/test_data/sample_thumbnail.jpg"
#     f2 = shutil.copy(f, settings.MEDIA_ROOT+"/sample_thumbnail.jpg")
#     v.thumbnail = File(open(f2, "rb"))
#     v.save()
#     v.thumbnail.close()
#     return v


# #TEST_VIDEO_INFO = settings.BASE_DIR + "/videosdb/test_data/test_video_info.json"
#HTTPLIB2_CACHE = settings.BASE_DIR + "/videosdb/test_data/httplib2_cache"

# from httplib2 code:


# def httplib2_decode_cache_entry(cache_entry):
#     info, content = cache_entry.split(b"\r\n\r\n", 1)
#     info = email.message_from_bytes(info)
#     for k, v in info.items():
#         if v.startswith("=?") and v.endswith("?="):
#             info.replace_header(
#                 k, str(*email.header.decode_header(v)[0])
#             )
#     return info


# def fake_request(dummy, url):
#     cache = httplib2.FileCache("httplib2_cache")
#     cached_raw = cache.get(url)
#     response = Mock()
#     if not cached_raw:
#         response.status = 404
#         return (response, "[]")
#     info = httplib2_decode_cache_entry(cached_raw)
#     return (200, info)


class DownloaderTest(TestCase):
    # def setUp(self):
    #settings.DEBUG = 1

    # @patch.object(httplib2.Http, "request", new=fake_request)
    def test_check_for_new_videos(self):
        v = Video(youtube_id="CR5HtTsUl5E", yt_data={"title": "hi"})
        v.save()
        dl = Downloader()
        dl.yt_api.yt_key = settings.YOUTUBE_KEY_TESTING
        dl.check_for_new_videos()
        self.assertTrue(Video.objects.all().count() > 1)
        self.assertTrue(Playlist.objects.all().count() > 1)
        self.assertTrue(Tag.objects.all().count() > 1)

    # @override_settings(MEDIA_ROOT="test_media")
    # class DownloaderTest(TestCase):
    #     def setUp(self):
    #         self.v = _create_test_video()

    #     def tearDown(self):
    #         self.v.delete()

    # def test_check_for_videos(self):
    #     test_channel = {"id": "id", "name": "name"}
    #     test_playlist = {
    #         'channel_title': 'name',
    #         'id': 'playlist_id',
    #         'title': 'Playlist title'
    #     }
    #     test_video_info = json.loads(open(TEST_VIDEO_INFO).read())

    #     yt_api_mock = create_autospec(YoutubeAPI, spec_set=True)
    #     yt_api_mock.list_channel_playlists.return_value = [test_playlist]
    #     yt_api_mock.list_playlist_videos.return_value = ["id1"]
    #     yt_api_mock.get_video_info.return_value = test_video_info
    #     yt_api_mock.get_video_transcript.return_value = "hello"

    #     dl = Downloader()
    #     dl.yt_api = yt_api_mock
    #     with self.settings(YOUTUBE_CHANNEL=test_channel):
    #         dl.check_for_new_videos()

    #     v = Video.objects.get(youtube_id="id1")
    #     self.assertEqual(v.title, "my title")
    #     self.assertEqual(v.transcript,  "hello")
    #     self.assertTrue(v.thumbnail)
    #     c = Playlist.objects.get(name=test_playlist["title"])
    #     self.assertEqual(v.categories.get(), c)
    #     self.assertEqual(
    #         sorted([t.name for t in v.tags.all()]),
    #         sorted(test_video_info["tags"]))

    # @tag("consume-quota")
    # def test_download(self):
    #     d = Downloader()
    #     d.process_video("tSc_rtEtpm4")

    # class YoutubeAPITest(TestCase):
    #     def setUp(self):
    #         self.api = YoutubeAPI(settings.YOUTUBE_KEY_2)

    #     def test_related(self):
    #         #r = self.api.get_related_videos("G2QmUoGjgzc")
    #         #r = list(r)
    #         # import ipdb
    #         # ipdb.set_trace()
    #         with open("asdf.json") as f:
    #             data = json.load(f)
    #             unique = dict()
    #             for result in data:
    #                 unique[result["id"]["videoId"]] = result
    #             pprint(unique)
