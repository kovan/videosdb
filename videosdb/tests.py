from django.test import TestCase
from videosdb.models import Video, Category
from vidoesdb_code  import Downloader
import yaml

class DownloaderTestCase(TestCase):
    def setUp(self):
        self.config = yaml.load(open("config.yaml"))

    def test_check_for_videos(self):
        dl = Downloader(self.config, None)
        dl.check_for_new_videos()
        #self.assertIs
