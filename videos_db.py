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
    import ipdb
    os.chdir("/tmp")
    ipdb.set_trace()

@traced(logging.getLogger(__name__))
class Wordpress:
    def __init__(self):
        from wordpress_xmlrpc import Client
        self.client = Client(
            config["www_root"] + "/xmlrpc.php",
            config["wp_username"],
            config["wp_pass"])

    def upload_image(self, filename, title, youtube_id):
        from wordpress_xmlrpc.compat import xmlrpc_client
        from wordpress_xmlrpc.methods import media, posts

        data = {
            "name": title + ".jpg",
            'type': 'image/jpeg'
        }

        with open(filename, 'rb') as img:
            data['bits'] = xmlrpc_client.Binary(img.read())

        response = self.client.call(media.UploadFile(data))
        return response



    def publish(self, video, categories, tags, thumbnail, as_draft=False):
        from wordpress_xmlrpc import WordPressPost
        from wordpress_xmlrpc.methods.posts import NewPost
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
            dnslink_name=config["dnslink_name"],
            www_root=config["www_root"],
            filename_quoted=quote(video.get("filename")),
            thumbnail_url=thumbnail["link"]
        )

        post = WordPressPost()
        post.title = video["title"]
        post.content = html
        post.thumbnail = thumbnail["id"]
        post.meta = {
            "youtube_id": video["youtube_id"]
        }
        post.terms_names = {
            "post_tag" : tags,
            "category": categories
        }
        if not as_draft:
            post.post_status = "publish"

        # returns new post's ID
        return self.client.call(NewPost(post))


@traced(logging.getLogger(__name__))
class DNS:
    @staticmethod
    def update(new_root_hash):
        from google.cloud import dns
        client = dns.Client()
        zone = client.zone(config["dns_zone"])
        records = zone.list_resource_record_sets()

        # init transaction
        changes = zone.changes()
        # delete old
        for record in records:
            if record.name == config["dnslink_name"] + "."  and record.record_type == "TXT":
                changes.delete_record_set(record)
        #add new
        record = zone.resource_record_set(config["dnslink_name"] + ".","TXT", 300, ["dnslink=/ipfs/"+ new_root_hash,])
        changes.add_record_set(record)
        #finish transaction
        changes.create()


@traced(logging.getLogger(__name__))
class IPFS:
    def __init__(self):
        import ipfsapi
        self.host = config["ipfs_host"]
        self.port = config["ipfs_port"]
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
        DNS.update(root_hash)
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
            result = execute(cmd, capture_stderr=True)
        except executor.ExternalCommandFailed as e:
            if "copyright" in str(e.command.stderr) or \
               "Unable to extract video title" in str(e.command.stderr) or \
               "available in your country" in str(e.command.stderr):
                raise YoutubeDL.UnavailableError()
            raise e

        video_json = json.load(open(youtube_id + ".info.json"))
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

    @staticmethod
    def _make_request(base_url, page_token=""):
        url = base_url
        url += "&key=" + config["youtube_key"]
        if page_token:
            url += "&pageToken=" + page_token

        response = requests.get(url).json()
        items = response["items"]
        if "nextPageToken" in response:
            items += YoutubeAPI._make_request(base_url, response["nextPageToken"])
        return items

    @staticmethod
    def _get_playlist_info(playlist_id):
        url = "https://www.googleapis.com/youtube/v3/playlists?part=snippet%2C+contentDetails"
        url += "&id=" + playlist_id
        items = YoutubeAPI._make_request(url)
        playlist = {
            "id": playlist_id,
            "title": items[0]["snippet"]["title"],
            "channel_title": items[0]["snippet"]["channelTitle"],
            "item_count": items[0]["contentDetails"]["itemCount"],
        } 
        return playlist

        
    @staticmethod
    def _get_channnelsection_playlists(channel_id):
        url = "https://www.googleapis.com/youtube/v3/channelSections?part=snippet%2CcontentDetails" 
        url += "&channelId=" + channel_id
        items = YoutubeAPI._make_request(url)
        playlist_ids = []
        for item in items:
            details = item.get("contentDetails")
            if not details:
                continue
            playlist_ids += details["playlists"]
        return playlist_ids

    @staticmethod
    def _get_channel_playlists(channel_id):
        url = "https://www.googleapis.com/youtube/v3/playlists?part=snippet%2C+contentDetails"
        url += "&channelId=" + channel_id
        items = YoutubeAPI._make_request(url)
        playlist_ids = []
        for item in items:
            playlist_ids.append(item["id"])
        return playlist_ids

    @staticmethod
    def list_playlists(channel_id):
        ids_channelsection = YoutubeAPI._get_channnelsection_playlists(channel_id) 
        ids_channel =  YoutubeAPI._get_channel_playlists(channel_id) 

        playlist_ids = set(ids_channelsection + ids_channel)
        playlists = []
        for _id in playlist_ids:
            playlist = YoutubeAPI._get_playlist_info(_id)
            playlists.append(playlist)

        return playlists



