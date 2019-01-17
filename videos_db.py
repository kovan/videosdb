#!env python3
from executor import execute
from autologging import traced, TRACE
import tempfile
import requests
import logging
import json
import sys
import os
import io


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
    import jinja2

    template_raw = '''[embed]https://www.youtube.com/watch?v={{ youtube_id }}[/embed] '''
    if "ipfs_hash" in video:
        template_raw += \
        '''
        <!-- wp:button -->
        <div class="wp-block-button"><a class="wp-block-button__link" href="http://ipfs.spiritualityresources.net/ipfs/{{ ipfs_hash }}?filename={{file|urlencode}}">Download video<br></a></div>
        <!-- /wp:button -->
        '''
    template = jinja2.Template(template_raw)
    html = template.render(
        youtube_id=video["youtube_id"],
        ipfs_hash=video.get("ipfs_hash"),
        file=video.get("filename")
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
        import ipdb; ipdb.set_trace()
        
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
        from pathlib import Path
        var_dir = str(Path.home()) + "/.videos_db"
        if not os.path.exists(var_dir):
            os.mkdir(var_dir)
        self.root_hash_filename = var_dir + "/ipfs_root_hash.txt"
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
        
        
    def add_video_http(self, video_filename):
        # IPFS add:
        url = self.host + "/api/v0/add"
        files = { "files": open(video_filename, "rb") }
        response = requests.post(url, files=files)
        response.raise_for_status()
        hash = response.json()["Hash"]

        # IPFS pin:
        params = { "arg" : "/ipfs/" + hash }
        requests.get(self.host + "/api/v0/pin/add", params=params)
        response.raise_for_status()

        # IPFS add to directory:
        params = { 
            "root" : self.root_hash,
            "ref" : hash,
            "name" : video_filename
        }
        #response = requests.get(self.host + "/api/v0/object/patch/add-link", params=params)
        #response.raise_for_status()
        return hash


@traced(logging.getLogger(__name__))
class YoutubeDL:
    def __init__(self):
        self.base_cmd =  "youtube-dl --youtube-skip-dash-manifest --ignore-errors "

    def download_video(self,url_or_id):
        filename_format = "%(uploader)s - %(title)s (%(height)sp) [%(id)s].%(ext)s"
        execute(self.base_cmd + "--output '%s' %s" %( filename_format,url_or_id))
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    def download_info(self, youtube_id):
        with tempfile.TemporaryDirectory() as tmpdir: 
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            cmd = self.base_cmd + "--write-info-json --skip-download --output '%(id)s' " + youtube_id
            execute(cmd)
            video_json = json.load(open(youtube_id + ".info.json"))
            os.chdir(old_cwd)
        return video_json 

    def list_videos(self, url):
        result = execute(self.base_cmd + "--playlist-random --get-id " + url, check=False, capture=True)
        if not result:
            raise Exception("youtube-dl error")
        ids = result.splitlines()
        return ids
    



@traced(logging.getLogger(__name__))
def publish_one(db, youtube_id, ipfs_address):
    ydl = YoutubeDL()
    info = ydl.download_info(youtube_id)
    video = dict()
    video["youtube_id"] = youtube_id
    interesting_attrs = ["title",
            "description",
            "uploader",
            "upload_date",
            "duration",
            "channel_url"]
    for attr in interesting_attrs:
        video[attr] = info[attr]


    if ipfs_address and "ipfs_hash" not in video:
        ipfs = IPFS(ipfs_address)
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            video["filename"] = ydl.download_video(video["youtube_id"])
            video["ipfs_hash"]= ipfs.add_file(video["filename"])
            os.chdir(old_cwd)
           
    _publish_wordpress(video)
    db["videos"].upsert(video,["youtube_id"], ensure=True)



@traced(logging.getLogger(__name__))
def publish_next(db, ipfs_address):
    # treat table as a LIFO stack, so that recent videos get published first:
    row = db["publish_queue"].find_one(order_by=["-id"]) 
    if not row:
        #we ran out of videos, reenqueue all:
        for video in db["videos"].all():
            db["publish_queue"].insert({"youtube_id": video["youtube_id"]})
        return

    publish_one(db, row["youtube_id"], ipfs_address)
    db["publish_queue"].delete(**row)


@traced(logging.getLogger(__name__))
def enqueue(db, url):
    import random

    ydl = YoutubeDL()
    video_ids = ydl.list_videos(url)
    random.shuffle(video_ids)

    for id in video_ids:
        db["publish_queue"].upsert({"youtube_id":id}, ["youtube_id"] )


@traced(logging.getLogger(__name__))
def main():
    import dataset
    import optparse
    parser = optparse.OptionParser()
    parser.add_option("--verbose", action="store_true")
    parser.add_option("--enqueue", metavar="URL")
    parser.add_option("--publish-next", action="store_true")
    parser.add_option("--publish-one",metavar="VIDEO-ID") 
    parser.add_option("--ipfs-address", metavar="HOST:PORT")
    parser.add_option("--only-update-dnslink", action="store_true")

    (options, args) = parser.parse_args()
    db = dataset.connect("sqlite:///db.db")

    if options.verbose:
        logging.basicConfig(
                 stream=sys.stdout,
                 format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")
        logging.getLogger(__name__).setLevel(TRACE)
        logging.getLogger("executor").setLevel(logging.DEBUG)

    if options.only_update_dnslink:
        DNS().update(open("/home/k/.videos_db/ipfs_root_hash.txt").read().strip())
        return
    if options.enqueue:
        enqueue(db, options.enqueue)
        return

    if options.publish_one:
        publish_one(db, options.publish_one, options.ipfs_address)
        return

    if options.publish_next:
        publish_next(db, options.ipfs_address)
        return

        

if __name__ == "__main__":
    main()

