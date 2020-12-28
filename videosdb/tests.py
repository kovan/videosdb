from django.test import TestCase
from django.utils import timezone
from videosdb.models import Video, Category
from videosdb.backend.code  import Publisher, Downloader, Wordpress, Publication

import os



def dbg():
    os.chdir("/tmp")
    import ipdb
    ipdb.set_trace()


#class DownloaderTestCase(TestCase):
#    def setUp(self):

    #def test_check_for_videos(self):
    #    dl = Downloader(self.config, None)
    #    dl.check_for_new_videos()
        #self.assertIs

#class APITest(TestCase):
#    def test_api_works(self):
#        wp = Wordpress(config)
#        response = wp.set_menus({})

class PublisherTest(TestCase):
    def test_publish_one(self):

        v = Video()
        v.youtube_id = "xxxxxxxxxxx"
        v.title = "New video title"
        v.description = "Description of the video click this should be hidden"
        v.transcript = "This is the transcript"
        v.excluded = False
        v.uploader = "Sadhguru"
        v.channel_id = "UCcYzLCs3zrQIBVHYA1sK2sw"
        v.yt_published_date = timezone.now()
        v.save()
        publisher = Publisher()
        with self.settings(TRUNCATE_DESCRIPTION_AFTER=r"(c|C)lick"):
            p = publisher.publish_one(v)

        Publication.objects.get(post_id=p.post_id)
        w = Wordpress()
        post = w.get(p.post_id)
        self.assertEqual(post.title, v.title)
        self.assertEqual(post.custom_fields[0]["key"], "youtube_id" )
        self.assertEqual(post.custom_fields[0]["value"], v.youtube_id )
        self.assertIn("Description of the video", post.content)
        self.assertNotIn("this should be hidden", post.content)
        self.assertIn(v.youtube_id, post.content)
        if v.transcript:
            self.assertIn(v.transcript, post.content)

        w.delete(post.id)
        p.delete()
        v.delete()

    def test_sync(self):
        pass
