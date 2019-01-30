#!env python3
from executor import execute
from autologging import traced, TRACE
import tempfile
import logging
import json
import sys
import os
import io


def dbg():
    import ipdb; ipdb.set_trace()


@traced(logging.getLogger(__name__))
def _publish_wordpress(video, categories, tags, as_draft=False):
    import requests
    from string import Template
    from urllib.parse import quote
    template_raw = \
'''
   <!-- wp:video {"align":"center"} -->
<figure class="wp-block-video aligncenter"><video controls poster="https://$ipfs_gateway/ipfs/$thumbnail_hash" src="https://$dnslink_name/videos/$filename_quoted"></video></figure>
<!-- /wp:video -->

<!-- wp:paragraph {"align":"center"} -->
<p style="text-align:center">Download/play from: <a href="https://$dnslink_name/videos/$filename_quoted">HTTP</a> | <a href="ipns://$dnslink_name/videos/$filename_quoted">IPFS</a> | <a href="https://www.youtube.com/watch?v=$youtube_id">YouTube</a></p>
<!-- /wp:paragraph --> 
'''
    
    template = Template(template_raw)
    html = template.substitute(
        youtube_id=video["youtube_id"],
        dnslink_name=config["dnslink_name"],
        www_root=config["www_root"],
        filename_quoted=quote(video.get("filename")),
        ipfs_gateway=config["ipfs_gateway"],
        thumbnail_hash=video["ipfs_thumbnail_hash"]
    )

    url = 'https://public-api.wordpress.com/rest/v1/sites/%s/posts/new' % config["wordpress_site_id"]
    headers = { "Authorization": "BEARER " + config["wordpress_token"] }
    data = {
        "title" : video["title"],
        "categories": ",".join(categories),
        "tags": ",".join(tags),
        "content": html
    }
    if as_draft:
        data["status"] = "draft"

    response = requests.post(url,headers=headers,data=data)
    response.raise_for_status()
    return response.json()

        

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
        
    def update_dnslink(self, force=False):
        if not self.dnslink_update_pending and not force:
            return

        root_hash = self.api.files_stat("/")["Hash"]
        DNS.update(root_hash)  
        self.dnslink_update_pending = False


@traced(logging.getLogger(__name__))
class YoutubeDL:
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
        with tempfile.TemporaryDirectory() as tmpdir: 
            os.chdir(tmpdir)
            cmd = YoutubeDL.BASE_CMD + "--write-info-json --skip-download --output '%(id)s' https://www.youtube.com/watch?v=" + youtube_id
            execute(cmd)
            video_json = json.load(open(youtube_id + ".info.json"))
        return video_json 


    @staticmethod
    def list_videos(url):
        result = execute(YoutubeDL.BASE_CMD + "--playlist-random --get-id " + url, check=False, capture=True, capture_stderr=True)
        if not result:
            raise Exception("youtube-dl error. " + result.stderr)
        ids = result.splitlines()
        return ids
    
@traced(logging.getLogger(__name__))
class DB:
    def __init__(self):
        import dataset
        self.db = dataset.connect("sqlite:///db.db")
        
    def queue_push(self, youtube_id):
        self.db["publish_queue"].insert({"youtube_id":youtube_id})
    
    def queue_pop(self):
        # treat table as a LIFO stack, so that recent videos get published first:
        row = self.db["publish_queue"].find_one(order_by=["-id"]) 
        if not row:
            #we ran out of videos, reenqueue all:
            for video in self.db["videos"].all():
                self.db["publish_queue"].insert({"youtube_id": video["youtube_id"]})
            row = self.db["publish_queue"].find_one(order_by=["-id"]) 
        
        if not row:
            return None

        self.db["publish_queue"].delete(**row)
        return row["youtube_id"]

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

        if download_info:
            info = YoutubeDL.download_info(youtube_id)

            for attr in interesting_attrs:
                video[attr] = info[attr]
                
            video["tags"] = ", ".join(video["tags"]) 

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

        self.db.put_video(video)

        return video


    def publish_one(self, youtube_id, as_draft):
        from datetime import datetime
        video = self.download_one(youtube_id)
        categories = set([
            "Short videos" if video["duration"]/60 <= 20 else "Long videos",
            "Englightenment",
            "Guru",
            "Shiva video",
            "Yoga video",
            video["uploader"]
        ])
        video_tags = set([tag.lower() for tag in video["tags"].split(',')])
        my_tags = set([
            "yoga",
            "yoga video",
            "enlightenment",
            "guru",
            "shiva",
            "shiva video"
        ])
        final_tags = video_tags.union(my_tags)

        result = _publish_wordpress(video, categories, final_tags, as_draft)
        video["publish_response"] =  json.dumps(result)
        video["publish_date"] = datetime.now()
        self.db.put_video(video)


    def publish_next(self, as_draft):
        next_video_id = self.db.queue_pop()
        self.publish_one(next_video_id, as_draft)


    def enqueue(self, url):
        import random

        video_ids = YoutubeDL.list_videos(url)
        random.shuffle(video_ids)

        for yid in video_ids:
            if self.db.get_video(yid) or self.db.is_video_in_queue(yid):
                continue
            self.db.queue_push(yid)

def _main():
    import argparse
    parser = argparse.ArgumentParser(description="Download videos from YouTube and publish them on IPFS and/or a Wordpress blog")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-e", "--enqueue", metavar="URL")
    parser.add_argument("-p", "--publish-one", metavar="VIDEO-ID") 
    parser.add_argument("-n", "--publish-next", action="store_true")
    parser.add_argument("-d", "--download-one", metavar="VIDEO-ID")
    parser.add_argument("-a", "--download-all", action="store_true")
    parser.add_argument("-i", "--enable-ipfs", action="store_true")
    parser.add_argument("-u", "--only-update-dnslink", action="store_true")
    parser.add_argument("--as-draft", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(
                 stream=sys.stdout,
                 format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")
        logging.getLogger(__name__).setLevel(TRACE)
        logging.getLogger("executor").setLevel(logging.DEBUG)



    if args.only_update_dnslink:
        ipfs = IPFS()
        ipfs.update_dnslink(true)
        return

    main = Main(args.enable_ipfs)

    if args.enqueue:
        main.enqueue(args.enqueue)

    if args.download_all:
        main.download_all()

    if args.download_one:
        main.download_one(args.download_one)

    if args.publish_one:
        main.publish_one(args.publish_one, args.as_draft)

    if args.publish_next:
        main.publish_next(args.as_draft)



if __name__ == "__main__":
    import yaml
    with io.open("config.yaml") as f:
        config = yaml.load(f)
    _main()