@traced(logging.getLogger(__name__))
class DB:
    def __init__(self):
        import dataset
        self.db = dataset.connect("sqlite:///db.db")

    def queue_push(self, publication):
        self.db["publish_queue"].insert(publication)

    def queue_next(self):
        # treat table as a LIFO stack, so that recent videos get published first:
        publication = self.db["publish_queue"].find_one(published=False, excluded=False, order_by=["-id"])
        return publication

    def queue_update(self, publication):
        self.db["publish_queue"].upsert(publication, ["youtube_id"], ensure=True)

    def is_video_in_queue(self, youtube_id):
        return self.db["publish_queue"].find_one(youtube_id=youtube_id) is not None

    def get_publications(self):
        return self.db["publish_queue"].all()

    def get_videos(self):
        return self.db["videos"].all()

    def get_video(self, youtube_id):
        return self.db["videos"].find_one(youtube_id=youtube_id)

    def put_video(self, video):
        self.db["videos"].upsert(video,["youtube_id"], ensure=True)



@traced(logging.getLogger(__name__))
class Main:
    def __init__(self, enable_ipfs=True):
        self.db = DB()
        if enable_ipfs:
            self.ipfs = IPFS()
        else:
            self.ipfs = None

    @staticmethod
    def _new_publication(yid):
        return  {
            "youtube_id": yid,
            "published": False,
            "excluded": False
        }
        
    def regen_ipfs_folder(self):
        self.ipfs.api.files_mkdir("/videos")
        for video in self.db.get_videos():
            self.ipfs.add_to_dir(video["filename"], video["ipfs_hash"])
        #self.ipfs.update_dnslink()
            

    def download_all(self):
        ids1 = [video["youtube_id"] for video in self.db.get_videos()]
        ids2 = [video["youtube_id"] for video in self.db.get_publications()]
        ids = set(ids1 + ids2)
        for _id in ids: 
            self.download_one(_id, False)

        if self.ipfs:
            self.ipfs.update_dnslink()

    def _fill_info(self, video):
        
        interesting_attrs = ["title",
                "description",
                "uploader",
                "upload_date",
                "duration",
                "channel_url",
                "tags"]

        download_info = False
        for attr in interesting_attrs:
            if not video.get(attr):
                download_info = True
                break

        if not download_info:
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            info = YoutubeDL.download_info(video["youtube_id"])

        for attr in interesting_attrs:
            video[attr] = info[attr]

        video["tags"] = ", ".join(video["tags"])


    def download_one(self, youtube_id, update_dnslink=True):
        video = self.db.get_video(youtube_id)
        if not video:
            video = dict()
            video["youtube_id"] = youtube_id

        try:
            self._fill_info(video)
            if video["uploader"] != config["youtube_channel"]["name"]:
                return None

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


    def publish_one(self, publication, as_draft):
        from datetime import datetime

        video = self.download_one(publication["youtube_id"])
        if not video:
            publication["excluded"] = True
            return False

        categories = publication["categories"].split(",")
        categories.append("Short videos" if video["duration"]/60 <= 20 else "Long videos")
        categories.append(video["uploader"])
            
        video_tags = set([tag.lower() for tag in video["tags"].split(',')])
        my_tags = set([])
        final_tags = list(video_tags.union(my_tags))

        wp = Wordpress()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            thumbnail_filename = self.ipfs.get_file(video["ipfs_thumbnail_hash"])
            thumbnail = wp.upload_image(thumbnail_filename, video["title"], youtube_id)

        post_id = wp.publish(video, categories, final_tags, thumbnail, as_draft)

        publication["published"] = True
        publication["post_id"] = post_id
        publication["publish_date"] = datetime.now()
        publication["tags"] = ",".join(final_tags)
        publication["categories"] = ",".join(categories)
        self.db.queue_update(publication)
        return True


    def publish_next(self, as_draft):
        publication = self.db.queue_next()
        if not publication:
            return None
        result = self.publish_one(publication, as_draft)
        if not result:
            self.publish_next(as_draft)

    def _enqueue_videos(self, videos, src_channel="", category=""):
        import random
        random.shuffle(videos)

        for video in videos:
            yid = video["id"]
            if self.db.is_video_in_queue(yid):
                continue
            pending_publication = Main._new_publication(yid) 
            if category:
                pending_publication["categories"] = category
            if src_channel:
                pending_publication["src_channel"] = src_channel
            self.db.queue_push(pending_publication)

    def _enqueue_channel(self, channel_id):

        playlists = YoutubeAPI.list_playlists(channel_id)
        for playlist in playlists:
            if playlist["channel_title"] != config["youtube_channel"]["name"]:
                continue
            if playlist["title"] == "Uploads from " + playlist["channel_title"] or \
                playlist["title"] == "Liked videos" or \
                playlist["title"] == "Popular uploads":
                continue
            playlist_url = "https://www.youtube.com/playlist?list=" + playlist["id"]
            videos = YoutubeDL.list_videos(playlist_url)
            self._enqueue_videos(videos, playlist["channel_title"], playlist["title"])

        # enqueue all channel videos that are not in playlists:
        channel_url = "https://www.youtube.com/channel/" + channel_id
        videos = YoutubeDL.list_videos(channel_url)
        self._enqueue_videos(videos)

    def enqueue(self):
        channel_id = config["youtube_channel"]["id"]
        self._enqueue_channel(channel_id)



