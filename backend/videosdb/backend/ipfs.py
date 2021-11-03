import os
import logging
import shutil
import sys
import tempfile
import ipfshttpclient
from django.conf import settings
import socket

from videosdb.backend.youtube_api import YoutubeDL, parse_youtube_id
from videosdb.models import Video


class DNS:
    def __init__(self, dns_zone):
        self.dns_zone = dns_zone
        path = os.path.dirname(sys.modules[__name__].__file__)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path + "/creds.json"

    def _update_record(self, record_name, record_type, ttl, new_value):
        from google.cloud import dns
        if not self.dns_zone:
            return

        client = dns.Client()
        zone = client.zone(self.dns_zone)
        records = zone.list_resource_record_sets()

        # init transaction
        changes = zone.changes()
        # delete old
        for record in records:
            if record.name == record_name + "." and record.record_type == record_type:
                changes.delete_record_set(record)
        # add new
        record = zone.resource_record_set(
            record_name + ".", record_type, ttl, [new_value, ])
        changes.add_record_set(record)
        # finish transaction
        changes.create()

    def update_dnslink(self, record_name, new_root_hash):
        self._update_record(record_name, "TXT", 300,
                            "dnslink=/ipfs/" + new_root_hash)

    def update_ip(self, record_name, new_ip):
        self._update_record(record_name, "A", 300, new_ip)


class IPFS:
    def __init__(self, files_root="/videos"):

        self.host = socket.gethostbyname(settings.IPFS_HOST)
        self.port = settings.IPFS_PORT
        self.files_root = files_root
        self.dnslink_update_pending = False
        self.api = ipfshttpclient.connect(
            "/ip4/%s/tcp/%s/http" % (self.host, self.port), session=True)
        self.api.files.mkdir(files_root, parents=True)

    def add_file(self, filename, add_to_dir=True, **kwargs):
        result = self.api.add(
            filename, pin=True, **kwargs)
        ipfs_hash = result[0]["Hash"]
        assert ipfs_hash

        if add_to_dir:
            self.add_to_dir(filename, ipfs_hash)

        return ipfs_hash

    def add_to_dir(self, filename, _hash):
        from ipfshttpclient.exceptions import StatusError
        src = "/ipfs/" + _hash
        dst = self.files_root + "/" + os.path.basename(filename)
        try:
            self.api.files.rm(dst)
        except StatusError:
            pass
        self.api.files.cp(src, dst)
        self.dnslink_update_pending = True

    def get_file(self, ipfs_hash):
        self.api.get(ipfs_hash)
        files = os.listdir(".")
        filename = max(files, key=os.path.getctime)
        return filename

    def update_dnslink(self, force=False):
        if not self.dnslink_update_pending and not force:
            return

        root_hash = self.api.files.stat(self.files_root)["Hash"]
        dns = DNS(settings.VIDEOSDB_DNSZONE)
        dns.update_dnslink("videos." +
                           settings.VIDEOSDB_DOMAIN, root_hash)
        self.dnslink_update_pending = False


def download_and_register_in_ipfs(overwrite_hashes=False):
    yt_dl = YoutubeDL()
    videos_dir = os.path.abspath(settings.VIDEO_FILES_DIR)
    if not os.path.exists(videos_dir):
        os.mkdir(videos_dir)
    ipfs = IPFS()

    files = ipfs.api.files.ls("/videos", opts=dict(long=True))
    files_in_ipfs = {}
    if files["Entries"]:
        for file in files["Entries"]:
            if file["Name"].lower().endswith(".mp4"):
                youtube_id = parse_youtube_id(file["Name"])
                if not youtube_id or youtube_id in files_in_ipfs:
                    raise Exception()
                files_in_ipfs[youtube_id] = file

    files_in_disk = {}
    for file in os.listdir(videos_dir):
        youtube_id = parse_youtube_id(file)
        if file.endswith(".part"):
            continue
        if not youtube_id or youtube_id in files_in_disk:
            raise Exception()
        files_in_disk[youtube_id] = file

    # 'Entries': [
    #     {'Size': 0, 'Hash': '', 'Name': 'Software', 'Type': 0}
    # ]
    videos = Video.objects.all().order_by("?")
    for video in videos:

        if not video.youtube_id in files_in_disk:
            logging.debug("Downloading " + video.youtube_id)
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                try:
                    video.filename = yt_dl.download_video(
                        video.youtube_id)
                except YoutubeDL.UnavailableError as e:
                    continue
                video.save()
                try:
                    shutil.move(video.filename, videos_dir)
                except OSError as e:
                    logging.exception(e)
                    continue
        file = files_in_disk.get(video.youtube_id)
        if file and file != video.filename:
            video.filename = file

        if video.youtube_id in files_in_ipfs:
            file = files_in_ipfs[video.youtube_id]

            logging.debug("Already in IPFS:  " + str(file))
            if not video.filename:
                video.filename = file["Name"]
            if not video.ipfs_hash or overwrite_hashes:
                logging.debug("writing hash")
                video.ipfs_hash = file["Hash"]
            video.save()
            continue

        logging.debug("Adding to IPFS: ID:%s, title: %s, Filename: %s, Hash: %s" %
                      (video.youtube_id, video.title, video.filename, video.ipfs_hash))
        video.ipfs_hash = ipfs.add_file(videos_dir + "/" +
                                        video.filename,
                                        wrap_with_directory=True,
                                        nocopy=True)

        video.save()

    ipfs.update_dnslink()
