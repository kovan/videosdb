
from copy import deepcopy
import json
import logging
import os
import re
from typing import Iterable, NewType, OrderedDict
import anyio
import httpx
from urllib.parse import urlencode
import redis.asyncio as redis
from videosdb.utils import wait_for_port
import youtube_transcript_api
from urllib.parse import urlparse
from types import AsyncGeneratorType
logger = logging.getLogger(__name__)


def parse_youtube_id(string: str):
    match = re.search(r'\[(.{11})]\.', string)
    if not match:
        return None
    return match.group(1)


async def pop_first(async_generator):
    first = await anext(async_generator)
    return first, async_generator


class Cache:

    def __init__(self, redis_db_n=None):
        if redis_db_n:
            self.redis = redis.Redis(db=redis_db_n)
        else:
            self.redis = redis.Redis()

    @staticmethod
    def key_func(url: str, params: dict):
        keys = list(params.keys())
        keys.sort()
        params_seq = []
        for key in keys:
            if key == "key":  # the api key can vary, skip it
                continue
            params_seq.append((key, params[key]))

        return url.lstrip("/") + "?" + urlencode(params_seq)

    @staticmethod
    def _pages_key_func(key, page_n):
        return f"{key}_page_{page_n}"

    async def get(self, key):
        async def page_generator():
            for page_n in range(page_count):
                value = await self.redis.get(
                    self._pages_key_func(key, page_n)
                )
                yield json.loads(value)

        value = await self.redis.get(key)
        if not value:
            return None, None

        json_value = json.loads(value)
        page_count = json_value["n_pages"]

        return json_value["etag"], page_generator()

    async def set(self, key, page_generator):
        transaction = self.redis.pipeline()
        page_count = 0
        etag = None
        async for page in page_generator:
            if page_count == 0:
                etag = page["etag"]
            transaction.set(
                self._pages_key_func(key, page_count),
                json.dumps(page))
            page_count += 1
            yield page

        transaction.set(key,
                        json.dumps({
                            "etag": etag,
                            "n_pages": page_count
                        }))
        logger.debug("Response Etag: " + etag)
        await transaction.execute()

    async def __aenter__(self):
        self._transaction = self.redis.pipeline()
        return self._transaction

    async def __aexit__(self, exc_type, exc_value, traceback):
        if not exc_type and not exc_value and not traceback:
            await self._transaction.execute()


class YoutubeAPI:
    APIReturnType = NewType(
        "APIReturnType", tuple[bool, AsyncGeneratorType[dict]])

    @staticmethod
    def get_root_url() -> str:
        return os.environ.get("YOUTUBE_API_URL",  "https://www.googleapis.com/youtube/v3")

    @staticmethod
    def wait_for_port() -> None:
        parsed_ytapi_url = urlparse(YoutubeAPI.get_root_url())
        if parsed_ytapi_url.port:
            wait_for_port(parsed_ytapi_url.port)

    class QuotaExceeded(Exception):
        def __init__(self, status, json={}):
            self.status = status
            self.json = json

        def __str__(self):
            return "%s %s" % (self.status, json.dumps(self.json, indent=4, sort_keys=True))

    async def aclose(self) -> None:
        return await self.http.aclose()

    def __init__(self, db, yt_key=None, redis_db_n=None):
        self.db = db
        limits = httpx.Limits(max_connections=50)
        self.http = httpx.AsyncClient(limits=limits)

        self.cache = Cache(redis_db_n)

        self.yt_key = os.environ.get("YOUTUBE_API_KEY", yt_key)
        if not self.yt_key:
            self.yt_key = "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU"

        self.root_url = YoutubeAPI.get_root_url()

        logger.debug("Pointing at URL: " + self.root_url)

    async def get_playlist_info(self, playlist_id) -> APIReturnType:
        url = "/playlists"
        params = {
            "part": "snippet",
            "id": playlist_id
        }
        return await self._request_one(url, params)

    async def list_channelsection_playlist_ids(self, channel_id) -> APIReturnType:
        async def generator(results):
            async for item in results:
                details = item.get("contentDetails")
                if not details:
                    continue
                if not "playlists" in details:
                    continue
                for id in details["playlists"]:
                    yield id

        url = "/channelSections"
        params = {
            "part": "contentDetails",
            "channelId": channel_id
        }
        modified, results = await self._request_main(url, params)
        return modified, generator(results)

    async def list_channel_playlist_ids(self, channel_id) -> APIReturnType:
        async def generator(results):
            async for item in results:
                yield item["id"]

        url = "/playlists"
        params = {
            "part": "snippet,contentDetails",
            "channelId": channel_id
        }
        modified, results = await self._request_main(url, params)
        return modified, generator(results)

    async def get_video_info(self, youtube_id) -> APIReturnType:
        url = "/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": youtube_id
        }
        return await self._request_one(url, params)

    async def list_playlist_items(self, playlist_id) -> APIReturnType:
        url = "/playlistItems"
        params = {
            "part": "snippet",
            "playlistId": playlist_id
        }
        return await self._request_main(url, params)

    async def get_channel_info(self, channel_id) -> APIReturnType:
        url = "/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": channel_id
        }
        return await self._request_one(url, params)

    async def get_related_videos(self, youtube_id) -> tuple[bool, Iterable]:
        url = "/search"
        params = {
            "part": "snippet",
            "type": "video",
            "relatedToVideoId": youtube_id
        }
        logger.info("getting related videos")

        modified, results = await self._request_main(url, params)

        related_videos = dict()
        async for video in results:
            if video["id"]["videoId"] in related_videos:
                continue

            related_videos[video["id"]["videoId"]] = video
        return modified, related_videos.values()


