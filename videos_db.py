#!env python3
from executor import execute
from autologging import traced, TRACE
import tempfile
import logging
import json
import sys
import os
import io

import config

def dbg():
        import ipdb; ipdb.set_trace()

@traced(logging.getLogger(__name__))
def _publish_blogger(video):
    import blogger
    import jinja2
    template_raw = '''
    <br />
    <div style="padding-bottom: 56.25%; position: relative;">
    <iframe allow="encrypted-media" allowfullscreen="" frameborder="0" gesture="media" src="https://www.youtube.com/embed/{{ youtube_id }}" style="height: 100%; left: 0; position: absolute; top: 0; width: 100%;">
    </iframe>
    </div>
    <ul>
    {% for file in files %}
        <li>Download from IPFS: <a href="https://cloudfare-ipfs.com/ipfs/{{ ipfs_hash }}" download="{{ filename }}">{{ title }}</a></li>
    {% endfor %}
    </ul>
    </div>
    '''
    template = jinja2.Template(template_raw)
    html = template.render(
        youtube_id=video["youtube_id"],
        title=video["title"]
    )
    eb = blogger.EasyBlogger(
        clientId=config.blogger_token, 
        clientSecret = config.blogger_secret,
        blogId = config.blogger_blogid)
    labels = "video, " + video["uploader"]
    eb.post(video["title"], html, labels, isDraft=False)

@traced(logging.getLogger(__name__))
def _publish_wordpress(video):
    import requests
    from string import Template
    from urllib.parse import urlencode
    template_raw = '''
        <!-- wp:core-embed/youtube {"url":"https://www.youtube.com/watch?v=$youtube_id","type":"video","providerNameSlug":"youtube","className":"wp-embed-aspect-16-9 wp-has-aspect-ratio"} -->
        <figure class="wp-block-embed-youtube wp-block-embed is-type-video is-provider-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio"><div class="wp-block-embed__wrapper">
        https://www.youtube.com/watch?v=$youtube_id
        </div></figure>
        <!-- /wp:core-embed/youtube -->
        '''

    template_raw_ipfs = '''
        <!-- wp:button {"align":"center"} -->
        <div class="wp-block-button aligncenter"><a class="wp-block-button__link" href="http://ipfs.spiritualityresources.net/ipfs/$ipfs_hash?$filename_param"
            download="$filename">Play/download video</a></div>
        <!-- /wp:button -->
        '''
#        '''
#        <!-- wp:paragraph {"align":"center","customFontSize":11} -->
#        <p style="font-size:11px;text-align:center">If your browser automatically plays the video instead of downloading it, right click on the link and choose "Save as..."</p>
#        <!-- /wp:paragraph -->
#        '''
    
    if video.get("ipfs_hash"):
        template_raw += template_raw_ipfs

    template = Template(template_raw)
    html = template.substitute(
        youtube_id=video["youtube_id"],
        ipfs_hash=video.get("ipfs_hash"),
        filename_param=urlencode({ "filename" : video.get("filename") }),
        filename=video.get("filename")
    )
    site_id = config.wordpress_site_id
    url = 'https://public-api.wordpress.com/rest/v1/sites/' + site_id + '/posts/new'
    headers = { "Authorization": "BEARER " + config.wordpress_token}
    categories = [
        "Videos",
        "Short videos" if video["duration"]/60 <= 20 else "Long videos",
        video["uploader"]
    ]
    data = {
        "title" : video["title"],
        "categories": ",".join(categories),
        "content": html
    }
    response = requests.post(url,headers=headers,data=data)
    response.raise_for_status()

        

@traced(logging.getLogger(__name__))
class DNS:
    @staticmethod
    def update(new_root_hash):
        from google.cloud import dns
        client = dns.Client(project=config.gcloud_project)
        zone = client.zone(config.dns_zone)
        records = zone.list_resource_record_sets()
        
        # init transaction
        changes = zone.changes()
        # delete old
        for record in records:
            if record.name == config.dnslink_name:
                changes.delete_record_set(record)
        #add new 
        record = zone.resource_record_set(config.dnslink_name,"TXT", 300, ["dnslink=/ipfs/"+ new_root_hash,])
        changes.add_record_set(record)
        #finish transaction
        changes.create()

        
