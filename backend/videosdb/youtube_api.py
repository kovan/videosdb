from google.cloud import firestore
import json
import logging
import os
import re
import httpx
import youtube_transcript_api
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def parse_youtube_id(string: str):
    match = re.search(r'\[(.{11})]\.', string)
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

    def __init__(self, db, yt_key=None):
        self.db = db
        limits = httpx.Limits(max_connections=50)
        self.http = httpx.AsyncClient(limits=limits)

        self.yt_key = os.environ.get("YOUTUBE_API_KEY", yt_key)
        if not self.yt_key:
            self.yt_key = "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"

        self.root_url = os.environ.get(
            "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3")

        logger.debug("Pointing at URL: " + self.root_url)

    async def get_playlist_info(self, playlist_id):
        url = "/playlists"
        params = {
            "part": "snippet",
            "id": playlist_id
        }
        return await self._request_one(url, params, playlist_id)

    async def list_channelsection_playlist_ids(self, channel_id):
        url = "/channelSections"
        params = {
            "part": "contentDetails",
            "channelId": channel_id
        }
        results = await self._request_main(url, params, channel_id)

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
        results = await self._request_main(url, params, channel_id)
        async for item in results:
            yield item["id"]

    async def get_video_info(self, youtube_id):
        url = "/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": youtube_id
        }
        return await self._request_one(url, params, youtube_id)

    async def list_playlist_items(self, playlist_id):
        url = "/playlistItems"
        params = {
            "part": "snippet",
            "playlistId": playlist_id
        }
        return await self._request_main(url, params, playlist_id)

    # async def get_related_videos(self, youtube_id):
    #     url = "/search"
    #     params = {
    #         "part": "snippet",
    #         "type": "video",
    #         "relatedToVideoId": youtube_id
    #     }
    #     logger.info("getting related videos")

    #     results = await self._request_many(url, params, youtube_id)

    #     related_videos = dict()
    #     async for video in results:
    #         if video["id"]["videoId"] in related_videos:
    #             continue

    #         related_videos[video["id"]["videoId"]] = video
    #     return related_videos.values()

    async def get_channel_info(self, channel_id):
        url = "/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": channel_id
        }
        return await self._request_one(url, params, channel_id)


# ------- PRIVATE-------------------------------------------------------


    async def _request_one(self, url, params, id, use_cache=True):

        result = self._request_main(url, params, id)
        try:
            item = await anext(result)
        except StopAsyncIteration:
            item = None
        return item

    async def _request_main(self,  use_cache=True, *args, **kwargs):
        if use_cache:
            return self._request_with_cache(*args, **kwargs)
        else:
            return self._request_without_cache(*args, **kwargs)

    async def _request_without_cache(self, *args, **kwargs):
        status_code, pages = self._request_decoupled(*args, **kwargs)

        async for page in pages:
            for item in page["items"]:
                yield item

    async def _request_with_cache(self, url, params, id):
        cache_col = self.db.collection("cache")
        cached_ref = cache_col.document(id)
        transaction = self.db.transaction()
        cached = await cached_ref.get(transaction=transaction)
        headers = {}
        if cached.exists:
            headers["If-None-Match"] = cached["etag"]

        status_code, response_pages = self._request_decoupled(
            url, params, id, headers)

        if status_code == 304:
            async for page in self.db.cached_ref.collection("pages").stream():
                yield page
        elif status_code >= 200 and status_code < 300:
            page_n = 0
            for page in response_pages:
                _write_to_cache(
                    transaction, cached_ref, page, page_n)
                yield page
                page_n += 1

    @staticmethod
    async def _request_decoupled(self, *args, **kwargs):
        response = self._request_base(*args, *kwargs)
        status_code = await anext(response)
        return status_code, response

    async def _request_base(self, url, params, id, headers=None):

        params["key"] = self.yt_key
        url += "?" + urlencode(params)
        page_token = None

        while True:
            if page_token:
                final_url = url + "&pageToken=" + page_token
            else:
                final_url = url
            logger.debug("requesting: " + final_url)

            response = await self.http.get(
                self.root_url + final_url, timeout=30.0, headers=headers if headers else {})
            logger.debug("Received response, code: " +
                         str(response.status_code))
            if response.status_code == 403:
                raise self.QuotaExceededError(
                    response.response.json())
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

            yield json_response

            if not "nextPageToken" in json_response:
                break
            else:
                page_token = json_response["nextPageToken"]


@firestore.async_transactional
async def _write_to_cache(transaction, cached_ref, json_response, page):
    if page == 0:
        transaction.set(
            cached_ref, {"etag": json_response["etag"]})

    transaction.set(
        cached_ref.collection("pages").document(page),
        json_response)


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
