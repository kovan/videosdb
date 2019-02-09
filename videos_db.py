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
        from ipfsapi.exceptions import StatusError
        file_hash = self.api.add(filename)["Hash"]
        self.api.pin_add(file_hash)

        if not add_to_dir:
            return file_hash

        src = "/ipfs/"+ file_hash
        dst =  "/videos/" + filename
        try:
            self.api.files_rm(dst)
        except StatusError:
            pass
        self.api.files_cp(src, dst)
        self.dnslink_update_pending = True

        return file_hash

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
    class CopyrightError(Exception):
        pass

    BASE_CMD =  "youtube-dl --ffmpeg-location /dev/null --youtube-skip-dash-manifest --ignore-errors "

    def download_video(self, _id):
        filename_format = "%(uploader)s - %(title)s [%(id)s].%(ext)s"
        execute(self.BASE_CMD + "--output '%s' %s" %( filename_format,"https://www.youtube.com/watch?v=" + _id))
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    def download_thumbnail(self, _id):
        execute(self.BASE_CMD + "--write-thumbnail --skip-download https://www.youtube.com/watch?v=" + _id)
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    def download_info(self, youtube_id):
        cmd = self.BASE_CMD + "--write-info-json --skip-download --output '%(id)s' https://www.youtube.com/watch?v=" + youtube_id
        try:
            result = execute(cmd, capture_stderr=True)
        except executor.ExternalCommandFailed as e:
            if "blocked it on copyright grounds" in str(e.command.stderr):
                raise YoutubeDL.CopyrightError()
            raise e

        video_json = json.load(open(youtube_id + ".info.json"))
        return video_json

    def list_videos(self, url):
        result = execute(self.BASE_CMD + "--flat-playlist --playlist-random -j " + url, check=False, capture=True, capture_stderr=True)
        videos = []
        for video_json in result.splitlines():
            video = json.loads(video_json)
            videos.append(video)
        return videos

    def _get_playlist_info(self, playlist_id):
        url = "https://www.googleapis.com/youtube/v3/playlists?part=snippet%2C+contentDetails"
        url += "&id=" + playlist_id
        url += "&key=" + config["youtube_key"]
        response = requests.get(url).json()
        playlist = {
            "id": playlist_id,
            "title": response["items"][0]["snippet"]["title"],
            "channel_title": response["items"][0]["snippet"]["channelTitle"],
            "item_count": response["items"][0]["contentDetails"]["itemCount"],
        }
        return playlist

    def list_playlists(self, channel_id):
        url = "https://www.googleapis.com/youtube/v3/channelSections?part=snippet%2CcontentDetails" 
        url += "&channelId=" + channel_id
        url += "&key=" + config["youtube_key"]
        response = requests.get(url).json()
        playlists_ids = []
        for item in response["items"]:
            details = item.get("contentDetails")
            if not details:
                continue
            playlists_ids += details["playlists"]

        playlist_ids = set(playlists_ids)
        playlists = []
        for _id in playlist_ids:
            playlist = self._get_playlist_info(_id)
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
        publication = self.db["publish_queue"].find_one(published=False, has_copyright=False, order_by=["-id"])
        return publication

    def queue_update(self, publication):
        self.db["publish_queue"].upsert(publication, ["youtube_id"], ensure=True)

    def is_video_in_queue(self, youtube_id):
        return self.db["publish_queue"].find_one(youtube_id=youtube_id) is not None

    def get_video_ids(self):
        return [video["youtube_id"] for video in self.db["videos"].all()]

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
            "has_copyright": False
        }
        

    def download_all(self):
        for _id in self.db.get_video_ids():
            self.download_one(_id, False)

        if self.ipfs:
            self.ipfs.update_dnslink()


    def download_one(self, youtube_id, update_dnslink=True):
        video = self.db.get_video(youtube_id)
        if not video:
            video = dict()
            video["youtube_id"] = youtube_id

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

        ydl = YoutubeDL()
        if download_info:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                info = ydl.download_info(youtube_id)

            for attr in interesting_attrs:
                video[attr] = info[attr]

            video["tags"] = ", ".join(video["tags"])

        if self.ipfs:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                if not video.get("ipfs_hash"):
                    video["filename"] = ydl.download_video(video["youtube_id"])
                    video["ipfs_hash"]= self.ipfs.add_file(video["filename"])
                if not video.get("ipfs_thumbnail_hash"):
                    thumbnail_filename = ydl.download_thumbnail(video["youtube_id"])
                    video["ipfs_thumbnail_hash"] = self.ipfs.add_file(thumbnail_filename, False)
            if update_dnslink:
                self.ipfs.update_dnslink()

        self.db.put_video(video)
        return video


    def publish_one(self, publication, as_draft):
        from datetime import datetime
        video = self.download_one(publication["youtube_id"])

        categories = publication["categories"].split(",")
        categories.append("Short videos" if video["duration"]/60 <= 20 else "Long videos")
        categories.append(video["uploader"])
            
        video_tags = set([tag.lower() for tag in video["tags"].split(',')])
        my_tags = set([
            "guru"
        ])
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
        return publication


    def publish_next(self, as_draft):
        publication = self.db.queue_next()
        if not publication:
            return None
        try:
            self.publish_one(publication, as_draft)
        except YoutubeDL.CopyrightError as e:
            publication["has_copyright"] = True
            self.db.queue_update(publication)
            self.publish_next(as_draft)


    def enqueue_one(self, channel_id):
        import random
        ydl = YoutubeDL()

        playlists = ydl.list_playlists(channel_id)
        for playlist in playlists:
            if playlist["channel_title"] in config["youtube_excluded_channels"]:
                continue
            if playlist["title"] == "Uploads from " + playlist["channel_title"]:
                continue

            playlist_url = "https://www.youtube.com/playlist?list=" + playlist["id"]
            videos = ydl.list_videos(playlist_url)
            random.shuffle(videos)

            for video in videos:
                yid = video["id"]
                if self.db.is_video_in_queue(yid):
                    continue
                pending_publication = Main._new_publication(yid) 
                pending_publication["categories"] = playlist["title"]
                self.db.queue_push(pending_publication)

    def enqueue(self):
        for channel_id in config["youtube_channels"]:
            self.enqueue_one(channel_id)



def _main():
    import argparse
    parser = argparse.ArgumentParser(description="Download videos from YouTube and publish them on IPFS and/or a Wordpress blog")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-t", "--trace", action="store_true")
    parser.add_argument("-e", "--enqueue", action="store_true")
    parser.add_argument("-n", "--publish-next", action="store_true")
    parser.add_argument("--enqueue-one", metavar="URL")
    parser.add_argument("--download-one", metavar="VIDEO-ID")
    parser.add_argument("--download-all", action="store_true")
    parser.add_argument("--only-update-dnslink", action="store_true")
    parser.add_argument("--as-draft", action="store_true")

    args = parser.parse_args()

    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s')
    handler = logging.handlers.RotatingFileHandler("log", 'a', 100000, 10)
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

    if args.enqueue:
        main.enqueue()

    if args.enqueue_one:
        main.enqueue_one(args.enqueue_one)

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
