import logging
import sys
import os
from autologging import traced, TRACE
from django.conf import settings
from .downloader import Downloader


def dbg():
    os.chdir("/tmp")
    import ipdb
    ipdb.set_trace()


@traced(logging.getLogger(__name__))
def add_arguments(parser):
    parser.add_argument("-c", "--check-for-new-videos", action="store_true")
    parser.add_argument("-d", "--download-one", dest="dl_video_id")
    parser.add_argument("-a", "--download-all", action="store_true")
    parser.add_argument(
        "-f", "--download-and-register-in-ipfs", action="store_true")


@traced(logging.getLogger(__name__))
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

    if options["download_and_register_in_ipfs"]:
        downloader = Downloader()
        downloader.download_and_register_in_ipfs()
