#!env python3
from executor import execute
import dataset
import json
import os
import optparse

class Video:
    def __init__(self, youtube_id, file=None, ipfs_hash=None):
        self.youtube_id = youtube_id
        self.file = file
        self.published = False
        self.ipfs_hash = ipfs_hash

    def __repr__(self):
        return self.youtube_id

    def publish_blogger(self):
        import blogger
        import jinja2
        template_raw = '''
        <br />
        <div style="padding-bottom: 56.25%; position: relative;">
        <iframe allow="encrypted-media" allowfullscreen="" frameborder="0" gesture="media" src="https://www.youtube.com/embed/{{ video_id }}" style="height: 100%; left: 0; position: absolute; top: 0; width: 100%;">
        </iframe>
        </div>
        <ul>
        {% for file in files %}
            <li>Download from IPFS: <a href="https://cloudfare-ipfs.com/ipfs/{{ ipfs_hash }}">{{ title }}</a></li>
        {% endfor %}
        </ul>
        </div>
        '''
        template = jinja2.Template(template_raw)
        html = template.render(
            video_id=self.youtube_id,
            title=self.title
        )
        eb = blogger.EasyBlogger(
            clientId="62814020656-olqaifiob7ufoqpe1k4iah3v2ra12h8a.apps.googleusercontent.com", 
            clientSecret = "fnUgEpdkUTtthUtDk0vLvjMm",
            blogId = "8804984470189945822")
        labels = "video, " + self.uploader
        eb.post(self.title, html, labels, isDraft=False)
        self.published = True

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



def publish_video(videos):
    import random
    if not videos:
        return
    video_id = random.choice(videos)
    video = db.get(video_id)
    video.publish_wordpress()
    db.put(video_id, video)


      
def check_for_videos(db, url, skip_download):

    def find_new_videos_ids(url):
        result = execute("youtube-dl --get-id " + url, capture=True)
        remote_videos_ids = result.splitlines()
        for id in remote_videos_ids:
            if db["videos"].find_one(youtube_id=id)
        new_videos_ids = remote_videos_ids - local_videos_ids
        return new_videos_ids

    def download_video(video_id, skip_download=False):
        import tempfile
        import glob
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            cmd = "youtube-dl"\
                    " --write-info-json"\
                    " --ignore-errors"\
                    " --playlist-random"\
                    " --output '%(uploader)s - %(title)s (%(height)sp) [%(id)s].%(ext)s' "\
                    + video_id
            if skip_download:
                cmd +=  " --skip-download"

            execute(cmd)
            
            video_json = json.load(open(glob.glob("*.json")[0]))

            video = Video(video_id)
            
            downloaded_video_files = [file for file in glob.glob("*") if not file.endswith(".json")]
            if downloaded_video_files:
                video.file = downloaded_video_files[0]

            interesting_attrs = ["title",
                    "description",
                    "uploader",
                    "upload_date",
                    "duration",
                    "channel_url"]
            for attr in interesting_attrs:
                setattr(video, attr, video_json[attr])

        return video

        
    new_videos_ids = find_new_videos_ids(url)
    for video_id in new_videos_ids:
        video = download_video(video_id, skip_download)
        db.put(video_id, video)

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("--url", metavar="URL")
    parser.add_option("--skip-publish", action="store_true")
    parser.add_option("--skip-download", action="store_true")
    (options, args) = parser.parse_args()
    
    db = lazydb.Db("db.db")
    db = dataset.connect("sqlite:///db.db")
    check_for_videos(db, options.url, options.skip_download)
    if not options.skip_publish:
        publish_random_video(db)

