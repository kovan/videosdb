# from pytwitter import Api
import datetime
import logging
import tweepy
import facebook

logger = logging.getLogger(__name__)


class Publisher:
    def __init__(self) -> None:
        self.db = db


class TwitterPublisher(Publisher):
    KEYS = {
        # "client_id": "enBHZzVNLWlmV3JKU1NSeWFLV3U6MTpjaQ",
        # "client_secret": "elP76AdKDxpnk6Zndm-4UBeYakhxKvy2xl-FjTsgTX9WB6WV-X",
        "api_key": "DRGK15vYb1JGEyugbgSrURmsu",
        "api_secret": "C70u8nyvV0kwetNTRk8f0qqLmACmShUsFLWriOkgw0wBfuQq99",
        # "bearer token": "AAAAAAAAAAAAAAAAAAAAAKj6hgEAAAAAUCcIEPQZHmKbpuw5bNLB1TiQqJ8%3DyuRZQ6DmgwTHEAxXq2CpORKNNBgmXtGDGCsliSxn60KxuBxS6u",
        "access_token": "1576729637199265793-RIBkV8rUCRvP1XuKbYExKiifct55kl",
        "access_secret": "OoyRvpY50nSyANEFt0WyAVeuuHgWyG2pNe2RKlQRNOizS",

    }

    def __init__(self, db) -> None:
        super().__init__(db)

        self.api = tweepy.asynchronous.AsyncClient(
            consumer_key=self.KEYS["api_key"],
            consumer_secret=self.KEYS["api_secret"],
            access_token=self.KEYS["access_token"],
            access_token_secret=self.KEYS["access_secret"])

        self.videos = set()

    async def create_tweet(self, *args, **kwargs):
        pass  # await self.api.create_tweet(*args, **kwargs)

    def add_video(self, video):
        self.videos.add(video)

    async def publish_tweet(self, video):
        await self.create_tweet(v)
        video |= {
            "videosdb": {
                "publishDate": datetime.datetime.now().isoformat()
            }
        }
        await self.db.set("videos/" + video["id"], video)
        logger.info("Published video " + video["id"])


class FacebookPublisher(Publisher):
    def __init__(self, db) -> None:
        super().__init__(db)

        oauth_access_token = ""
        self.api = facebook.GraphAPI(oauth_access_token)

        groups = self.api.get_object("me/groups")
        group_id = groups['data'][0]['id']  # we take the ID of the first group
        self.api.put_object(group_id, "feed", message="from terminal")
