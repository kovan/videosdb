#!env python3
import logging
import json
import sys
import os
import requests
from autologging import traced, TRACE
from videosdb.models import Video, Category


def dbg():
    os.chdir("/tmp")
    import ipdb
    ipdb.set_trace()

@traced(logging.getLogger(__name__))
class Wordpress:
    def __init__(self, config):
        from wordpress_xmlrpc import Client
        self.config = config
        self.client = Client(
            self.config["www_root"] + "/xmlrpc.php",
            self.config["wp_username"],
            self.config["wp_pass"])

    def upload_image(self, filename, title):
        from wordpress_xmlrpc.compat import xmlrpc_client
        from wordpress_xmlrpc.methods import media

        data = {
            "name": title + ".jpg",
            'type': 'image/jpeg',
        }

        with open(filename, 'rb') as img:
            data['bits'] = xmlrpc_client.Binary(img.read())

        thumbnail = self.client.call(media.UploadFile(data))
        return thumbnail

    def find_image(self, image_id):
        from wordpress_xmlrpc.methods import media
        from xmlrpc.client import Fault
        return self.client.call(media.GetMediaItem(image_id))

    def delete(self, video):
        from wordpress_xmlrpc.methods.posts import DeletePost
        return self.client.call(DeletePost(video.post_id))


    def publish(self, video: Video, as_draft: bool):
        import xmlrpc
        from wordpress_xmlrpc import WordPressPost
        from wordpress_xmlrpc.methods.posts import NewPost, GetPosts, EditPost
        from string import Template
        from urllib.parse import quote
        template_raw = \
                '''
<!-- wp:embed {"url":"https://www.youtube.com/watch?v=$youtube_id","type":"video","providerNameSlug":"youtube","responsive":true,"className":"wp-embed-aspect-16-9 wp-has-aspect-ratio"} -->
<figure class="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio"><div class="wp-block-embed__wrapper">
https://www.youtube.com/watch?v=$youtube_id
</div></figure>
<!-- /wp:embed -->

<!-- wp:paragraph {"fontSize":"small"} -->
<p class="has-small-font-size">$transcript</p>
<!-- /wp:paragraph -->
                '''

        #thumbnail = self.find_image(video.thumbnail_id)
        template = Template(template_raw)
        html = template.substitute(
            youtube_id=video.youtube_id,
	    transcript= "" if not video.transcript else "TRANSCRIPT: " + video.transcript
        )

        post = WordPressPost()
        post.title = video.title
        post.content = html
        #post.thumbnail = video.thumbnail_id
        post.custom_fields = [{
            "key": "youtube_id",
            "value": video.youtube_id
        }]

        post.terms_names = {}

        if video.categories:
            post.terms_names["category"] = [str(c) for c in video.categories.all()]
        
        if video.tags:
            post.terms_names["post_tag"] = [str(t) for t in video.tags.all()]

        if not as_draft:
            post.post_status = "publish"

        print ("publishing " + str(video.post_id))
        
        if video.published:
            return self.client.call(EditPost(video.post_id, post))

        return self.client.call(NewPost(post))




class YoutubeAPI:
    def __init__(self, yt_key):
        self.yt_key = yt_key

    def _make_request(self, base_url, page_token=""):
        url = base_url
        if page_token:
            url += "&pageToken=" + page_token
        url += "&key=" + self.yt_key

        print("request: " + url)
        response = requests.get(url)
        response.raise_for_status()
        json = response.json()
        items = json["items"]
        if "nextPageToken" in json:
            items += self._make_request(base_url, json["nextPageToken"])
        return items

    def _get_playlist_info(self, playlist_id):
        url = "https://www.googleapis.com/youtube/v3/playlists?part=snippet"
        url += "&id=" + playlist_id
        items = self._make_request(url)
        playlist = {
            "id": playlist_id,
            "title": items[0]["snippet"]["title"],
            "channel_title": items[0]["snippet"]["channelTitle"]
        } 
        return playlist

    def _get_channnelsection_playlists(self, channel_id):
        url = "https://www.googleapis.com/youtube/v3/channelSections?part=contentDetails" 
        url += "&channelId=" + channel_id
        items = self._make_request(url)
        playlist_ids = []
        for item in items:
            details = item.get("contentDetails")
            if not details:
                continue
            if not "playlists" in details:
                continue
            playlist_ids += details["playlists"]
        return playlist_ids

    def _get_channel_playlists(self, channel_id):
        url = "https://www.googleapis.com/youtube/v3/playlists?part=snippet%2C+contentDetails"
        url += "&channelId=" + channel_id
        items = self._make_request(url)
        playlist_ids = []
        for item in items:
            playlist_ids.append(item["id"])
        return playlist_ids

    def list_playlists(self, channel_id):
        ids_channelsection = self._get_channnelsection_playlists(channel_id) 
        ids_channel =  self._get_channel_playlists(channel_id) 

        playlist_ids = set(ids_channelsection + ids_channel)
        playlists = []
        for _id in playlist_ids:
            playlist = self._get_playlist_info(_id)
            playlists.append(playlist)

        return playlists

    def get_video_info(self, youtube_id):
        url = "https://www.googleapis.com/youtube/v3/videos?part=snippet"
        url += "&id=" + youtube_id
        items = self._make_request(url)
        if items:
            video_info = items[0]["snippet"]
            return video_info
        return None

    def list_playlist_videos(self, playlist_id):
        url = "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet"
        url += "&playlistId=" + playlist_id
        items = self._make_request(url)
        video_ids = []
        for item in items:
            video_ids.append(item["snippet"]["resourceId"]["videoId"])
        return video_ids

    def get_video_transcript(self, youtube_id):
        from youtube_transcript_api import YouTubeTranscriptApi
        try:
            t = YouTubeTranscriptApi.get_transcript(youtube_id)
        except Exception:
            return None

        result = ""
        for d in t:
            result += d["text"] + " "
        return result.capitalize() + "."




