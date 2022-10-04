# from pytwitter import Api
import datetime
import logging
import os
import facebook
import httpx
from tweepy.asynchronous import AsyncClient
logger = logging.getLogger(__name__)

BITLY_ACCESS_TOKEN = "87dce0221a0751012efc890ba7ef595a3e8763ab"


class Publisher:
    def __init__(self, db) -> None:
        self.db = db


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

    def __init__(self, db=None) -> None:
        super().__init__(db)

        self.http = httpx.AsyncClient()
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

    async def get_bitly_url(self, url):
        return await self.http.post("https://api-ssl.bitly.com/v4/shorten",
                                    headers={
                                        "Authorization": "Bearer " + BITLY_ACCESS_TOKEN
                                    },
                                    data={
                                        "long_url": url,
                                        "domain": "bit.ly"
                                    })

    async def publish_video(self, video):
        url = os.environ["VIDEOSDB_HOSTNAME"] + \
            "/video/" + video["videosdb"]["slug"]
        short_url = await self.get_bitly_url(url)
        text = "{title}, {bitly_url}"
        result = await self.create_tweet(text=video["title"])
        video |= {
            "videosdb": {
                "publishing": {
                    "twitter": {
                        "publishDate": datetime.datetime.now().isoformat(),
                        "id": result.data["id"]
                    }
                }
            }
        }
        # await self.db.set("videos/" + video["id"], video)
        logger.info("Published video " + video["id"])


class FacebookPublisher(Publisher):
    def __init__(self, db) -> None:
        super().__init__(db)

        oauth_access_token = ""
        self.api = facebook.GraphAPI(oauth_access_token)

        groups = self.api.get_object("me/groups")
        group_id = groups['data'][0]['id']  # we take the ID of the first group
        self.api.put_object(group_id, "feed", message="from terminal")
