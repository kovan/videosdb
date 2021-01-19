import os
import json
import shutil
from django.core.files import File
from django.conf import settings
from django.test import TestCase, override_settings, tag
from unittest.mock import create_autospec, patch
from django.utils import timezone
from videosdb.models import Video, Category
from videosdb.backend.downloader import Downloader
from videosdb.backend.youtube_api import YoutubeAPI


@override_settings(MEDIA_ROOT="test_media")
def _create_test_video():
    v = Video()
    v.youtube_id = "id1"
    v.excluded = False
    v.full_response = json.loads(open(TEST_VIDEO_INFO).read())
    v.yt_published_date = timezone.now()

    f = settings.BASE_DIR + "/videosdb/test_data/sample_thumbnail.jpg"
    f2 = shutil.copy(f, settings.MEDIA_ROOT+"/sample_thumbnail.jpg")
    v.thumbnail = File(open(f2, "rb"))
    v.save()
    v.thumbnail.close()
    return v


TEST_VIDEO_INFO = settings.BASE_DIR + "/videosdb/test_data/test_video_info.json"


@override_settings(MEDIA_ROOT="test_media")
class DownloaderTest(TestCase):
    def setUp(self):
        if not os.path.exists("test_media"):
            os.mkdir("test_media")
        self.v = _create_test_video()

    def tearDown(self):
        shutil.rmtree("test_media")
        self.v.delete()

    def test_check_for_videos(self):
        test_channel = {"id": "id", "name": "name"}
        test_playlist = {
            'channel_title': 'name',
            'id': 'playlist_id',
            'title': 'Playlist title'
        }
        test_video_info = json.loads(open(TEST_VIDEO_INFO).read())

        yt_api_mock = create_autospec(YoutubeAPI, spec_set=True)
        yt_api_mock.list_playlists.return_value = [test_playlist]
        yt_api_mock.list_playlist_videos.return_value = ["id1"]
        yt_api_mock.get_video_info.return_value = test_video_info
        yt_api_mock.get_video_transcript.return_value = "hello"

        dl = Downloader()
        dl.yt_api = yt_api_mock
        with self.settings(YOUTUBE_CHANNEL=test_channel):
            dl.check_for_new_videos()

        v = Video.objects.get(youtube_id="id1")
        self.assertEqual(v.title, "my title")
        self.assertEqual(v.transcript,  "hello")
        self.assertTrue(v.thumbnail)
        c = Category.objects.get(name=test_playlist["title"])
        self.assertEqual(v.categories.get(), c)
        self.assertEqual(
            sorted([t.name for t in v.tags.all()]),
            sorted(test_video_info["tags"]))

    @ tag("consume-quota")
    def test_download(self):
        pass
