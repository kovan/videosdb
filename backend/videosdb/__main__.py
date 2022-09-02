import argparse
import logging.config
from videosdb.ipfs import IPFS

from videosdb.downloader import Downloader
from videosdb.settings import LOGGING


def entrypoint():
    logging.config.dictConfig(LOGGING)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check-for-new-videos", action="store_true")
    parser.add_argument("-e", "--exclude-transcripts", action="store_true")
    parser.add_argument("-u", "--update-dnslink", action="store_true")
    parser.add_argument(
        "-f", "--download-and-register-in-ipfs", action="store_true")
    parser.add_argument("-o", "--overwrite-hashes", action="store_true")

    options = parser.parse_args()
    if options.check_for_new_videos:
        downloader = Downloader(
            exclude_transcripts=options.exclude_transcripts)
        downloader.check_for_new_videos()

    if options.download_and_register_in_ipfs:
        ipfs = IPFS()
        ipfs.download_and_register_folder(
            options.overwrite_hashes)

    if options.update_dnslink:
        ipfs = IPFS()
        ipfs.update_dnslink(force=True)


if __name__ == "__main__":
    entrypoint()

