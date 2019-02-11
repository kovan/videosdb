#!env python3
from executor import execute
import executor
from autologging import traced, TRACE
import tempfile
import requests
import logging
import logging.handlers
import json
import sys
import os
import io



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
        from wordpress_xmlrpc.methods import media, posts

        data = {
            "name": title + ".jpg",
            'type': 'image/jpeg',
        }

        with open(filename, 'rb') as img:
            data['bits'] = xmlrpc_client.Binary(img.read())

        thumbnail = self.client.call(media.UploadFile(data))
        return thumbnail


    def publish(self, video, categories, tags, thumbnail_id, thumbnail_url, post_id=None, as_draft=False):
        from wordpress_xmlrpc import WordPressPost
        from wordpress_xmlrpc.methods.posts import NewPost, GetPosts, EditPost
        from string import Template
        from urllib.parse import quote
        template_raw = \
        '''
        <!-- wp:video {"align":"center"} -->
        <figure class="wp-block-video aligncenter">
            <video controls poster="$thumbnail_url" src="https://$dnslink_name/videos/$filename_quoted">
            </video>
            <figcaption>
        Download/play from: <a href="ipns://$dnslink_name/videos/$filename_quoted">IPFS</a> | <a href="https://$dnslink_name/videos/$filename_quoted">HTTP</a> | <a href="https://www.youtube.com/watch?v=$youtube_id">YouTube</a>
            </figcaption>
        </figure>
        <!-- /wp:video -->
        '''

        template = Template(template_raw)
        html = template.substitute(
            youtube_id=video["youtube_id"],
            dnslink_name=self.config["dnslink_name"],
            www_root=self.config["www_root"],
            filename_quoted=quote(video.get("filename")),
            thumbnail_url=thumbnail_url
        )

        post = WordPressPost()
        post.title = video["title"]
        post.content = html
        post.thumbnail = thumbnail_id
        post.custom_fields = [{
            "key": "youtube_id",
            "value": video["youtube_id"]
        }]
        post.terms_names = {
            "category": categories
        }
        if tags:
            post.terms_names["post_tag"] = tags

        if not as_draft:
            post.post_status = "publish"

        if post_id: # it is an edit
            return self.client.call(EditPost(post_id, post))

        return self.client.call(NewPost(post))


@traced(logging.getLogger(__name__))
class DNS:
    def __init__(self, config):
        self.config = config

    def update(new_root_hash):
        from google.cloud import dns
        client = dns.Client()
        zone = client.zone(self.config["dns_zone"])
        records = zone.list_resource_record_sets()

        # init transaction
        changes = zone.changes()
        # delete old
        for record in records:
            if record.name == self.config["dnslink_name"] + "."  and record.record_type == "TXT":
                changes.delete_record_set(record)
        #add new
        record = zone.resource_record_set(self.config["dnslink_name"] + ".","TXT", 300, ["dnslink=/ipfs/"+ new_root_hash,])
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
        file_hash = self.api.add(filename)["Hash"]
        self.api.pin_add(file_hash)

        if add_to_dir:
            self.add_to_dir(filename, file_hash)

        return file_hash

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
        dns = DNS(self.config)
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
        execute(YoutubeDL.BASE_CMD + "--output '%s' %s" %( filename_format,"https://www.youtube.com/watch?v=" + _id))
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    @staticmethod
    def download_thumbnail(_id):
        execute(YoutubeDL.BASE_CMD + "--write-thumbnail --skip-download https://www.youtube.com/watch?v=" + _id)
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    @staticmethod
    def download_info(youtube_id):
        cmd = YoutubeDL.BASE_CMD + "--write-info-json --skip-download --output '%(id)s' https://www.youtube.com/watch?v=" + youtube_id
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
    def __init__(self, config):
        self.config = config

    def _make_request(self, base_url, page_token=""):
        url = base_url
        url += "&key=" + self.config["youtube_key"]
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
        params = {
            
        }
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
        return items[0]


