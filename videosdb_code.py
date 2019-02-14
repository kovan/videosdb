#!env python3
from executor import execute
import executor
from autologging import traced, TRACE
import tempfile
import requests
import logging
import json
import sys
import os
import io
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
        return self.client.call(media.GetMediaItem(image_id))
        

    def publish(self, video, as_draft):
        from wordpress_xmlrpc import WordPressPost
        from wordpress_xmlrpc.methods.posts import NewPost, GetPosts, EditPost
        from string import Template
        from urllib.parse import quote
        template_raw = \
        '''
        <!-- wp:video {"align":"center"} -->
        <figure class="wp-block-video aligncenter">
            <video controls preload="none" poster="$thumbnail_url" src="https://$ipfs_gateway/ipfs/$ipfs_hash?filename=$filename_quoted">
            </video>
            <figcaption>
        Download/play from: <a href="https://$ipfs_gateway/ipfs/$ipfs_hash?filename=$filename_quoted">HTTP</a> | <a href="ipns://$ipfs_hash?filename=$filename_quoted">IPFS</a> | <a href="https://www.youtube.com/watch?v=$youtube_id">YouTube</a>
            </figcaption>
        </figure>
        <!-- /wp:video -->
        '''

        thumbnail = self.find_image(video.thumbnail_id)
        template = Template(template_raw)
        html = template.substitute(
            youtube_id=video.youtube_id,
            ipfs_gateway=self.config["ipfs_gateway"],
            www_root=self.config["www_root"],
            filename_quoted=quote(video.filename),
            ipfs_hash=video.ipfs_hash,
            thumbnail_url=thumbnail.link
        )

        post = WordPressPost()
        post.title = video.title
        post.content = html
        post.thumbnail = video.thumbnail_id
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

        if video.published:
            return self.client.call(EditPost(video.post_id, post))

        return self.client.call(NewPost(post))


@traced(logging.getLogger(__name__))
class DNS:
    def __init__(self, dns_zone, record_name):
        self.dns_zone = dns_zone
        self.record_name = record_name

    def update(self, new_root_hash):
        from google.cloud import dns
        client = dns.Client()
        zone = client.zone(self.dns_zone)
        records = zone.list_resource_record_sets()

        # init transaction
        changes = zone.changes()
        # delete old
        for record in records:
            if record.name == self.record_name + "."  and record.record_type == "TXT":
                changes.delete_record_set(record)
        #add new
        record = zone.resource_record_set(self.record_name + ".","TXT", 300, ["dnslink=/ipfs/"+ new_root_hash,])
        changes.add_record_set(record)
        #finish transaction
        changes.create()


@traced(logging.getLogger(__name__))
class IPFS:
    def __init__(self, config):
        import ipfsapi
        self.config = config
        self.host = self.config["ipfs_host"]
        self.port = self.config["ipfs_port"]
        self.dnslink_update_pending = False
        self.api = ipfsapi.connect(self.host, self.port)

    def add_file(self, filename, add_to_dir=True):
        ipfs_hash = self.api.add(filename)["Hash"]
        self.api.pin_add(ipfs_hash)

        if add_to_dir:
            self.add_to_dir(filename, ipfs_hash)

        return ipfs_hash

    def add_to_dir(self, filename, _hash):
        from ipfsapi.exceptions import StatusError
        src = "/ipfs/"+ _hash
        dst =  "/videos/" + filename
        try:
            self.api.files_rm(dst)
        except StatusError:
            pass
        self.api.files_cp(src, dst)
        self.dnslink_update_pending = True


    def get_file(self, ipfs_hash):
        self.api.get(ipfs_hash)
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    def update_dnslink(self, force=False):
        if not self.dnslink_update_pending and not force:
            return

        root_hash = self.api.files_stat("/")["Hash"]
        dns = DNS(self.config["dns_zone"], self.config["dnslink_name"])
        dns.update(root_hash)
        self.dnslink_update_pending = False


