import re
import os
import executor
import io
import tempfile
import logging
import json
import httplib2
import youtube_transcript_api
from autologging import traced
from executor import execute
import re
from urllib.parse import urljoin, urlencode

logger = logging.getLogger(__name__)


def parse_youtube_id(string: str) -> str:
    match = re.search(r'\[(.{11})\]\.', string)
    if not match:
        return None
    return match.group(1)


def _sentence_case(text):
    punc_filter = re.compile(r'([.!?]\s*)')
    split_with_punctuation = punc_filter.split(text)

    final = ''.join([i.capitalize() for i in split_with_punctuation])
    return final


@traced(logging.getLogger(__name__))
class YoutubeAPI:
    class YoutubeAPIError(Exception):
        def __init__(self, s):
            self.s = s

    def __init__(self, yt_key):
        self.yt_key = yt_key
        self.http = httplib2.Http(".cache")
        self.transcript_api = youtube_transcript_api.YouTubeTranscriptApi(
            cookies=None)
        self.root_url = "https://www.googleapis.com/youtube/v3"

    def _make_request(self, url):
        url += "&key=" + self.yt_key
        page_token = None

        while True:
            if page_token:
                final_url = url + "&pageToken=" + page_token
            else:
                final_url = url
            logger.debug("request: " + final_url)
            (response, content) = self.http.request(final_url)
            if response.status != 200:
                raise self.YoutubeAPIError("%s: %s\n %s" %
                                           (response.status, response.reason, json.loads(content)))

            json_response = json.loads(content)
            items = json_response["items"]
            for item in items:
                yield item

            if not "nextPageToken" in json_response:
                break
            else:
                page_token = json_response["nextPageToken"]

    def _get_playlist_info(self, playlist_id):
        url = self.root_url + "/playlists?part=snippet"
        url += "&id=" + playlist_id
        items = list(self._make_request(url))
        playlist = {
            "id": playlist_id,
            "title": items[0]["snippet"]["title"],
            "channel_title": items[0]["snippet"]["channelTitle"]
        }
        return playlist

    def _get_channnelsection_playlists(self, channel_id):
        url = self.root_url + "/channelSections?part=contentDetails"
        url += "&channelId=" + channel_id

        for item in self._make_request(url):
            details = item.get("contentDetails")
            if not details:
                continue
            if not "playlists" in details:
                continue
            for id in details["playlists"]:
                yield id

    def _get_channel_playlists(self, channel_id):
        url = self.root_url + "/playlists?part=snippet%2C+contentDetails"
        url += "&channelId=" + channel_id

        for item in self._make_request(url):
            yield item["id"]

    def list_playlists(self, channel_id):
        ids_channelsection = self._get_channnelsection_playlists(channel_id)
        ids_channel = self._get_channel_playlists(channel_id)

        playlist_ids = set(list(ids_channelsection) + list(ids_channel))
        for _id in playlist_ids:
            yield self._get_playlist_info(_id)

    def get_video_info(self, youtube_id):
        url = self.root_url + "/videos?part=snippet,contentDetails,statistics"
        url += "&id=" + youtube_id
        items = list(self._make_request(url))
        if items:
            video_info = {
                **items[0]["snippet"],
                **items[0]["contentDetails"],
                **items[0]["statistics"],
            }
            return video_info
        return None

    def list_playlist_videos(self, playlist_id):
        url = self.root_url + "/playlistItems?part=snippet"
        url += "&playlistId=" + playlist_id

        for item in self._make_request(url):
            yield item["snippet"]["resourceId"]["videoId"]

    def get_related_videos(self, youtube_id):
        url = self.root_url + "/search?part=snippet&type=video"
        url += "&relatedToVideoId=" + youtube_id
        items = self._make_request(url)
        return items

    def get_video_transcript(self, youtube_id):
        # url = self.root_url + "/captions?part=id,snippet&videoId=" + youtube_id
        # transcripts = self.transcript_fetcher.fetch(youtube_id)
        # transcript = transcripts.find_transcript(
        #     ("en", "en-US", "en-GB")).fetch()

        transcript = self.transcript_api.get(
            youtube_id, languages=("en", "en-US", "en-GB"))

        result = ""
        for d in transcript:
            result += d["text"] + " "
        return _sentence_case(result.capitalize() + ".")


@traced(logging.getLogger(__name__))
class YoutubeDL:
    class UnavailableError(Exception):
        def __init__(self, s):
            self.s = s

        def __repr__(self):
            return self.s

    def __init__(self):
        # --limit-rate 1M "
        self.BASE_CMD = "youtube-dl -f 'best[height<=720]'  --youtube-skip-dash-manifest --ignore-errors "

    def download_video(self, _id, asynchronous=False):
        filename_format = "%(uploader)s - %(title)s [%(id)s].%(ext)s"
        cmd = self.BASE_CMD + \
            "--output '%s' %s" % (filename_format,
                                  "http://www.youtube.com/watch?v=" + _id)
        logging.info(cmd)
        try:
            execute(cmd, asynchronous)
        except executor.ExternalCommandFailed as e:
            raise self.UnavailableError(repr(e))
        files = os.listdir(".")
        if files:
            filename = max(files, key=os.path.getctime)
            return filename
        return None

    def download_thumbnail(self, _id):
        execute(self.BASE_CMD +
                "--write-thumbnail --skip-download http://www.youtube.com/watch?v=" + _id)
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    def download_info(self, youtube_id):
        cmd = self.BASE_CMD + \
            "--write-info-json --skip-download --output '%(id)s' http://www.youtube.com/watch?v=" + \
            youtube_id
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                result = execute(cmd, capture_stderr=True)
                with io.open(youtube_id + ".info.json") as f:
                    video_json = json.load(f)
        except executor.ExternalCommandFailed as e:
            out = str(e.command.stderr)
            if "copyright" in out or \
               "Unable to extract video title" in out or \
               "available in your country" in out or \
               "video is unavailable" in out:
                raise self.UnavailableError(repr(e))
            raise
        return video_json

    def list_videos(self, url):
        result = execute(self.BASE_CMD + "--flat-playlist --playlist-random -j " +
                         url, check=False, capture=True, capture_stderr=True)
        videos = []
        for video_json in result.splitlines():
            video = json.loads(video_json)
            videos.append(video)
        return videos
