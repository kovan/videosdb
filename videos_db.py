#!env python3
from executor import execute
from autologging import traced, TRACE
import tempfile
import random
import logging
import json
import sys
import os
YDL_BASE_CMD = "youtube-dl --youtube-skip-dash-manifest --ignore-errors "

@traced(logging.getLogger(__name__))
class Video:
    def __init__(self, youtube_id = None):
        self.youtube_id = youtube_id
        self.file = ""
        self.ipfs_hash = ""

    def __repr__(self):
        return self.youtube_id

    def publish_blogger(self):
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
            youtube_id=self.youtube_id,
            title=self.title
        )
        eb = blogger.EasyBlogger(
            clientId="62814020656-olqaifiob7ufoqpe1k4iah3v2ra12h8a.apps.googleusercontent.com", 
            clientSecret = "fnUgEpdkUTtthUtDk0vLvjMm",
            blogId = "8804984470189945822")
        labels = "video, " + self.uploader
        eb.post(self.title, html, labels, isDraft=False)

    def publish_wordpress(self):
        import requests
        import jinja2
        import urllib

        template_raw = '''"[embed]https://www.youtube.com/watch?v={{ youtube_id }}[/embed] '''
        if self.ipfs_hash:
            template_raw += '''
                <p>Download video: <a href="http://ipfs.spiritualityresources.net/ipfs/{{ ipfs_hash }}?filename={{ file|urlencode}}">{{ file }}</a></p>
        '''
        template = jinja2.Template(template_raw)
        html = template.render(
            youtube_id=self.youtube_id,
            ipfs_hash=self.ipfs_hash,
            file=self.file
        )
        site_id = "156901386"
        url = 'https://public-api.wordpress.com/rest/v1/sites/' + site_id + '/posts/new'
        headers = { "Authorization": "BEARER " + "qpTIK7(hogZ#3WhSK#N@39xSQHc5aD@7D5VkxnXWBGgXsQwt90E#vw3!3yJA&Kc)" }
        categories = [
            "Videos",
            "Short videos" if self.duration/60 <= 20 else "Long videos",
            self.uploader
        ]
        data = {
            "title" : self.title,
            "categories": ",".join(categories),
            "content": html
        }
        requests.post(url,headers=headers,data=data)


    def download_to_ipfs(self):
        import requests
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            filename_format = "%(uploader)s - %(title)s (%(height)sp) [%(id)s].%(ext)s"
            execute(YDL_BASE_CMD + "--output '%s' %s" %( filename_format ,self.youtube_id))
            self.file = os.listdir(".")[0]

            url = "http://ipfs:5001/api/v0/add"
            files = {
                "files": open(self.file, "rb")
            }

            response = requests.post(url, files=files)
            self.ipfs_hash = response.json()["Hash"]
            self.size = response.json()["Size"]
            

    def fill_info(self):
        with tempfile.TemporaryDirectory() as tmpdir: #tmpdir = tempfile.mkdtemp()
            
            os.chdir(tmpdir)
            cmd = YDL_BASE_CMD + "--write-info-json --skip-download --output '%(id)s' " + self.youtube_id
            execute(cmd)

            video_json = json.load(open(self.youtube_id + ".info.json"))
            interesting_attrs = ["title",
                    "description",
                    "uploader",
                    "upload_date",
                    "duration",
                    "channel_url"]
            for attr in interesting_attrs:
                setattr(self, attr, video_json[attr])


@traced(logging.getLogger(__name__))
def publish_one(db, youtube_id, enable_ipfs):
    video = Video(youtube_id)
    video.fill_info()
    if enable_ipfs:
        video.download_to_ipfs()
    video.publish_wordpress()
    db["videos"].upsert(vars(video),["youtube_id"], ensure=True)

@traced(logging.getLogger(__name__))
def publish_next(db, enable_ipfs):
    # treat table as a LIFO stack, so that recent videos get published first:
    row = db["publish_queue"].find_one(order_by=["-id"]) 
    if not row:
        #we ran out of videos, reenqueue all:
        for video_row in db["videos"].all():
            db["publish_queue"].insert({"youtube_id": video_row["youtube_id"]})
        return

    publish_one(db, row["youtube_id"], enable_ipfs)
    db["publish_queue"].delete(**row)


@traced(logging.getLogger(__name__))
def enqueue(db, url):

    def _get_remote_videos_ids(url):
        result = execute(YDL_BASE_CMD + "--playlist-random --get-id " + url, check=False, capture=True)
        if not result:
            raise Exception("youtube-dl error")
        ids = result.splitlines()
        random.shuffle(ids)
        return ids

    for id in _get_remote_videos_ids(url):
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
    parser.add_option("--enable-ipfs", action="store_true")
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
        publish_one(db, options.publish_one, options.enable_ipfs)
        return

    if options.publish_next:
        publish_next(db, options.enable_ipfs)
        return

        

if __name__ == "__main__":
    main()

