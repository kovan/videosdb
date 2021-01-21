import re
import logging
import json
import httplib2
from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger("videosdb")


def _sentence_case(text):
    punc_filter = re.compile(r'([.!?]\s*)')
    split_with_punctuation = punc_filter.split(text)

    final = ''.join([i.capitalize() for i in split_with_punctuation])
    return final


class YoutubeAPI:
    def __init__(self, yt_key):
        self.yt_key = yt_key
        self.http = httplib2.Http(".cache")
        self.root_url = "https://www.googleapis.com/youtube/v3"

    def _make_request(self, base_url, page_token=""):
        url = base_url
        if page_token:
            url += "&pageToken=" + page_token
        url += "&key=" + self.yt_key

        logger.debug("request: " + url)
        (response, content) = self.http.request(url)
        if response.status != 200:
            raise Exception("%s: %s\n %s" %
                            (response.status, response.reason, content))

        json_response = json.loads(content)
        items = json_response["items"]
        if "nextPageToken" in json_response:
            items += self._make_request(base_url,
                                        json_response["nextPageToken"])
        # logger.debug(items)
        return items

    def _get_playlist_info(self, playlist_id):
        url = self.root_url + "/playlists?part=snippet"
        url += "&id=" + playlist_id
        items = self._make_request(url)
        playlist = {
            "id": playlist_id,
            "title": items[0]["snippet"]["title"],
            "channel_title": items[0]["snippet"]["channelTitle"]
        }
        return playlist

    def _get_channnelsection_playlists(self, channel_id):
        url = self.root_url + "/channelSections?part=contentDetails"
        url += "&channelId=" + channel_id
        items = self._make_request(url)
        playlist_ids = []
        for item in items:
            details = item.get("contentDetails")
            if not details:
                continue
            if not "playlists" in details:
                continue
            playlist_ids += details["playlists"]
        return playlist_ids

    def _get_channel_playlists(self, channel_id):
        url = self.root_url + "/playlists?part=snippet%2C+contentDetails"
        url += "&channelId=" + channel_id
        items = self._make_request(url)
        playlist_ids = []
        for item in items:
            playlist_ids.append(item["id"])
        return playlist_ids

    def list_playlists(self, channel_id):
        ids_channelsection = self._get_channnelsection_playlists(channel_id)
        ids_channel = self._get_channel_playlists(channel_id)

        playlist_ids = set(ids_channelsection + ids_channel)
        playlists = []
        for _id in playlist_ids:
            playlist = self._get_playlist_info(_id)
            playlists.append(playlist)

        return playlists

    def get_video_info(self, youtube_id):
        url = self.root_url + "/videos?part=snippet,contentDetails,statistics"
        url += "&id=" + youtube_id
        items = self._make_request(url)
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
        items = self._make_request(url)
        video_ids = []
        for item in items:
            video_ids.append(item["snippet"]["resourceId"]["videoId"])
        return video_ids

    def get_related_videos(self, youtube_id):
        url = self.root_url + "/search?part=snippet&type=video"
        url += "&relatedToVideoId=" + youtube_id
        items = self._make_request(url)
        return items

    def get_video_transcript(self, youtube_id):
        #url = self.root_url + "/captions?part=id,snippet&videoId=" + youtube_id

        try:
            t = YouTubeTranscriptApi.get_transcript(
                youtube_id, languages=("en", "en-US"), cookies="youtube.com_cookies.txt")
        except Exception as e:
            logger.warn(e)
            return None

        result = ""
        for d in t:
            result += d["text"] + " "
        return _sentence_case(result.capitalize() + ".")
