import anyio
import argparse
import logging.config
import logging
import os
from videosdb.downloader import Downloader
from videosdb.settings import LOGGING
from autologging import TRACE


def entrypoint():

    logging.config.dictConfig(LOGGING)
    if os.environ["LOGLEVEL"] == "TRACE":
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
