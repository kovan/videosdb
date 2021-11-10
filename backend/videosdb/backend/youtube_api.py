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
import aiogoogle

from aiogoogle.sessions.aiohttp_session import AiohttpSession
import aiohttp
from aiogoogle import Aiogoogle
from executor import execute
from google.cloud import firestore

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

    @classmethod
    async def create(cls, yt_key):
        obj = cls()

        obj.http = httpx.AsyncClient(http2=True)
        obj.yt_key = os.environ.get("YOUTUBE_API_KEY", yt_key)
        # if not "YOUTUBE_API_NO_CACHE" in os.environ:
        #     obj.http = CachingClient(obj.http)
        obj.root_url = os.environ.get(
            "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3")

        obj.cache = Cache()
        return obj

    #     obj.aiogoogle = Aiogoogle(
    #         api_key=yt_key, session_factory=lambda: AiohttpSession(trust_env=True))
    #     obj.api = await obj.aiogoogle.discover('youtube', 'v3')
    #     return obj

    # async def _aiogoogle_run(self, method):
    #     async with self.aiogoogle:
    #         return await self.aiogoogle.as_api_key(
    #             method
    #         )

    # async def aio_list_playlist_items(self, playlist_id):
    #     result = await self._aiogoogle_run(
    #         self.api.playlistItems.list(
    #             id=playlist_id,
    #             part="snippet"
    #         )
    #     )
    #     return result

    async def get_playlist_info(self, playlist_id):
        url = "/playlists?part=snippet"
        url += "&id=" + playlist_id
        return await self._request_one(url)

    async def list_channnelsection_playlist_ids(self, channel_id):
        url = "/channelSections?part=contentDetails"
        url += "&channelId=" + channel_id
        ids = []
        async for item in self._request_many(url):
            details = item.get("contentDetails")
            if not details:
                continue
            if not "playlists" in details:
                continue
            for id in details["playlists"]:
                ids.append(id)
        return ids

    async def list_channel_playlist_ids(self, channel_id):
        url = "/playlists?part=snippet%2C+contentDetails"
        url += "&channelId=" + channel_id

        return (item["id"] async for item in self._request_many(url))

    async def get_video_info(self, youtube_id):
        url = "/videos?part=snippet,contentDetails,statistics"
        url += "&id=" + youtube_id

        return await self._request_one(url)

    async def list_playlist_items(self, playlist_id):
        url = "/playlistItems?part=snippet"
        url += "&playlistId=" + playlist_id
        return (item async for item in self._request_many(url))

    async def get_related_videos(self, youtube_id):
        logging.info("getting related videos")
        url = "/search?part=snippet&type=video"
        url += "&relatedToVideoId=" + youtube_id
        result = dict()
        async for video in self._request_many(url):
            if video["id"]["videoId"] in result:
                continue

            result[video["id"]["videoId"]] = video
        return result.values()

    async def get_channel_info(self, channel_id):
        url = "/channels?part=snippet%2CcontentDetails%2Cstatistics"
        url += "&id=" + channel_id
        return await self._request_one(url)

    def get_video_transcript(self, youtube_id):
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


# ------- PRIVATE-------------------------------------------------------


    async def _request_one(self, url):
        async for item in self._request_many(url):
            return item
        else:
            return None

    async def _request_many(self, url):

        async def _get_with_cache(url):
            headers = {}
            cached = await self.cache.get(url)
            if cached:
                headers["If-None-Match"] = cached["content"]["etag"]

            response = await self.http.get(
                self.root_url + url, timeout=10.0, headers=headers)

            if response.status_code == 304:
                logger.debug("Using cached response.")
                return response, cached["content"], True

            if response.status_code == 200:
                logger.debug("Using new response.")
                asyncio.create_task(self.cache.set(url, {
                    "url": url,
                    "headers": dict(response.headers),
                    "content": response.json()
                }))  # defer

            return response, False

        url += "&key=" + self.yt_key
        page_token = None
        results = {}

        while True:
            if page_token:
                final_url = url + "&pageToken=" + page_token
            else:
                final_url = url
            logger.debug("requesting: " + final_url)

            if "YOUTUBE_API_ENABLE_CACHE" in os.environ:
                response, content, from_cache = await _get_with_cache(url)
            else:
                response = await self.http.get(self.root_url + url, timeout=10.0)

            if response.status_code == 403:
                raise self.QuotaExceededError(
                    response.status_code, response.json())

            response.raise_for_status()
            json_response = response.json()

            results = results | json_response

            if not "nextPageToken" in json_response:
                break
            else:
                page_token = json_response["nextPageToken"]

        return results


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
