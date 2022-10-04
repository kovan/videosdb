
# from pytwitter import Api
import fnc
import datetime
import logging
import os
import httpx
from tweepy.asynchronous import AsyncClient
logger = logging.getLogger(__name__)

BITLY_ACCESS_TOKEN = "87dce0221a0751012efc890ba7ef595a3e8763ab"


class Publisher:
    def __init__(self, db) -> None:
        self.db = db
        self.http = httpx.AsyncClient()

    async def _get_bitly_url(self, url):
        response = await self.http.post("https://api-ssl.bitly.com/v4/shorten",
                                        headers={
                                            "Authorization": "Bearer " + BITLY_ACCESS_TOKEN,
                                        },
                                        json={
                                            "long_url": url,
                                            "domain": "bit.ly",
                                            "group_guid": "Bma3nPlFgj5"
                                        })
        response.raise_for_status()
        return response.json()["link"]

    async def _create_post_text(self, video):
        url = os.environ["VIDEOSDB_HOSTNAME"] + \
            "/video/" + video["videosdb"]["slug"]
        # short_url = await self._get_bitly_url(url)
        yt_url = "https://www.youtube.com/watch?v=" + video["id"],
        text = "{title}, {short_url}, {youtube_url} ".format(
            title=video["snippet"]["title"],
            youtube_url=yt_url,
            short_url=url
        )
        return text

    async def _save_to_db(self, video, pub_id):
        video |= {
            "videosdb": {
                "publishing": {

                    "publishDate": datetime.datetime.now().isoformat(),
                    "id":  pub_id

                }
            }
        }
        # await self.db.set("videos/" + video["id"], video)
        logger.info("Published video " + video["id"])

    async def publish_video(self, video):
        raise NotImplementedError()


class TwitterPublisher(Publisher):
    KEYS_DEV = {
        "api_key": "DRGK15vYb1JGEyugbgSrURmsu",
        "api_secret": "C70u8nyvV0kwetNTRk8f0qqLmACmShUsFLWriOkgw0wBfuQq99",

        "access_token": "1576729637199265793-RIBkV8rUCRvP1XuKbYExKiifct55kl",
        "access_secret": "OoyRvpY50nSyANEFt0WyAVeuuHgWyG2pNe2RKlQRNOizS",

    }
    KEYS_STAGING = {
        "api_key": "cKuDDh4GkFJVH7z133yIFpWWd",
        "api_secret": "wOCUGluLxY7dJURJnwVSACu2VYoeWE2CW6sp4bQoGQeVglbUwu",
        "access_token": "1576729637199265793-5xmsyDQaVVaTTHOcXggOHMTxPlV3NU",
        "access_secret": "LUW64jOicSzWzEslXixQ6JYi0RPT911vcsxYKrL65mE4o",
    }
    KEYS_PROD = {
        "api_key": "f73ZNvOyGwYVJUUyav65KW4xv",
        "api_secret": "QOU5Oo9svOWT9tEd9SPiPUUck41gqmU0C6mLzr1wCJtpZeifOp",
        "access_token": "c1l6RHRpMS1tVVBzQ3hLZHkySXI6MTpjaQ",
        "access_secret": "yQuARx02RyIc6EMVFs3i5nVRqTmAMvXbpunyx0Gv40r1bNcxss",
    }

    def __init__(self, db=None) -> None:
        super().__init__(db)

        keys = self.KEYS_DEV
        self.api = AsyncClient(
            consumer_key=keys["api_key"],
            consumer_secret=keys["api_secret"],
            access_token=keys["access_token"],
            access_token_secret=keys["access_secret"])

        self.videos = set()

    async def create_tweet(self, *args, **kwargs):
        return await self.api.create_tweet(*args, **kwargs)

    def add_video(self, video):
        self.videos.add(video)

    async def publish_all(self,):
        for video in self.videos:
            await self.publish_video(video)

    async def publish_video(self, video):
        video_dict = video.to_dict()
        if fnc.get("videosdb.publishing.publishDate", video_dict):
            return

        text = await self._create_post_text(video_dict)

        result = await self.create_tweet(text=text)

        await self._save_to_db(video_dict, result.data["id"], "twiter")


# class FacebookPublisher(Publisher):
#     ACCESS_TOKEN_1 = "199149919028365|Kbax0dCo8FMtUMwXf_1_URCmkLY"
#     ACCESS_TOKEN_2 = "EAAC1IDQuRI0BAPN3FMT0ZCyaPBf72XeZAZAsiHnPb5z8024vfA2jTAy2Vbi3IlhHNU295RCTZBXwmyIsNZBrOWeSOPmDhxzqQUValr7WUYuZBIZBnCg8nrcmtadxxzJXvxiQ36JDCiSYVByHRnYxVxQ4mMgcatTsqyLThhDZADuMLL983w5FiZBoMDZBSDrCSeQVon4INU3aOR2F9tIyuSRAWrqNYBbFM680kZD"

#     def __init__(self, db=None) -> None:
#         super().__init__(db)

#         self.api = facebook.GraphAPI(self.ACCESS_TOKEN_2)

#     async def publish_video(self, video):
#         text = await self._create_post_text(video)

#         result = await self.api.put_object("me", "feed", message=text)

#         await self._save_to_db(video, result, type(self))