@traced(logging.getLogger(__name__))
class Downloader:
    def __init__(self, config):
        self.config = config
        self.yt_api = YoutubeAPI(config["youtube_key"])


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

            # some playlists include videos from other channels
            # for now exclude those videos
            # in the future maybe exclude whole playlist 
            if video.channel_id != self.config["youtube_channel"]["id"]:
                video.excluded = True
                return
                 
            if not video.transcript:
                video.transcript = self.yt_api.get_video_transcript(video.youtube_id)


        for yid in video_ids:
            video, created = Video.objects.get_or_create(youtube_id=yid)
            if video.excluded:
                continue
            try:
                process_video(video)
                if category_name:
                    category, created = Category.objects.get_or_create(name=category_name)
                    video.categories.add(category)

            finally:
                video.save()



    def enqueue_channel(self, channel_id):
        playlists = self.yt_api.list_playlists(channel_id)
        for playlist in playlists:
            if playlist["channel_title"] != self.config["youtube_channel"]["name"]:
                continue
            if playlist["title"] == "Liked videos" or \
                playlist["title"] == "Popular uploads":
                continue

            video_ids = self.yt_api.list_playlist_videos(playlist["id"])

            if playlist["title"] == "Uploads from " + playlist["channel_title"]:
                print(len(video_ids))
                self.enqueue_videos(video_ids)
            else:
                self.enqueue_videos(video_ids, playlist["title"])

    def download_one(self, _id):
       self.enqueue_videos([_id]) 


    def check_for_new_videos(self):
        channel_id = self.config["youtube_channel"]["id"]
        self.enqueue_channel(channel_id)

    def download_pending(self):
        videos = Video.objects.filter(excluded=False)
        self.enqueue_videos([v.youtube_id for v in videos if not v.title])


@traced(logging.getLogger(__name__))
class Publisher:
    def __init__(self, config):
        self.config = config
        self.wordpress = Wordpress(config)

    def publish_one(self, video, as_draft=False):
        from django.utils import timezone
        if type(video) is not Video:
            video = Video.objects.get(youtube_id=video)

        new_categories = []
        for category in new_categories:
            category, created = Category.objects.get_or_create(name=category)
            video.categories.add(category)

        post_id = self.wordpress.publish(video, as_draft)

        video.published = True
        video.post_id = post_id
        video.published_date = timezone.now()
        video.save()


    def publish_next(self, as_draft=False):
        #first publish newer videos:
        pending_videos = Video.objects.filter(published=False, excluded=False).order_by("-id")
        if not pending_videos:
            #if there are no new videos left, republish oldest ones:
            pending_videos = Video.objects.filter(excluded=False).order_by("published_date")
            if not pending_videos:
                return False
            self.wordpress.delete(pending_videos[0])
            pending_videos[0].published = False
            pending_videos[0].save()
            

        self.publish_one(pending_videos[0], as_draft)
        return True


    def publish_all(self, as_draft=False):
        videos = Video.objects.filter(excluded=False)
        for video in videos:
            self.publish_one(video, as_draft)
        
    def sync_wordpress(self):
        pass
        
    def republish_all(self):
        for video in Video.objects.filter(published=True):
            self.publish_one(video) 

    def reset_published(self):
        for video in Video.objects.filter(published=True):
            video.published = False
            video.published_date = None
            video.post_id = None
            video.thumbnail_id = None
            video.save()



@traced(logging.getLogger(__name__))
def configure_logging(enable_trace):
    import logging.handlers
    import pathlib
    
    logger = logging.getLogger(__name__)
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

@traced(logging.getLogger(__name__))
def add_arguments(parser):
    parser.add_argument("-t", "--trace", action="store_true")
    parser.add_argument("-c", "--check-for-new-videos", action="store_true")
    parser.add_argument("-s", "--sync-wordpress", action="store_true")
    parser.add_argument("-n", "--publish-next", action="store_true")
    parser.add_argument("-a", "--publish-all", action="store_true")
    parser.add_argument("-o", "--publish-one", dest="video_id")
    parser.add_argument("--republish-all", action="store_true")
    parser.add_argument("--as-draft", action="store_true")


@traced(logging.getLogger(__name__))
def handle(*args, **options):
    import yaml
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    configure_logging(options["trace"])

    downloader = Downloader(config)

    if options["check_for_new_videos"]:
        downloader.check_for_new_videos()

    publisher = Publisher(config)

    if options["republish_all"]:
        publisher.republish_all()

    if options["publish_all"]:
        publisher.publish_all()

    if options["publish_next"]:
        publisher.publish_next(options["as_draft"])

    if options["sync_wordpress"]:
        publisher.sync_wordpress()
        
    if options["video_id"]:
        publisher.publish_one(options["video_id"], options["as_draft"])

        


