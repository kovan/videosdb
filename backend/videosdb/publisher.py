#from pytwitter import Api
from videosdb.db import DB
import tweepy

KEYS = {
    # "client_id": "enBHZzVNLWlmV3JKU1NSeWFLV3U6MTpjaQ",
    # "client_secret": "elP76AdKDxpnk6Zndm-4UBeYakhxKvy2xl-FjTsgTX9WB6WV-X",
    "api_key": "DRGK15vYb1JGEyugbgSrURmsu",
    "api_secret": "C70u8nyvV0kwetNTRk8f0qqLmACmShUsFLWriOkgw0wBfuQq99",
    # "bearer token": "AAAAAAAAAAAAAAAAAAAAAKj6hgEAAAAAUCcIEPQZHmKbpuw5bNLB1TiQqJ8%3DyuRZQ6DmgwTHEAxXq2CpORKNNBgmXtGDGCsliSxn60KxuBxS6u",
    "access_token": "1576729637199265793-RIBkV8rUCRvP1XuKbYExKiifct55kl",
    "access_secret": "OoyRvpY50nSyANEFt0WyAVeuuHgWyG2pNe2RKlQRNOizS",

}


class Publisher:
    def __init__(self) -> None:
        self.db = DB()

        self.api = tweepy.Client(
            consumer_key=KEYS["api_key"],
            consumer_secret=KEYS["api_secret"],
            access_token=KEYS["access_token"],
            access_token_secret=KEYS["access_secret"])

        tweepy.Client()

    def publish_tweets(self):
        self.api.create_tweet(text="hi")
