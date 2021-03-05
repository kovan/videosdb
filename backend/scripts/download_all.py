import logging
from videosdb.models import Video
from videosdb.backend.youtube_api import YoutubeDL
import os

from django.conf import settings

def run():
    os.chdir(settings.VIDEO_FILES_DIR)
    yt_dl = YoutubeDL()
    for video in Video.objects.filter(excluded=False):
        logging.debug("Downloading " + video.youtube_id)
        try:
            yt_dl.download_video(
                video.youtube_id, asynchronous=False)
        except YoutubeDL.UnavailableError as e:
            logging.error(repr(e))
            continue
