import logging
import sys
import os
from autologging import traced, TRACE
from django.conf import settings
from .downloader import Downloader
from .publisher import Publisher


def dbg():
    os.chdir("/tmp")
    import ipdb
    ipdb.set_trace()


@traced(logging.getLogger("videosdb"))
def add_arguments(parser):
    parser.add_argument("-c", "--check-for-new-videos", action="store_true")
    parser.add_argument("-s", "--sync-wordpress", action="store_true")
    parser.add_argument("-d", "--download-one", dest="dl_video_id")
    parser.add_argument("-a", "--download-all", action="store_true")
    parser.add_argument("-p", "--publish-all", action="store_true")
    parser.add_argument("-o", "--publish-one", dest="video_id")
    parser.add_argument("--republish-all", action="store_true")


@traced(logging.getLogger("videosdb"))
def handle(*args, **options):

    if options["check_for_new_videos"]:
        downloader = Downloader()
        downloader.check_for_new_videos()

    if options["download_all"]:
        downloader = Downloader()
        downloader.download_all()

    if options["dl_video_id"]:
        downloader = Downloader()
        downloader.download_one(options["dl_video_id"])

    if options["republish_all"]:
        publisher = Publisher()
        publisher.republish_all()

    if options["sync_wordpress"]:
        publisher = Publisher()
        publisher.sync_wordpress()

    if options["video_id"]:
        publisher = Publisher()
        publisher.publish_one(options["video_id"])