def _main():
    import argparse
    parser = argparse.ArgumentParser(description="Download videos from YouTube and publish them on IPFS and/or a Wordpress blog")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-t", "--trace", action="store_true")
    parser.add_argument("-e", "--enqueue", action="store_true")
    parser.add_argument("-n", "--publish-next", action="store_true")
    parser.add_argument("--download-one", metavar="VIDEO-ID")
    parser.add_argument("--download-all", action="store_true")
    parser.add_argument("--only-update-dnslink", action="store_true")
    parser.add_argument("--as-draft", action="store_true")
    parser.add_argument("--regen-ipfs-folder", action="store_true")

    args = parser.parse_args()

    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s')
    handler = logging.handlers.RotatingFileHandler("log", 'a', 1000000, 10)
    handler2 = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler2.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(handler2)


    if args.verbose:
        logging.getLogger("executor").setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)

    if args.trace:
        logger.setLevel(TRACE)

    if args.only_update_dnslink:
        ipfs = IPFS()
        ipfs.update_dnslink(True)
        return

    main = Main()

    if args.regen_ipfs_folder:
        main.regen_ipfs_folder()

    if args.enqueue:
        main.enqueue()

    if args.download_all:
        main.download_all()

    if args.download_one:
        main.download_one(args.download_one)

    if args.publish_next:
        main.publish_next(args.as_draft)



if __name__ == "__main__":
    import yaml
    with io.open("config.yaml") as f:
        config = yaml.load(f)
    _main()
