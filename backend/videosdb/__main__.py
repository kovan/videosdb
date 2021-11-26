import os
import sys
import argparse
import logging.config
from .ipfs import IPFS

from .downloader import Downloader
from .settings import LOGGING

BASE_DIR = os.path.dirname(sys.modules[__name__].__file__)
os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS',
                      os.path.join(BASE_DIR, "creds.json"))


def dbg():
    os.chdir("/tmp")
    import ipdb
    ipdb.set_trace()


def main():
    logging.config.dictConfig(LOGGING)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--check-for-new-videos", action="store_true")
    parser.add_argument("-u", "--update-dnslink", action="store_true")
    parser.add_argument(
        "-f", "--download-and-register-in-ipfs", action="store_true")
    parser.add_argument("-o", "--overwrite-hashes", action="store_true")

    options = parser.parse_args()
    if options.check_for_new_videos:
        downloader = Downloader()
        downloader.check_for_new_videos()

    if options.download_and_register_in_ipfs:
        ipfs = IPFS()
        ipfs.download_and_register_folder(
            options.overwrite_hashes)

    if options.update_dnslink:
        ipfs = IPFS()
        ipfs.update_dnslink(force=True)


main()