@traced(logging.getLogger(__name__))
class YoutubeDL:
    class UnavailableError(Exception):
        pass

    BASE_CMD =  "youtube-dl --ffmpeg-location /dev/null --youtube-skip-dash-manifest --ignore-errors "

    @staticmethod
    def download_video(_id):
        filename_format = "%(uploader)s - %(title)s [%(id)s].%(ext)s"
        execute(YoutubeDL.BASE_CMD + "--output '%s' %s" %( filename_format,"http://www.youtube.com/watch?v=" + _id))
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    @staticmethod
    def download_thumbnail(_id):
        execute(YoutubeDL.BASE_CMD + "--write-thumbnail --skip-download http://www.youtube.com/watch?v=" + _id)
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    @staticmethod
    def download_info(youtube_id):
        cmd = YoutubeDL.BASE_CMD + "--write-info-json --skip-download --output '%(id)s' http://www.youtube.com/watch?v=" + youtube_id
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                result = execute(cmd, capture_stderr=True)
                with io.open(youtube_id + ".info.json") as f:
                    video_json = json.load(f)
        except executor.ExternalCommandFailed as e:
            if "copyright" in str(e.command.stderr) or \
               "Unable to extract video title" in str(e.command.stderr) or \
               "available in your country" in str(e.command.stderr):
                raise YoutubeDL.UnavailableError()
            raise
        return video_json

    @staticmethod
    def list_videos(url):
        result = execute(YoutubeDL.BASE_CMD + "--flat-playlist --playlist-random -j " + url, check=False, capture=True, capture_stderr=True)
        videos = []
        for video_json in result.splitlines():
            video = json.loads(video_json)
            videos.append(video)
        return videos



class YoutubeAPI:
    def __init__(self, yt_key):
        self.yt_key = yt_key

    def _make_request(self, base_url, page_token=""):
        url = base_url
        url += "&key=" + self.yt_key
        if page_token:
            url += "&pageToken=" + page_token

        response = requests.get(url)
        response.raise_for_status()
        items = response.json()["items"]
        if "nextPageToken" in response:
            items += self._make_request(base_url, response["nextPageToken"])
        return items

    def _get_playlist_info(self, playlist_id):
        url = "https://www.googleapis.com/youtube/v3/playlists?part=snippet%2C+contentDetails"
        url += "&id=" + playlist_id
        items = self._make_request(url)
        playlist = {
            "id": playlist_id,
            "title": items[0]["snippet"]["title"],
            "channel_title": items[0]["snippet"]["channelTitle"],
            "item_count": items[0]["contentDetails"]["itemCount"],
        } 
        return playlist

    def _get_channnelsection_playlists(self, channel_id):
        url = "https://www.googleapis.com/youtube/v3/channelSections?part=snippet%2CcontentDetails" 
        url += "&channelId=" + channel_id
        items = self._make_request(url)
        playlist_ids = []
        for item in items:
            details = item.get("contentDetails")
            if not details:
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
        url = "https://www.googleapis.com/youtube/v3/videos?part=snippet%2CcontentDetails%2Cstatistics"
        url += "&id=" + youtube_id
        items = self._make_request(url)
        if items:
            return items[0]
        return None


