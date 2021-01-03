import os
import json
import shutil
from django.core.files import File
from django.conf import settings
from django.test import TestCase, override_settings
from unittest.mock import create_autospec, patch
from django.utils import timezone
from videosdb.models import Video, Category, Publication
from videosdb.backend.downloader import Downloader
from videosdb.backend.publisher import Publisher
from videosdb.backend.youtube_api import YoutubeAPI


def _create_test_video():
        v = Video()
        v.youtube_id = "xxxxxxxxxxx"
        v.title = "New video title"
        v.description = "Description of the video click this should be hidden"
        v.transcript = "This is the transcript"
        v.excluded = False
        v.uploader = "Uploader"
        v.channel_id = "UCcYzLCs3zrQIBVHYA1sK2sw"
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
        self.v = _create_test_video()
    def tearDown(self):
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
        yt_api_mock.list_playlists.return_value=[test_playlist]
        yt_api_mock.list_playlist_videos.return_value=["id1"]
        yt_api_mock.get_video_info.return_value=test_video_info
        yt_api_mock.get_video_transcript.return_value="hello"

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
        self.assertEqual([t.name for t in v.tags.all()], test_video_info["tags"])

    # def test_download_thumbnail(self):
    #     dl = Downloader()
    #     dl.download_one("CR5HtTsUl5E")

        
# @override_settings(MEDIA_ROOT="test_media")

# class PublisherTest(TestCase):
#     @patch("videosdb.backend.wordpress.Wordpress")
#     def setUp(self, wp_mock):
# #         wp_mock = create_autospec(Wordpress, spec_set=True)
#         #wp_mock = create_autospec(Wordpress, spec_set=True)
#         #Publisher.__init__ = None
#         self.publisher = Publisher()
#         #self.publisher.wordpress = wp_mock
# #         #self.wordpress = Wordpress()
# #         self.new_posts = []
# #         if not os.path.exists(settings.MEDIA_ROOT):
# #             os.mkdir(settings.MEDIA_ROOT)        
#         self.v = _create_test_video()

#     def tearDown(self):
# #         for post_id in self.new_posts:
# #             self.wordpress.delete(post_id)

# #         shutil.rmtree(settings.MEDIA_ROOT)
#         self.v.delete()
        

#     def test_publish_one(self):

#         with self.settings(TRUNCATE_DESCRIPTION_AFTER=r"(c|C)lick"):
#             pub = self.publisher.publish_one(self.v)
        
# #         self.assertTrue(Publication.objects.filter(post_id=pub.post_id).count())
# #         self.assertTrue(pub.thumbnail_id)

# #         # post = self.wordpress.get(pub.post_id)
# #         # self.new_posts.append(pub.post_id)
# #         # self.assertEqual(post.title, self.v.title)
# #         # self.assertEqual(post.custom_fields[0]["key"], "youtube_id" )
# #         # self.assertEqual(post.custom_fields[0]["value"], self.v.youtube_id )
# #         # self.assertIn("Description of the video", post.content)
# #         # self.assertNotIn("this should be hidden", post.content)
# #         # self.assertIn(self.v.youtube_id, post.content)
# #         # self.assertTrue(post.thumbnail)
# #         # if self.v.transcript:
# #         #     self.assertIn(self.v.transcript, post.content)

# #         pub.delete()



