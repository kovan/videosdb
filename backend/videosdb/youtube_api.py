import json
import logging
import os
import re
import httpx
from urllib.parse import urlencode
from videosdb.utils import wait_for_port
import youtube_transcript_api
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def parse_youtube_id(string: str):
    match = re.search(r'\[(.{11})]\.', string)
    if not match:
        return None
    return match.group(1)


YT_API_ROOT_URL = "https://www.googleapis.com/youtube/v3"


def get_root_url():
    return os.environ.get("YOUTUBE_API_URL", YT_API_ROOT_URL)


class YoutubeAPI:

    class QuotaExceeded(Exception):
        def __init__(self, status, json={}):
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

        self.root_url = get_root_url()

        parsed_ytapi_url = urlparse(self.root_url)
        if parsed_ytapi_url.port:
            wait_for_port(parsed_ytapi_url.port)
        logger.debug("Pointing at URL: " + self.root_url)

    async def get_playlist_info(self, playlist_id):
        url = "/playlists"
        params = {
            "part": "snippet",
            "id": playlist_id
        }
        return await self._request_one(url, params)

    async def list_channelsection_playlist_ids(self, channel_id):
        url = "/channelSections"
        params = {
            "part": "contentDetails",
            "channelId": channel_id
        }
        results = self._request_main(url, params)

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
        results = self._request_main(url, params)
        async for item in results:
            yield item["id"]

    async def get_video_info(self, youtube_id):
        url = "/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": youtube_id
        }
        return await self._request_one(url, params)

    async def list_playlist_items(self, playlist_id):
        url = "/playlistItems"
        params = {
            "part": "snippet",
            "playlistId": playlist_id
        }
        return self._request_main(url, params)

    async def get_related_videos(self, youtube_id):
        url = "/search"
        params = {
            "part": "snippet",
            "type": "video",
            "relatedToVideoId": youtube_id
        }
        logger.info("getting related videos")

        results = self._request_main(url, params)

        related_videos = dict()
        async for video in results:
            if video["id"]["videoId"] in related_videos:
                continue

            related_videos[video["id"]["videoId"]] = video
        return related_videos.values()

    async def get_channel_info(self, channel_id):
        url = "/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": channel_id
        }
        return await self._request_one(url, params)


# ------- PRIVATE-------------------------------------------------------

    async def _request_one(self, url, params, use_cache=True):

        result = self._request_main(url, params, use_cache)
        try:
            item = await anext(result)
        except StopAsyncIteration:
            item = None
        return item

    async def _request_main(self, url, params, use_cache=True):
        if use_cache:
            pages = self._request_with_cache(url, params)
        else:
            status_code, pages = self._request_decoupled(url, params)

        async for page in pages:
            for item in page["items"]:
                yield item

    async def _request_with_cache(self, url, params):
        @staticmethod
        def _key_func(url: str, params: dict):
            return url.lstrip("/") + "?" + urlencode(params)
            # s = url + str(params)
            # return hashlib.sha256(s.encode('utf-8')).hexdigest()

        cache_id = _key_func(url, params)
        cached = await self.db.get("cache/" + cache_id)
        headers = {}
        if cached.exists:
            headers["If-None-Match"] = cached.get("etag")

        status_code, response_pages = await self._request_decoupled(
            url, params, headers=headers)

        if status_code == 304:
            async for page in self.db.stream("cache/%s/pages" % cache_id):
                yield page.to_dict()
            return

        if status_code >= 200 and status_code < 300:
            page_n = 0
            try:
                async for page in response_pages:
                    if page_n == 0:
                        await self.db.set("cache/" + cache_id, {"etag": page["etag"]})
                    await self.db.set("cache/%s/pages/%s" % (cache_id, page_n), page)
                    yield page
                    page_n += 1
            except Exception as e:
                # do not cache half-responses
                logger.info("Deleting half-downloaded cache pages")
                await self.db.recursive_delete("cache/" + cache_id)
                raise e

            return

    async def _request_decoupled(self, *args, **kwargs):
        response = self._request_base(*args, **kwargs)
        status_code = await anext(response)
        return status_code, response

    async def _request_base(self, url, params, headers=None):

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
            logger.debug("Received response for URL: %s code: %s" %
                         (final_url, response.status_code))

            if response.status_code == 403:
                raise self.QuotaExceeded(
                    response.status_code,
                    response.json())
            if not page_token:  # first page
                yield response.status_code

            if response.status_code == 304:
                break

            response.raise_for_status()

            json_response = response.json()

            # if not page_token:  # first page
            #     if "pageInfo" in json_response:
            #         logger.debug(
            #             "Total items: " + str(json_response["pageInfo"]["totalResults"]))

            yield json_response

            if not "nextPageToken" in json_response:
                break
            else:
                page_token = json_response["nextPageToken"]


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
