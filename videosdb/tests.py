import os
import json


from django.test import TestCase
from unittest.mock import MagicMock,create_autospec
from django.utils import timezone
from videosdb.models import Video, Category, Publication
from videosdb.backend.downloader import Downloader
from videosdb.backend.publisher import Publisher
from videosdb.backend.youtube_api import YoutubeAPI
from videosdb.backend.wordpress import Wordpress



TEST_VIDEO_INFO = os.path.dirname(__file__) + "/test_data/test_video_info.json"

class DownloaderTest(TestCase):


    def test_check_for_videos(self):
        test_channel = {"id": "id", "name": "name"}
        test_playlist = {
            'channel_title': 'name', 
            'id': 'playlist_id', 
            'title': 'Playlist title'
        }
        
        test_video_info = json.loads(open(TEST_VIDEO_INFO).read())

        yt_api_mock = create_autospec(YoutubeAPI, spec_set=True)
        yt_api_mock.list_playlists = MagicMock(return_value=[test_playlist])
        yt_api_mock.list_playlist_videos = MagicMock(return_value=["id1"])
        yt_api_mock.get_video_info = MagicMock(return_value=test_video_info)
        yt_api_mock.get_video_transcript = MagicMock(return_value="hello")

        dl = Downloader()
        dl.yt_api = yt_api_mock
        with self.settings(YOUTUBE_CHANNEL=test_channel):
            dl.check_for_new_videos()

        v = Video.objects.get(youtube_id="id1")
        self.assertEqual(v.title, "my title")
        self.assertEqual(v.transcript,  "hello")
        c = Category.objects.get(name=test_playlist["title"])
        self.assertEqual(v.categories.get(), c)
        self.assertEqual([t.name for t in v.tags.all()], test_video_info["tags"])
        

class PublisherTest(TestCase):
    def setUp(self):
        self.publisher = Publisher()
        self.wordpress = Wordpress()
        self.thumbnails_uploaded = []

    def tearDown(self):
        for t in self.thumbnails_uploaded:
            self.wordpress.dele


    def test_publish_one(self):

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
        v.save()

        with self.settings(TRUNCATE_DESCRIPTION_AFTER=r"(c|C)lick"):
            p = self.publisher.publish_one(v)

        Publication.objects.get(post_id=p.post_id)

        post = self.wordpress.get(p.post_id)
        self.assertEqual(post.title, v.title)
        self.assertEqual(post.custom_fields[0]["key"], "youtube_id" )
        self.assertEqual(post.custom_fields[0]["value"], v.youtube_id )
        self.assertIn("Description of the video", post.content)
        self.assertNotIn("this should be hidden", post.content)
        self.assertIn(v.youtube_id, post.content)
        self.assertTrue(post.thumbnail)
        if v.transcript:
            self.assertIn(v.transcript, post.content)

        self.wordpress.delete(post.id)
        p.delete()
        v.delete()


