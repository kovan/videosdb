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
def configure_logging(enable_trace):
    import logging.handlers
    
    logger = logging.getLogger("videosdb")
    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s')
    if not os.path.exists("logs"):
        os.makedirs("logs")
    handler = logging.handlers.RotatingFileHandler("./logs/log", 'a', 1000000, 10)
    handler2 = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler2.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(handler2)

    if enable_trace:
        logger.setLevel(TRACE)

@traced(logging.getLogger("videosdb"))
def add_arguments(parser):
    parser.add_argument("-t", "--trace", action="store_true")
    parser.add_argument("-c", "--check-for-new-videos", action="store_true")
    parser.add_argument("-s", "--sync-wordpress", action="store_true")
    parser.add_argument("-a", "--publish-all", action="store_true")
    parser.add_argument("-o", "--publish-one", dest="video_id")
    parser.add_argument("--republish-all", action="store_true")


@traced(logging.getLogger("videosdb"))
def handle(*args, **options):

    configure_logging(options["trace"])

    downloader = Downloader()

    if options["check_for_new_videos"]:
        downloader.check_for_new_videos()

    publisher = Publisher()

    if options["republish_all"]:
        publisher.republish_all()

    if options["sync_wordpress"]:
        publisher.sync_wordpress()
     
    if options["video_id"]:
        publisher.publish_one(options["video_id"])