@traced(logging.getLogger(__name__))
class Downloader:
    def __init__(self, config, ipfs):
        self.config = config
        self.ipfs = ipfs
        self.yt_api = YoutubeAPI(config["youtube_key"])


    def enqueue_videos(self, video_ids, category_name=None):

        def process_video(video):

            #if new video or missing info, download info:
            if not video.title:
                info = YoutubeDL.download_info(video.youtube_id)
                video.title = info["title"]
                video.uploader = info["uploader"]
                video.channel_id = info["channel_id"]
                video.duration = info["duration"]
                video.set_tags(info["tags"])
                video.full_response = json.dumps(info)
                # dont use YT API in order to save quota.
                #
                #info = self.yt_api.get_video_info(video.youtube_id)
                #if not info:
                #    video.excluded = True
                #    return
                #video.parse_youtubeapi_info(info)
                #video.title = info["title"]
                #video.uploader = info["channelTitle"]
                #video.channel_id = info["channelId"]
                #video.set_tags(info["tags"])


            # some playlists include videos from other channels
            # for now exclude those videos
            # in the future maybe exclude whole playlist 
            if video.channel_id != self.config["youtube_channel"]["id"]:
                video.excluded = True
                return
            
            if not self.ipfs:
                return

            if not video.ipfs_hash:
                with tempfile.TemporaryDirectory() as tmpdir:
                    os.chdir(tmpdir)
                    video.filename = YoutubeDL.download_video(video.youtube_id)
                    video.ipfs_hash= self.ipfs.add_file(video.filename)

            if not video.ipfs_thumbnail_hash:
                with tempfile.TemporaryDirectory() as tmpdir:
                    os.chdir(tmpdir)
                    thumbnail_filename = YoutubeDL.download_thumbnail(video.youtube_id)
                    video.ipfs_thumbnail_hash = self.ipfs.add_file(thumbnail_filename, False)
                 


        for yid in video_ids:
            video, created = Video.objects.get_or_create(youtube_id=yid)
            if video.excluded:
                continue
            try:
                process_video(video)
                if category_name:
                    category, created = Category.objects.get_or_create(name=category_name)
                    video.categories.add(category)

            except YoutubeDL.UnavailableError:
                video.excluded = True
            finally:
                video.save()



    def enqueue_channel(self, channel_id):
        playlists = self.yt_api.list_playlists(channel_id)
        for playlist in playlists:
            if playlist["channel_title"] != self.config["youtube_channel"]["name"]:
                continue
            if playlist["title"] == "Uploads from " + playlist["channel_title"] or \
                playlist["title"] == "Liked videos" or \
                playlist["title"] == "Popular uploads":
                continue

            playlist_url = "http://www.youtube.com/playlist?list=" + playlist["id"]
            videos = YoutubeDL.list_videos(playlist_url)
            video_ids = [video["id"] for video in videos]
            self.enqueue_videos(video_ids, playlist["title"])

        # enqueue all channel videos that are not in playlists:
        channel_url = "http://www.youtube.com/channel/" + channel_id
        videos = YoutubeDL.list_videos(channel_url)
        video_ids = [video["id"] for video in videos]
        self.enqueue_videos(video_ids)


    def check_for_new_videos(self):
        channel_id = self.config["youtube_channel"]["id"]
        self.enqueue_channel(channel_id)
        if self.ipfs:
            self.ipfs.update_dnslink()

    def regen_ipfs_folder(self):
        self.ipfs.api.files_mkdir("/videos")
        for video in Video.objects.all():
            self.ipfs.add_to_dir(video.filename, video.ipfs_hash)

@traced(logging.getLogger(__name__))
class Publisher:
    def __init__(self, config, ipfs):
        self.config = config
        self.ipfs = ipfs
        self.wordpress = Wordpress(config)

    def publish_one(self, video, as_draft=False):
        from datetime import datetime

        new_categories = [
             "Short videos" if video.duration/60 <= 20 else "Long videos", 
             video.uploader
        ]
        for category in new_categories:
            category, created = Category.objects.get_or_create(name=category)
            video.categories.add(category)


        if not video.published:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                thumbnail_filename = self.ipfs.get_file(video.ipfs_thumbnail_hash)
                thumbnail = self.wordpress.upload_image(thumbnail_filename, video.title)
                video.thumbnail_id = thumbnail["id"]

        post_id = self.wordpress.publish(video, as_draft)

        video.published = True
        video.post_id = post_id
        video.published_date = datetime.now()
        video.save()


    def publish_next(self, as_draft=False):
        pending_videos = Video.objects.filter(published=False, excluded=False).order_by("-id")
        if not pending_videos:
            return False

        self.publish_one(pending_videos[0], as_draft)
        return True


    def publish_all(self):
        while self.publish_next():
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
class Main:
    def __init__(self, config):
        self.config = config

    def configure_logging(self, enable_trace=False):
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