@traced(logging.getLogger(__name__))
class IPFS:
    def __init__(self):
        self.host = config.ipfs_host
        self.port = config.ipfs_port
        self.root_dir = "/videos"
        import ipfsapi
        self.api = ipfsapi.connect(self.host, self.port)

    def add_file(self, filename):
        file_hash = self.api.add(filename)["Hash"]
        self.api.pin_add(file_hash)
        src = "/ipfs/"+ video["ipfs_hash"]
        dst =  self.ipfs.root_dir + "/" + video["filename"]
        result = self.ipfs.api.files_mv(src, dst)
        return file_hash
        
    def update_dnslink(self):
        root_hash = self.api.files_stat(self.root_dir)["Hash"]
        DNS.update(root_hash)  


@traced(logging.getLogger(__name__))
class YoutubeDL:
    BASE_CMD =  "youtube-dl --youtube-skip-dash-manifest --ignore-errors "

    @staticmethod
    def download_video(id):
        filename_format = "%(uploader)s - %(title)s [%(id)s].%(ext)s"
        execute(YoutubeDL.BASE_CMD + "--output '%s' %s" %( filename_format,"https://www.youtube.com/watch?v=" + id))
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
        result = execute(YoutubeDL.BASE_CMD + "--playlist-random --get-id " + url, check=False, capture=True)
        if not result:
            raise Exception("youtube-dl error")
        ids = result.splitlines()
        return ids
    
@traced(logging.getLogger(__name__))
class DB:
    def __init__(self):
        import dataset
        self.db = dataset.connect("sqlite:///db.db")
        
    def queue_push(self, youtube_id):
        self.db["publish_queue"].insert({"youtube_id":youtube_id})
    
    def queue_pop_video_id(self):
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

    def get_queue(self):
        return [row["youtube_id"] for row in self.db["publish_queue"].all()]

    def get_video(self, youtube_id):
        return self.db["videos"].find_one(youtube_id=youtube_id)

    def put_video(self, video):
        self.db["videos"].upsert(video,["youtube_id"], ensure=True)


@traced(logging.getLogger(__name__))
class Main:
    def __init__(self):
        self.db = DB()
        if config.ipfs_host and config.ipfs_port:
            self.ipfs = IPFS(config.ipfs_host, config.ipfs_port)
        else:
            self.ipfs = None

    def download_all(self):
        for _id in self.db.get_queue():
            self.download_one(_id, False)
    
        if self.ipfs:
            self.ipfs.update_dnslink()


    def download_one(self, youtube_id, update_dnslink=True):
        video = self.db.get_video(youtube_id)
        if not video:
            video = dict()
            video["youtube_id"] = youtube_id
            info = YoutubeDL.download_info(youtube_id)
            interesting_attrs = ["title",
                    "description",
                    "uploader",
                    "upload_date",
                    "duration",
                    "channel_url"]
            for attr in interesting_attrs:
                video[attr] = info[attr]


        if self.ipfs and not video.get("ipfs_hash"):
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                video["filename"] = YoutubeDL.download_video(video["youtube_id"])
                video["ipfs_hash"]= self.ipfs.add_file(video["filename"])
               
        self.db.put_video(video)

        if self.ipfs and update_dnslink:
            self.ipfs.update_dnslink()

        return video


    def publish_one(self, youtube_id):
        video = self.download_one(youtube_id)
        _publish_wordpress(video)


    def publish_next(self):
        next_video_id = self.db.queue_pop()
        if not next_video_id:
            return
        self.publish_one(next_video_id)


    def enqueue(self, url):
        import random

        video_ids = YoutubeDL.list_videos(url)
        random.shuffle(video_ids)

        for youtube_id in video_ids:
            if not self.db.is_video_in_queue(youtube_id):
                self.db.queue_push(youtube_id)

def _main():
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("--verbose", action="store_true")
    parser.add_option("--enqueue", metavar="URL")
    parser.add_option("--download-all", action="store_true")
    parser.add_option("--publish-next", action="store_true")
    parser.add_option("--publish-one",metavar="VIDEO-ID") 
    parser.add_option("--ipfs-enable", action="store_true")
    parser.add_option("--only-update-dnslink", action="store_true")

    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(
                 stream=sys.stdout,
                 format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")
        logging.getLogger(__name__).setLevel(TRACE)
        logging.getLogger("executor").setLevel(logging.DEBUG)

    if options.only_update_dnslink:
        ipfs = IPFS()
        ipfs.update_dnslink()
        return

    main = Main()

    if options.enqueue:
        main.enqueue(options.enqueue)
        return

    if options.download_all:
        main.download_all()
        return

    if options.publish_one:
        main.publish_one(options.publish_one)
        return

    if options.publish_next:
        main.publish_next()
        return

        


if __name__ == "__main__":
    _main()