@traced(logging.getLogger(__name__))
class DB:
    def __init__(self):
        import dataset
        self.db = dataset.connect("sqlite:///db.db")

    def queue_next(self):
        # treat table as a LIFO stack, so that recent videos get published first:
        #video = video.objects.filter(
        video = self.db["publish_queue"].find_one(published=False, excluded=False, order_by=["-id"])
        return video

    def queue_upsert(self, video):
        from videosdb.models import video
        self.db["publish_queue"].upsert(video, ["youtube_id"], ensure=True)

    def get_video(self, youtube_id):
        return self.db["publish_queue"].find_one(youtube_id=youtube_id)

    def get_videos(self):
        return self.db["publish_queue"].all()

    def get_videos(self):
        return self.db["videos"].all()

    def get_video(self, youtube_id):
        return self.db["videos"].find_one(youtube_id=youtube_id)

    def put_video(self, video):
        self.db["videos"].upsert(video,["youtube_id"], ensure=True)



@traced(logging.getLogger(__name__))
class Main:
    def __init__(self, enable_trace=False, enable_ipfs=True):
        import yaml
        with io.open("config.yaml") as f:
            self.config = yaml.load(f)
            
        self._configure_logging(enable_trace)
        self.db = DB()

        if enable_ipfs:
            self.ipfs = IPFS(self.config)
        else:
            self.ipfs = None

    def _configure_logging(self, enable_trace=False):
        import logging
        
        logger = logging.getLogger(__name__)
        formatter = logging.Formatter('%(asctime)s %(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s')
        handler = logging.handlers.RotatingFileHandler("log", 'a', 1000000, 10)
        handler2 = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        handler2.setFormatter(formatter)
        logger.addHandler(handler)
        logger.addHandler(handler2)

        #logging.getLogger("executor").setLevel(logging.DEBUG)
        #logging.getLogger().setLevel(logging.DEBUG)

        if enable_trace:
            logger.setLevel(TRACE)

    def regen_ipfs_folder(self):
        self.ipfs.api.files_mkdir("/videos")
        for video in self.db.get_videos():
            self.ipfs.add_to_dir(video["filename"], video["ipfs_hash"])
        #self.ipfs.update_dnslink()
            

    def download_all(self):
        ids = [video["youtube_id"] for video in self.db.get_videos()]
        for _id in ids: 
            self.download_one(_id, False)

        if self.ipfs:
            self.ipfs.update_dnslink()


    def download_one(self, youtube_id, update_dnslink=True):
        video = self.db.get_video(youtube_id)
        if not video:
            video = dict()
            video["youtube_id"] = youtube_id

        try:
            self._fill_info(video)
            self.db.put_video(video)

            if self.ipfs:
                with tempfile.TemporaryDirectory() as tmpdir:
                    os.chdir(tmpdir)
                    if not video.get("ipfs_hash"):
                        video["filename"] = YoutubeDL.download_video(video["youtube_id"])
                        video["ipfs_hash"]= self.ipfs.add_file(video["filename"])
                    if not video.get("ipfs_thumbnail_hash"):
                        thumbnail_filename = YoutubeDL.download_thumbnail(video["youtube_id"])
                        video["ipfs_thumbnail_hash"] = self.ipfs.add_file(thumbnail_filename, False)
                if update_dnslink:
                    self.ipfs.update_dnslink()

        except YoutubeDL.UnavailableError as e:
            return None

        self.db.put_video(video)
        return video


    def publish_one(self, video, as_draft=False):
        from videosdb.models import video
        from datetime import datetime

        video = self.download_one(video["youtube_id"])
        if not video:
            video["excluded"] = True
            self.db.queue_upsert(video)
            return False

        tags = Taxonomy(video["tags"])
        categories = Taxonomy(video.get("categories"))
        categories.add("Short videos" if video["duration"]/60 <= 20 else "Long videos")
        categories.add(video["uploader"])
            
        wp = Wordpress(self.config)

        if video["published"]:
            post_id = video["post_id"]
        else:
            post_id = None
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                thumbnail_filename = self.ipfs.get_file(video["ipfs_thumbnail_hash"])
                thumbnail = wp.upload_image(thumbnail_filename, video["title"])
                video["thumbnail_id"] = thumbnail["id"]
                video["thumbnail_url"] = thumbnail["link"]

        post_id = wp.publish(
            video, 
            categories.as_list(), 
            tags.as_list(), 
            video["thumbnail_id"],
            video["thumbnail_url"],
            post_id, 
            as_draft)

        video["published"] = True
        video["post_id"] = post_id
        video["publish_date"] = datetime.now()
        video["tags"] = tags.serialize()
        video["categories"] = categories.serialize()
        self.db.queue_upsert(video)
        return True


    def publish_next(self, as_draft):
        while True:
            video = self.db.queue_next()
            if not video:
                return
            result = self.publish_one(video, as_draft)
            if result:
                return

    def _enqueue_videos(self, video_ids, category=None):
        from videosdb.models import Video
        api = YoutubeAPI(self.config)
        for yid in video_ids:
            info = YoutubeDL.download_info(yid)
            # some playlists include videos from other channels
            # for now exclude those videos
            # in the future maybe exclude whole playlist 
            if info["channel_id"] != self.config["youtube_channel"]["id"]:
                continue

            video, created = Video.objects.get_or_create(youtube_id=yid)
            video.parse_youtube_info(info)
            
            if category:
                category, created = Categories.objects.get_or_create(name=category)
                video.categories.add(category)

            if src_channel:
                video.src_channel = src_channel

            self.download_one(video)
            video.save()

    def _enqueue_channel(self, channel_id):
        api = YoutubeAPI(self.config)
        playlists = api.list_playlists(channel_id)
        for playlist in playlists:
            if playlist["channel_title"] != self.config["youtube_channel"]["name"]:
                continue
            if playlist["title"] == "Uploads from " + playlist["channel_title"] or \
                playlist["title"] == "Liked videos" or \
                playlist["title"] == "Popular uploads":
                continue

            playlist_url = "https://www.youtube.com/playlist?list=" + playlist["id"]
            videos = YoutubeDL.list_videos(playlist_url)
            video_ids = [video["id"] for video in videos]
            self._enqueue_videos(video_ids, playlist["title"])

        # enqueue all channel videos that are not in playlists:
        channel_url = "https://www.youtube.com/channel/" + channel_id
        videos = YoutubeDL.list_videos(channel_url)
        self._enqueue_videos(videos)

    def enqueue(self):
        channel_id = self.config["youtube_channel"]["id"]
        self._enqueue_channel(channel_id)

    def republish_all(self):
        for video in self.db.get_videos():
            if not video["published"]:
                continue
            self.publish_one(video) 


def _main():
    import argparse
    parser = argparse.ArgumentParser(description="Download videos from YouTube and publish them on IPFS and/or a Wordpress blog")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-t", "--trace", action="store_true")
    parser.add_argument("-e", "--enqueue", action="store_true")
    parser.add_argument("-n", "--publish-next", action="store_true")
    parser.add_argument("--publish-all", action="store_true")
    parser.add_argument("--republish-all", action="store_true")
    parser.add_argument("--download-one", metavar="VIDEO-ID")
    parser.add_argument("--download-all", action="store_true")
    parser.add_argument("--as-draft", action="store_true")
    parser.add_argument("--regen-ipfs-folder", action="store_true")

    args = parser.parse_args()


    main = Main()

    if args.regen_ipfs_folder:
        main.regen_ipfs_folder()

    if args.enqueue:
        main.enqueue()

    if args.republish_all:
        main.republish_all()

    if args.download_all:
        main.download_all()

    if args.publish_all:
        main.publish_all()

    if args.download_one:
        main.download_one(args.download_one)

    if args.publish_next:
        main.publish_next(args.as_draft)



if __name__ == "__main__":
    _main()
