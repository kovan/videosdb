import json
import logging
import os
import re
import httpx
import youtube_transcript_api
from urllib.parse import urlencode
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_youtube_id(string: str):
    match = re.search(r'\[(.{11})]\.', string)
    if not match:
        return None
    return match.group(1)


class Cache:

    def __init__(self, db):
        self.db = db

    # @staticmethod
    # def _key_func(key):
    #     return hashlib.sha256(key.encode('utf-8')).hexdigest()

    async def get(self, key):
        doc = await self.db.collection("cache").document(key).get()
        if doc.exists:
            return doc.to_dict()
        return None

    async def set(self, key, val):
        await self.db.collection("cache").document(key).set(val)

    async def delete(self, key):
        await self.db.collection("cache").document(key).delete()


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
    async def create(cls, db, yt_key=None):
        obj = cls()
        limits = httpx.Limits(max_connections=50)
        obj.http = httpx.AsyncClient(limits=limits)

        obj.yt_key = os.environ.get("YOUTUBE_API_KEY", yt_key)
        if not obj.yt_key:
            obj.yt_key = "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"

        obj.root_url = os.environ.get(
            "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3")

        obj._cache = Cache(db)

        logger.debug("Pointing at URL: " + obj.root_url)
        return obj

    async def get_playlist_info(self, playlist_id):
        url = "/playlists"
        params = {
            "part": "snippet",
            "id": playlist_id
        }
        return await self._request_one(url, params, playlist_id, False)

    async def list_channelsection_playlist_ids(self, channel_id):
        url = "/channelSections"
        params = {
            "part": "contentDetails",
            "channelId": channel_id
        }
        status_code, results = await self._request_many(url, params, channel_id, False)

        async for item in results:
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
        status_code, results = await self._request_many(url, params, channel_id, False)
        async for item in results:
            yield item["id"]

    async def get_video_info(self, youtube_id):
        url = "/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": youtube_id
        }
        return await self._request_one(url, params, youtube_id, False)

    async def list_playlist_items(self, playlist_id):
        url = "/playlistItems"
        params = {
            "part": "snippet",
            "playlistId": playlist_id
        }
        return await self._request_many(url, params, playlist_id)

    async def get_related_videos(self, youtube_id):
        url = "/search"
        params = {
            "part": "snippet",
            "type": "video",
            "relatedToVideoId": youtube_id
        }
        logger.info("getting related videos")

        status_code, results = await self._request_many(url, params, youtube_id)
        if status_code == 304:
            return status_code, None

        related_videos = dict()
        async for video in results:
            if video["id"]["videoId"] in related_videos:
                continue

            related_videos[video["id"]["videoId"]] = video
        return status_code, related_videos.values()

    async def get_channel_info(self, channel_id):
        url = "/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": channel_id
        }
        return await self._request_one(url, params, channel_id, False)


# ------- PRIVATE-------------------------------------------------------

    async def _request_one(self, url, params, id, use_cache=True):
        result = self._request(url, params, id, use_cache)
        status_code = await anext(result)
        try:
            item = await anext(result)
        except StopAsyncIteration:
            item = None
        return status_code, item

    async def _request_many(self, url, params, id, use_cache=True):
        results = self._request(url, params, id, use_cache)
        status_code = await anext(results)
        return status_code, results

    async def _request(self, url, params, id, use_cache=True):

        params["key"] = self.yt_key
        url += "?" + urlencode(params)
        page_token = None

        headers = {}
        if use_cache:
            cached = await self._cache.get(id)
            if cached:
                headers["If-None-Match"] = cached["etag"]

        while True:
            if page_token:
                final_url = url + "&pageToken=" + page_token
            else:
                final_url = url
            logger.debug("requesting: " + final_url)

            response = await self.http.get(
                self.root_url + final_url, timeout=30.0, headers=headers)
            logger.debug("Received response, code: " +
                         str(response.status_code))
            if response.status_code == 403:
                raise self.QuotaExceededError(
                    response.status_code, response.json())

            if not page_token:  # first page
                yield response.status_code

            if response.status_code == 304:
                logger.debug(
                    "Got 304 Not modified for id " + str(id))
                break

            response.raise_for_status()

            json_response = response.json()
            if "pageInfo" in json_response:
                logger.debug(
                    "Pages: " + str(json_response["pageInfo"]["totalResults"]))
            if not page_token and use_cache:  # first page
                await self._cache.set(id, {
                    "etag": json_response["etag"],
                    "timestamp": datetime.now().isoformat()
                })

            for item in json_response["items"]:
                yield item

            if not "nextPageToken" in json_response:
                break
            else:
                page_token = json_response["nextPageToken"]


"""
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
        return videos """


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
