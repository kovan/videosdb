from django.test import TestCase
from videosdb.models import Video, Category
from videosdb_code  import Downloader, Wordpress
import yaml
import os

config = yaml.load(open("config.yaml"))

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

class APITest(TestCase):
    def test_api_works(self):
        wp = Wordpress(config)
        response = wp.set_menus({})
