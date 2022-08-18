import asyncio
import io
import json
import logging
import os
import re
import tempfile
import hashlib
import executor
import httpx
import youtube_transcript_api
from urllib.parse import urlencode
from executor import execute
from google.cloud import firestore

logger = logging.getLogger(__name__)


def parse_youtube_id(string: str) -> str:
    match = re.search(r'\[(.{11})\]\.', string)
    if not match:
        return None
    return match.group(1)


class Cache:

    def __init__(self):
        self.db = firestore.AsyncClient()

    @staticmethod
    def _key_func(key):
        return hashlib.sha256(key.encode('utf-8')).hexdigest()

    async def get(self, key):
        doc = await self.db.collection("cache").document(self._key_func(key)).get()
        if doc.exists:
            return doc.to_dict()
        return None

    async def set(self, key, val):
        await self.db.collection("cache").document(self._key_func(key)).set(val)

    async def delete(self, key):
        await self.db.collection("cache").document(self._key_func(key)).delete()


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

        if "YOUTUBE_API_CACHE" in os.environ:
            obj.cache = Cache()

        logger.debug("Pointing at URL: " + obj.root_url)
        return obj

    async def get_playlist_info(self, playlist_id):
        url = "/playlists"
        params = {
            "part": "snippet",
            "id": playlist_id
        }
        return await self._request_one(url, params)

    async def list_channnelsection_playlist_ids(self, channel_id):
        url = "/channelSections"
        params = {
            "part": "contentDetails",
            "channelId": channel_id
        }
        async for item in self._request_many(url, params):
            details = item.get("contentDetails")
            if not details:
                continue
            if not "playlists" in details:
                continue
            for id in details["playlists"]:
                yield id

    async def list_channel_playlist_ids(self, channel_id):
        url = "/playlists"
        params = {
            "part": "snippet,contentDetails",
            "channelId": channel_id
        }
        async for item in self._request_many(url, params):
            yield item["id"]

    async def get_video_info(self, youtube_id):
        url = "/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": youtube_id
        }
        item = await self._request_one(url, params)
        if not item:
            return None
        return item

    async def list_playlist_items(self, playlist_id):
        url = "/playlistItems"
        params = {
            "part": "snippet",
            "playlistId": playlist_id
        }
        async for item in self._request_many(url, params):
            yield item

    async def get_related_videos(self, youtube_id):
        url = "/search"
        params = {
            "part": "snippet",
            "type": "video",
            "relatedToVideoId": youtube_id
        }
        logger.info("getting related videos")
        result = dict()
        async for video in self._request_many(url, params):
            if video["id"]["videoId"] in result:
                continue

            result[video["id"]["videoId"]] = video
        return result.values()

    async def get_channel_info(self, channel_id):
        url = "/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": channel_id
        }
        return await self._request_one(url, params)


# ------- PRIVATE-------------------------------------------------------

    async def _request_one(self, url, params):
        async for item in self._request_many(url, params):
            return item

    async def _request_many(self, url, params):

        async def _get_with_cache(url):
            headers = {}
            cached = await self.cache.get(url)
            if cached:
                headers["If-None-Match"] = cached["content"]["etag"]

            response = await self.http.get(
                self.root_url + url, timeout=30.0, headers=headers)

            if response.status_code == 304:
                logger.debug("Using cached response.")
                return response, True,  cached["content"]

            asyncio.create_task(self.cache.set(url, {
                "url": url,
                "headers": dict(response.headers),
                "content": response.json()
            }))  # defer
            return response, False

        params["key"] = self.yt_key
        url += "?" + urlencode(params)
        page_token = None

        while True:
            if page_token:
                final_url = url + "&pageToken=" + page_token
            else:
                final_url = url
            logger.debug("requesting: " + final_url)

            if hasattr(self, "cache"):
                response, from_cache, content = await _get_with_cache(url)
            else:
                response = await self.http.get(
                    self.root_url + final_url, timeout=30.0)

            if response.status_code == 403:
                raise self.QuotaExceededError(
                    response.status_code, response.json())

            response.raise_for_status()
            json_response = response.json()

            for item in json_response["items"]:
                yield item

            if not "nextPageToken" in json_response:
                break
            else:
                page_token = json_response["nextPageToken"]


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
    return _sentence_case(result.capitalize() + ".")
