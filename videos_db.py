#!env python3
from executor import execute
from autologging import traced, TRACE
import tempfile
import random
import logging
import json
import sys
import os

@traced(logging.getLogger(__name__))
class Video:
    def __init__(self, youtube_id = "", file=None, ipfs_hash=None):
        self.youtube_id = youtube_id
        self.file = file
        self.published = False
        self.ipfs_hash = ipfs_hash
        self.extension = ""

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
        site_id = "156901386"
        url = 'https://public-api.wordpress.com/rest/v1/sites/' + site_id + '/posts/new'
        headers = { "Authorization": "BEARER " + "qpTIK7(hogZ#3WhSK#N@39xSQHc5aD@7D5VkxnXWBGgXsQwt90E#vw3!3yJA&Kc)" }
        data = {
            "title" : self.title,
            "categories": "videos, " + self.uploader,
            "content": "[embed]https://www.youtube.com/watch?v=%s[/embed]" % self.youtube_id
        }
        requests.post(url,headers=headers,data=data)


    def download(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            filename_format = "'%(uploader)s - %(title)s (%(height)sp) [%(id)s].%(ext)s'"
            execute("youtube-dl --ignore-errors --output %s %s" %( filename_format ,self.youtube_id))
            #TODO

    def fill_info(self):
        with tempfile.TemporaryDirectory() as tmpdir: #tmpdir = tempfile.mkdtemp()
            
            os.chdir(tmpdir)
            cmd = "youtube-dl --ignore-errors --write-info-json --skip-download --output '%(id)s' " + self.youtube_id
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
def publish_one(db, youtube_id):
    video = Video(youtube_id)
    video.fill_info()
    video.publish_wordpress()
    db["videos"].upsert(vars(video),["youtube_id"])

@traced(logging.getLogger(__name__))
def publish_next(db):
    # treat table as a LIFO stack, so that recent videos get published first:
    row = db["publish_queue"].find_one(order_by=["-id"]) 
    if not row:
        #we ran out of videos, reenqueue all:
        for video_row in db["videos"].all():
            db["publish_queue"].insert({"youtube_id": video_row["youtube_id"]})
        return

    publish_one(db, row["youtube_id"])
    db["publish_queue"].delete(**row)


@traced(logging.getLogger(__name__))
def enqueue(db, url):

    def _get_remote_videos_ids(url):
        result = execute("youtube-dl --ignore-errors --playlist-random --get-id " + url, capture=True)
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
    (options, args) = parser.parse_args()
    db = dataset.connect("sqlite:///db.db")
    if options.verbose:
        logging.basicConfig(
                 stream=sys.stderr,
                 format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s")
        logging.getLogger(__name__).setLevel(TRACE)
        logging.getLogger("executor").setLevel(logging.DEBUG)

    if options.enqueue:
        enqueue(db, options.enqueue)
        return

    if options.publish_one:
        publish_one(db, options.publish_one)
        return

    if options.publish_next:
        publish_next(db)
        return

        

if __name__ == "__main__":
    main()

