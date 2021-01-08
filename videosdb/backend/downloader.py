from django.utils.dateparse import parse_datetime
from .youtube_api import YoutubeAPI
from django.core.files import File
from django.conf import settings
from videosdb.models import Video, Category
from autologging import traced
from urllib.error import HTTPError
from urllib.request import urlretrieve
import json
import logging
import os


@traced(logging.getLogger("videosdb"))
class Downloader:
    def __init__(self):
        self.yt_api = YoutubeAPI(settings.YOUTUBE_KEY)
        if not os.path.exists(settings.MEDIA_ROOT):
            os.mkdir(settings.MEDIA_ROOT)

    def enqueue_videos(self, video_ids, category_name=None):

        def process_video(youtube_id, category_name=None):
            video, created = Video.objects.get_or_create(youtube_id=youtube_id)
            # if new video or missing info, download info:
            if created \
                    or not video.full_response \
                    or not video.title \
                    or not video.like_count:

                info = self.yt_api.get_video_info(video.youtube_id)
                if info:

                    video.title = info["title"]
                    video.description = info["description"]
                    video.uploader = info["channelTitle"]
                    video.channel_id = info["channelId"]
                    video.yt_published_date = parse_datetime(
                        info["publishedAt"])
                    video.view_count = int(info["viewCount"])
                    video.like_count = int(info["likeCount"])
                    video.dislike_count = int(info["dislikeCount"])
                    video.favorite_count = int(info["favoriteCount"])
                    video.comment_count = int(info["commentCount"])
                    video.definition = info["definition"]
                    video.duration = info["duration"]

                    if "tags" in info:
                        video.set_tags(info["tags"])
                    video.full_response = json.dumps(info)
                else:
                    video.excluded = True

            # some playlists include videos from other channels
            # for now exclude those videos
            # in the future maybe exclude whole playlist
            if video.channel_id != settings.YOUTUBE_CHANNEL["id"]:
                video.excluded = True

            if video.excluded:
                if video.is_dirty():
                    video.save()
                return

            if not video.thumbnail and video.full_response:
                info = json.loads(video.full_response)
                if "thumbnails" in info:
                    thumbnails = info["thumbnails"]
                    if "standard" in thumbnails:
                        tn = thumbnails["standard"]
                    elif "high" in thumbnails:
                        tn = thumbnails["high"]
                    elif "default" in thumbnails:
                        tn = thumbnails["default"]
                    elif "low" in thumbnails:
                        tn = thumbnails["low"]
                    else:
                        tn = None

                    if tn:
                        url = tn["url"]
                        try:
                            tempname, _ = urlretrieve(
                                url, "%s/%s.jpg" % (settings.MEDIA_ROOT, video.youtube_id))
                            f = File(open(tempname, 'rb'))
                            video.thumbnail = f
                            f.close()
                            os.remove(tempname)
                        except HTTPError:
                            video.thumbnail = None

            if not video.transcript:
                video.transcript = self.yt_api.get_video_transcript(
                    video.youtube_id)

            if category_name:
                category, created = Category.objects.get_or_create(
                    name=category_name)
                video.categories.add(category)

            if video.is_dirty():
                video.save()

        # threads = []
        # for i in range(len(video_ids)):
        #     thread = self.loop.create_task(
        #         process_video(video_ids[i], category_name))
        #     threads.append(thread)
        # self.loop.run_until_complete(asyncio.gather(*threads))
        for yid in video_ids:
            process_video(yid, category_name)

    def enqueue_channel(self, channel_id):
        def process_playlist(playlist):

            if playlist["channel_title"] != settings.YOUTUBE_CHANNEL["name"]:
                return
            if playlist["title"] == "Liked videos" or \
                    playlist["title"] == "Popular uploads":
                return

            video_ids = self.yt_api.list_playlist_videos(playlist["id"])

            if playlist["title"] == "Uploads from " + playlist["channel_title"]:
                self.enqueue_videos(video_ids)
            else:
                self.enqueue_videos(video_ids, playlist["title"])

        playlists = self.yt_api.list_playlists(channel_id)
        for playlist in playlists:
            process_playlist(playlist)

        # threads = []
        # for i in range(len(playlists)):
        #     thread = self.loop.create_task(
        #         process_playlist(playlists[i]))
        #     threads.append(thread)
        # self.loop.run_until_complete(asyncio.gather(*threads))

    def download_one(self, youtube_id):
        self.enqueue_videos([youtube_id])

    def download_all(self):
        all = Video.objects.filter(excluded=False)
        self.enqueue_videos([v.youtube_id for v in all])

    def check_for_new_videos(self):
        channel_id = settings.YOUTUBE_CHANNEL["id"]
        self.enqueue_channel(channel_id)

    def download_pending(self):
        videos = Video.objects.filter(excluded=False)
        self.enqueue_videos([v.youtube_id for v in videos if not v.title])
