import io
import json
import logging
import os
import re
import tempfile
import executor
import httpx
import youtube_transcript_api
from urllib.parse import urlencode
from executor import execute

logger = logging.getLogger(__name__)

MAX_CACHE_SIZE = 100000


def parse_youtube_id(string: str) -> str:
    match = re.search(r'\[(.{11})\]\.', string)
    if not match:
        return None
    return match.group(1)


class YoutubeAPI:

    class QuotaExceededError(Exception):
        def __init__(self, status, json):
            self.status = status
            self.json = json

        def __str__(self):
            return "%s %s" % (self.status, json.dumps(self.json, indent=4, sort_keys=True))

    async def aclose(self):
        return await self.http.aclose()

    @classmethod
    async def create(cls, yt_key=None):
        obj = cls()

        obj.http = httpx.AsyncClient(http2=True)
        obj.yt_key = os.environ.get("YOUTUBE_API_KEY", yt_key)
        if not obj.yt_key:
            obj.yt_key = "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"

        obj.root_url = os.environ.get(
            "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3")

        logger.debug("Pointing at URL: " + obj.root_url)
        return obj

    # @cached(cache=LRUCache(maxsize=MAX_CACHE_SIZE))
    async def get_playlist(self, playlist_id, etag=None):
        url = "/playlists"
        params = {
            "part": "snippet",
            "id": playlist_id
        }
        response = YoutubeAPI.Request(self,  url, params, etag)
        return response, await response.one()

    async def list_channnelsection_playlist_ids(self, channel_id, etag=None):
        url = "/channelSections"
        params = {
            "part": "contentDetails",
            "channelId": channel_id
        }
        async for item in YoutubeAPI.Request(self,  url, params):
            details = item.get("contentDetails")
            if not details:
                continue
            if not "playlists" in details:
                continue
            for id in details["playlists"]:
                yield id

    async def list_channel_playlist_ids(self, channel_id, etag=None):
        url = "/playlists"
        params = {
            "part": "snippet,contentDetails",
            "channelId": channel_id
        }
        async for item in YoutubeAPI.Request(self,  url, params, etag):
            yield item["id"]

    async def get_video_info(self, youtube_id, etag=None):
        url = "/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": youtube_id
        }
        response = YoutubeAPI.Request(self,  url, params, etag)
        return response, await response.one()

    async def list_playlist_items(self, playlist_id, etag=None):
        url = "/playlistItems"
        params = {
            "part": "snippet",
            "playlistId": playlist_id
        }
        return YoutubeAPI.Request(self,  url, params, etag)

    async def get_related_videos(self, youtube_id, etag=None):
        url = "/search"
        params = {
            "part": "snippet",
            "type": "video",
            "relatedToVideoId": youtube_id
        }
        logger.info("getting related videos")
        result = dict()
        async for video in YoutubeAPI.Request(self,  url, params, etag):
            if video["id"]["videoId"] in result:
                continue

            result[video["id"]["videoId"]] = video
        return result.values()

    async def get_channel_info(self, channel_id, etag=None):
        url = "/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": channel_id
        }
        response = YoutubeAPI.Request(self,  url, params, etag)
        return response, await response.one()


# ------- PRIVATE-------------------------------------------------------


    class Request():
        def __init__(self, youtube_api, url, params, etag=None):
            self.api = youtube_api
            self._headers = {}
            if etag:
                self._headers["If-None-Match"] = etag

            params["key"] = youtube_api.yt_key
            self._url = url + "?" + urlencode(params)

        def __aiter__(self):
            self._page_token = None
            self.not_modified = False
            self._items = []
            self._finished = False
            return self

        async def one(self):
            async for item in self:
                return item
            return None

        async def __anext__(self):
            if self._items:
                return self._items.pop()

            if self._finished:
                raise StopAsyncIteration

            # otherwise we make one request more:
            if self._page_token:
                final_url = self._url + "&pageToken=" + self._page_token
            else:
                final_url = self._url
            logger.debug("requesting: " + final_url)

            response = await self.api.http.get(
                self.api.root_url + final_url,  headers=self._headers, timeout=30.0)

            if response.status_code == 304:
                logger.debug("304 Not modified.")
                self.not_modified = True
                self._finished = True
                raise StopAsyncIteration

            if response.status_code == 403:
                raise self.api.QuotaExceededError(
                    response.status_code, response.json())

            response.raise_for_status()
            json_response = response.json()

            logger.debug("Response:\n" + json.dumps(json_response,
                                                    indent=4, sort_keys=True))

            self._items = json_response["items"]

            if not "nextPageToken" in json_response:
                self._finished = True
            else:
                self._page_token = json_response["nextPageToken"]

            if self._items:
                return self._items.pop()
            else:
                raise StopAsyncIteration


# ----------- unused -----------------:


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
            "--external-downloader=aria2c --external-downloader-args '--min-split-size=1M --max-connection-per-server=16 --max-concurrent-downloads=16 --split=16' " +\
            "--output '%s' %s" % (filename_format,
                                  "http://www.youtube.com/watch?v=" + _id)
        logger.info(cmd)
        try:
            # import ipdb
            # ipdb.set_trace()

            execute(cmd, asynchronous=asynchronous, silent=True)
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
                result = execute(cmd, capture=True, capture_stderr=True)
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


def get_video_transcript(youtube_id):

    def _sentence_case(text):
        punc_filter = re.compile(r'([.!?]\s*)')
        split_with_punctuation = punc_filter.split(text)

        final = ''.join([i.capitalize() for i in split_with_punctuation])
        return final
    # url = "/captions?part=id,snippet&videoId=" + youtube_id
    # transcripts = self.transcript_fetcher.fetch(youtube_id)
    # transcript = transcripts.find_transcript(
    #     ("en", "en-US", "en-GB")).fetch()
    transcripts = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(
        youtube_id, languages=("en", "en-US", "en-GB"))

    result = ""
    for d in transcripts:
        result += d["text"] + "\n"
    result = _sentence_case(result.capitalize() + ".")
    logger.info("Transcription successfully downloaded for video " + youtube_id)
