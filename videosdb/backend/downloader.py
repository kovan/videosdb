import logging
import json
from autologging import traced, TRACE
from videosdb.models import Video, Category
from .youtube_api import YoutubeAPI
from django.conf import settings


@traced(logging.getLogger(__name__))
class Downloader:
    def __init__(self):
        self.yt_api = YoutubeAPI(settings.YOUTUBE_KEY)


    def enqueue_videos(self, video_ids, category_name=None):

        def process_video(video):
            from django.utils.dateparse import parse_datetime

            #if new video or missing info, download info:
            if not video.title:
                info = self.yt_api.get_video_info(video.youtube_id)
                if not info:
                    video.excluded = True
                    return

                video.title = info["title"]
                video.description = info["description"]
                video.uploader = info["channelTitle"]
                video.channel_id = info["channelId"]
                video.yt_published_date = parse_datetime(info["publishedAt"])
                if "tags" in info:
                    video.set_tags(info["tags"])
                video.full_response = json.dumps(info)
                video.save()

            # some playlists include videos from other channels
            # for now exclude those videos
            # in the future maybe exclude whole playlist 
            if video.channel_id != settings.YOUTUBE_CHANNEL["id"]:
                video.excluded = True
                video.save()
                return

            if not video.transcript:
                video.transcript = self.yt_api.get_video_transcript(video.youtube_id)
                video.save()


        for yid in video_ids:
            video, created = Video.objects.get_or_create(youtube_id=yid)
            if video.excluded:
                continue

            process_video(video)
            if category_name:
                category, created = Category.objects.get_or_create(name=category_name)
                video.categories.add(category)
                video.save()




    def enqueue_channel(self, channel_id):
        playlists = self.yt_api.list_playlists(channel_id)
        for playlist in playlists:
            if playlist["channel_title"] != settings.YOUTUBE_CHANNEL["name"]:
                continue
            if playlist["title"] == "Liked videos" or \
                playlist["title"] == "Popular uploads":
                continue

            video_ids = self.yt_api.list_playlist_videos(playlist["id"])

            if playlist["title"] == "Uploads from " + playlist["channel_title"]:
                self.enqueue_videos(video_ids)
            else:
                self.enqueue_videos(video_ids, playlist["title"])

    def download_one(self, _id):
        self.enqueue_videos([_id]) 


    def check_for_new_videos(self):
        channel_id = settings.YOUTUBE_CHANNEL["id"]
        self.enqueue_channel(channel_id)

    def download_pending(self):
        videos = Video.objects.filter(excluded=False)
        self.enqueue_videos([v.youtube_id for v in videos if not v.title])

