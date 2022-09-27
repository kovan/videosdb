#!env poetry run python3

import anyio
import argparse
import logging.config
import logging
import os
from videosdb.downloader import Downloader
from videosdb.db import DB
from videosdb.settings import LOGGING
from autologging import TRACE
from videosdb.youtube_api import YoutubeAPI


def entrypoint():

    logging.config.dictConfig(LOGGING)
    if os.environ.get("LOGLEVEL") == "TRACE":
        logging.getLogger("videosdb").setLevel(TRACE)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check-for-new-videos", action="store_true")
    parser.add_argument("-e", "--exclude-transcripts", action="store_true")
    parser.add_argument("-d", "--fill-related-videos", action="store_true")
    parser.add_argument("-u", "--update-dnslink", action="store_true")
    parser.add_argument(
        "-f", "--download-and-register-in-ipfs", action="store_true")
    parser.add_argument("-o", "--overwrite-hashes", action="store_true")

    options = parser.parse_args()
    if options.check_for_new_videos:
        DB.wait_for_port()
        YoutubeAPI.wait_for_port()
        downloader = Downloader(options)

        anyio.run(downloader.check_for_new_videos)

    if options.download_and_register_in_ipfs:
        ipfs = IPFS()
        ipfs.download_and_register_folder(
            options.overwrite_hashes)

    if options.update_dnslink:
        ipfs = IPFS()
        ipfs.update_dnslink(force=True)


if __name__ == "__main__":
    entrypoint()
