import logging
from videosdb.models import Video
from videosdb.backend.youtube_api import YoutubeDL


def run():
    yt_dl = YoutubeDL()
    for video in Video.objects.filter(excluded=False):
        logging.debug("Downloading " + video.youtube_id)
        try:
            yt_dl.download_video(
                video.youtube_id, asynchronous=True)
        except YoutubeDL.UnavailableError as e:
            logging.error(repr(e))
            continue
