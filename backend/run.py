#!env python3

import anyio
import argparse
import logging.config
import logging
import os
from dotenv import load_dotenv
from videosdb.db import DB
from videosdb.downloader import Downloader
from videosdb.settings import LOGGING
from autologging import TRACE


def entrypoint():

    logging.config.dictConfig(LOGGING)
    if os.environ.get("LOGLEVEL") == "TRACE":
        logging.getLogger("videosdb").setLevel(TRACE)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check-for-new-videos", action="store_true")
    parser.add_argument("-e", "--enable-transcripts", action="store_true")
    parser.add_argument("-d", "--fill-related-videos", action="store_true")
    parser.add_argument("-u", "--update-dnslink", action="store_true")
    parser.add_argument("-v", "--dotenv", action="store")
    parser.add_argument("-x", "--export-to-emulator-host", action="store")
    parser.add_argument("-t", "--enable-twitter-publishing",
                        action="store_true")
    parser.add_argument(
        "-f", "--download-and-register-in-ipfs", action="store_true")
    parser.add_argument("-s", "--validate-db-schema", action="store_true")

    options = parser.parse_args()

    if options.dotenv:
        load_dotenv(options.dotenv)

    if options.check_for_new_videos:
        downloader = Downloader(options)

        anyio.run(downloader.check_for_new_videos)

    if options.validate_db_schema:
        db = DB()
        anyio.run(db.validate_videos_schema)


if __name__ == "__main__":
    entrypoint()
