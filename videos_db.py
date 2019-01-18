#!env python3
from executor import execute
from autologging import traced, TRACE
import tempfile
import dataset
import requests
import logging
import json
import sys
import os
import io

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
        clientId="62814020656-olqaifiob7ufoqpe1k4iah3v2ra12h8a.apps.googleusercontent.com", 
        clientSecret = "fnUgEpdkUTtthUtDk0vLvjMm",
        blogId = "8804984470189945822")
    labels = "video, " + video["uploader"]
    eb.post(video["title"], html, labels, isDraft=False)

@traced(logging.getLogger(__name__))
def _publish_wordpress(video):
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
        <div class="wp-block-button aligncenter"><a class="wp-block-button__link" href="http://ipfs.spiritualityresources.net/ipfs/$ipfs_hash?$filename_param">Download video</a></div>
        <!-- /wp:button -->

        '''

    if video.get("ipfs_hash"):
        template_raw += template_raw_ipfs

    template = Template(template_raw)
    html = template.substitute(
        youtube_id=video["youtube_id"],
        ipfs_hash=video.get("ipfs_hash"),
        filename_param=urlencode({ "filename" : video.get("filename")} )
    )
    site_id = "156901386"
    url = 'https://public-api.wordpress.com/rest/v1/sites/' + site_id + '/posts/new'
    headers = { "Authorization": "BEARER " + "qpTIK7(hogZ#3WhSK#N@39xSQHc5aD@7D5VkxnXWBGgXsQwt90E#vw3!3yJA&Kc)" }
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
    def update(self, new_root_hash):
        from google.cloud import dns
        client = dns.Client()
        zone = client.zone("spirituality")
        #records, page_token = zone.list_resource_record_sets()
        records = zone.list_resource_record_sets()
        
        # init transaction
        changes = zone.changes()
        # delete old
        for record in records:
            if record.name == "list.spiritualityresources.net.":
                changes.delete_record_set(record)
        #add new 
        record = zone.resource_record_set("list.spiritualityresources.net.","TXT", 300, ["dnslink=/ipfs/"+ new_root_hash,])
        changes.add_record_set(record)
        #finish transaction
        changes.create()

        
@traced(logging.getLogger(__name__))
class IPFS:
    def __init__(self, address):
        self.host, self.port = address.split(":")
        self.root_hash_filename = "ipfs_root_hash.txt"
        if os.path.exists(self.root_hash_filename):
            self.root_hash = open(self.root_hash_filename).read().strip() 
        else:
            self.root_hash = ""

    def _update_root_hash(self, new_root_hash):
        self.root_hash = new_root_hash
        with io.open(self.root_hash_filename, "w") as f:
            f.write(new_root_hash)
        DNS().update(new_root_hash) 

    def add_file(self, filename):
        import ipfsapi
        api = ipfsapi.connect(self.host, self.port)
        hash = api.add(filename)["Hash"]
        api.pin_add(hash)
        if self.root_hash:
            result = api.object_patch_add_link(self.root_hash, filename, hash)
            self._update_root_hash(result["Hash"])        
        return hash
        
        

@traced(logging.getLogger(__name__))
class YoutubeDL:
    BASE_CMD =  "youtube-dl --youtube-skip-dash-manifest --ignore-errors "

    @staticmethod
    def download_video(url_or_id):
        filename_format = "%(uploader)s - %(title)s [%(id)s].%(ext)s"
        execute(YoutubeDL.BASE_CMD + "--output '%s' %s" %( filename_format,url_or_id))
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    @staticmethod
    def download_info(youtube_id):
        with tempfile.TemporaryDirectory() as tmpdir: 
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            cmd = YoutubeDL.BASE_CMD + "--write-info-json --skip-download --output '%(id)s' " + youtube_id
            execute(cmd)
            video_json = json.load(open(youtube_id + ".info.json"))
            os.chdir(old_cwd)
        return video_json 

    @staticmethod
    def download_many(id_list, max_procs = 1):
       from multiprocessing import Pool
       with Pool(max_procs) as pool:
           return pool.map(YoutubeDL.download_video,id_list)
             

    @staticmethod
    def list_videos(self, url):
        result = execute(YoutubeDL.BASE_CMD + "--playlist-random --get-id " + url, check=False, capture=True)
        if not result:
            raise Exception("youtube-dl error")
        ids = result.splitlines()
        return ids
    

@traced(logging.getLogger(__name__))
class Main:
    def __init__(self, ipfs_address=None):
        self.db = dataset.connect("sqlite:///db.db")
        self.ipfs_address = ipfs_address
    

    def download_all(self):
        ids = [row["youtube_id"] for row in self.db["publish_queue"].all()]
        YoutubeDL.download_many(ids, max_procs=10)
        

    def download_one(self, youtube_id):
        video = self.db["videos"].find_one(youtube_id=youtube_id)
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

        if self.ipfs_address and "ipfs_hash" not in video:
            ipfs = IPFS(self.ipfs_address)
            with tempfile.TemporaryDirectory() as tmpdir:
                old_cwd = os.getcwd()
                os.chdir(tmpdir)
                video["filename"] = YoutubeDL.download_video(video["youtube_id"])
                video["ipfs_hash"]= ipfs.add_file(video["filename"])
                os.chdir(old_cwd)
               
        self.db["videos"].upsert(video,["youtube_id"], ensure=True)
        return video


    def publish_one(self, youtube_id):
        video = self.download_one(youtube_id)
        _publish_wordpress(video)


    def publish_next(self):
        # treat table as a LIFO stack, so that recent videos get published first:
        row = self.db["publish_queue"].find_one(order_by=["-id"]) 
        if not row:
            #we ran out of videos, reenqueue all:
            for video in self.db["videos"].all():
                self.db["publish_queue"].insert({"youtube_id": video["youtube_id"]})
            return

        self.publish_one(row["youtube_id"])
        self.db["publish_queue"].delete(**row)


    def enqueue(self, url):
        import random

        video_ids = YoutubeDL.list_videos(url)
        random.shuffle(video_ids)

        for id in video_ids:
            self.db["publish_queue"].upsert({"youtube_id":id}, ["youtube_id"] )

def _main():
    import dataset
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("--verbose", action="store_true")
    parser.add_option("--enqueue", metavar="URL")
    parser.add_option("--download-all", action="store_true")
    parser.add_option("--publish-next", action="store_true")
    parser.add_option("--publish-one",metavar="VIDEO-ID") 
    parser.add_option("--ipfs-address", metavar="HOST:PORT")
    parser.add_option("--only-update-dnslink", metavar="ROOT_HASH")

    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(
                 stream=sys.stdout,
                 format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")
        logging.getLogger(__name__).setLevel(TRACE)
        logging.getLogger("executor").setLevel(logging.DEBUG)

    if options.only_update_dnslink:
        DNS().update(options.only_update_dnslink)
        return

    main = Main(options.ipfs_address)

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
