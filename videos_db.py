#!env python3
from executor import execute
from autologging import traced, TRACE
import tempfile
import requests
import logging
import json
import sys
import os

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
        file=video.get("file")
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
    requests.post(url,headers=headers,data=data)


@traced(logging.getLogger(__name__))
class IPFS:
    def __init__(self, host, root_hash):
        self.host = host
        self.root_hash = root_hash

    def add_video(self, video_filename):
        # IPFS add:
        url = self.host + "/api/v0/add"
        files = { "files": open(video_filename, "rb") }
        response = requests.post(url, files=files)
        hash = response.json()["Hash"]

        # IPFS pin:
        params = { "arg" : "/ipfs/" + hash }
        requests.get(self.host + "/api/v0/pin/add", params=params)

        # IPFS add to directory:
        params = { 
            "arg" : self.root_hash,
            "arg" : hash,
            "arg" : video_filename
        }
        requests.get(self.host + "/api/v0/object/patch/add-link", params=params)
        return hash


@traced(logging.getLogger(__name__))
class YoutubeDL:
    def __init__(self):
        self.base_cmd =  "youtube-dl --youtube-skip-dash-manifest --ignore-errors "

    def download_video(self,url):
        filename_format = "%(uploader)s - %(title)s (%(height)sp) [%(id)s].%(ext)s"
        execute(self.base_cmd + "--output '%s' %s" %( filename_format ,url))
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
def publish_one(db, youtube_id, ipfs_host):
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


    if ipfs_host and "ipfs_hash" not in video:
        ipfs = IPFS(ipfs_host, open("ipfs_root_hash.txt").read())
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            video_filename = ydl.download_video(video["youtube_id"])
            video["ipfs_hash"]= ipfs.add_video(video_filename)
            os.chdir(old_cwd)
           
    _publish_wordpress(video)
    db["videos"].upsert(video,["youtube_id"], ensure=True)



@traced(logging.getLogger(__name__))
def publish_next(db, ipfs_host):
    # treat table as a LIFO stack, so that recent videos get published first:
    row = db["publish_queue"].find_one(order_by=["-id"]) 
    if not row:
        #we ran out of videos, reenqueue all:
        for video in db["videos"].all():
            db["publish_queue"].insert({"youtube_id": video["youtube_id"]})
        return

    publish_one(db, row["youtube_id"], ipfs_host)
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
    parser.add_option("--ipfs-host", metavar="PROTOCOL://HOST:PORT")
    (options, args) = parser.parse_args()
    db = dataset.connect("sqlite:///db.db")
    if options.verbose:
        logging.basicConfig(
                 stream=sys.stdout,
                 format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")
        logging.getLogger(__name__).setLevel(TRACE)
        logging.getLogger("executor").setLevel(logging.DEBUG)

    if options.enqueue:
        enqueue(db, options.enqueue)
        return

    if options.publish_one:
        publish_one(db, options.publish_one, options.ipfs_host)
        return

    if options.publish_next:
        publish_next(db, options.ipfs_host)
        return

        

if __name__ == "__main__":
    main()