# ------- PRIVATE-------------------------------------------------------


    async def _request_one(self, url, params, use_cache=True):

        modified, generator = await self._request_main(url, params, use_cache)
        try:
            item = await anext(generator)
        except StopAsyncIteration:
            item = None
        return modified, item

    async def _request_main(self, url, params, use_cache=True):
        async def generator(pages):
            async for page in pages:
                for item in page["items"]:
                    yield item

        if use_cache:
            result = self._request_with_cache(url, params)
        else:
            result = self._request_base(url, params)

        status_code, pages = await pop_first(result)

        return status_code != 304, generator(pages)

    async def _request_with_cache(self, url, params):

        headers = {}

        key = Cache.key_func(url, params)

        etag, cached_pages = await self.cache.get(key)

        if etag:
            logger.debug("Request Etag: " + etag)
            headers["If-None-Match"] = etag

        status_code, response_pages = await pop_first(
            self._request_base(url, params, headers=headers)
        )

        yield status_code

        if status_code == 304:
            pages_generator = cached_pages
        elif status_code >= 200 and status_code < 300:
            pages_generator = self.cache.set(key, response_pages)

        async for page in pages_generator:
            yield page

    async def _request_base(self, url, params, headers=None, max_retries=5):

        params["key"] = self.yt_key
        url += "?" + urlencode(params)
        page_token = None

        while True:
            if page_token:
                final_url = url + "&pageToken=" + page_token
            else:
                final_url = url
            logger.debug("requesting: " + final_url)

            response = await self._get_with_retries(
                self.root_url + final_url, headers=headers)

            if response.status_code == 403:
                raise self.QuotaExceeded(
                    response.status_code,
                    response.json())

            if response.status_code != 304:
                response.raise_for_status()

            if not page_token:  # first page
                yield response.status_code

            if response.status_code == 304:
                break

            json_response = response.json()

            yield json_response

            if not "nextPageToken" in json_response:
                break
            else:
                page_token = json_response["nextPageToken"]

    async def _get_with_retries(self, url, timeout=60.0, headers=None, max_retries=5):
        retries = 0
        while True:
            response = await self.http.get(url, timeout=timeout, headers=headers if headers else {})
            must_retry = response.status_code >= 500 and response.status_code < 600
            log_severity = logging.DEBUG if not must_retry else logging.WARN
            logger.log(log_severity, "Received response for URL: %s code: %s" %
                       (url, response.status_code))
            if not must_retry:
                break
            retries += 1
            if retries > max_retries:
                response.raise_for_status()
            anyio.sleep(3.0)
        return response


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
