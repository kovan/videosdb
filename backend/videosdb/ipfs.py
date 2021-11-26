import os
import logging
import shutil
import sys
import tempfile
import ipfshttpclient
import videosdb.settings as settings
import socket

from videosdb.youtube_api import YoutubeDL, parse_youtube_id
#from videosdb.models import Video
from google.cloud import firestore

logger = logging.getLogger(__name__)

class DNS:
    def __init__(self, dns_zone):
        self.dns_zone = dns_zone

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

    def download_and_register_folder(self, overwrite_hashes=False):
        yt_dl = YoutubeDL()
        db = firestore.Client()
        videos_dir = os.path.abspath(settings.VIDEO_FILES_DIR)
        if not os.path.exists(videos_dir):
            os.mkdir(videos_dir)

        files = self.api.files.ls(self.files_root, opts=dict(long=True))
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
        # videos = Video.objects.all().order_by("?")
        video_ids = db.collection("meta").document("meta").get().to_dict()["videoIds"]

        for video_id in video_ids:
            video_ref = db.collection("videos").document(video_id)

            if not video_id in files_in_disk:
                logger.debug("Downloading " + video_id)
                with tempfile.TemporaryDirectory() as tmpdir:
                    os.chdir(tmpdir)
                    try:
                        filename = yt_dl.download_video(
                            video_id)
                    except YoutubeDL.UnavailableError as e:
                        continue
                    video_ref.set({
                        "videosdb": {
                            "filename": filename
                        }
                    }, merge=True)
                    try:
                        shutil.move(filename, videos_dir)
                    except OSError as e:
                        logger.exception(e)
                        continue

            file = files_in_disk.get(video_id)
            # if file and file != video.filename:
            #     video.filename = file

            if video_id in files_in_ipfs:
                file = files_in_ipfs[video_id]

                logger.debug("Already in IPFS:  " + str(file))
                video_ref.set({
                    "videosdb": {
                        "filename": file["Name"],
                        "ipfs_hash": file["Hash"]
                    }
                }, merge=True)
                continue

            # adding to IPFS:
            video_doc = video_ref.get()
            video = video_doc.to_dict()
            logger.debug("Adding to IPFS: ID:%s, title: %s, Filename: %s, Hash: %s" %
                          (video_id, video["snippet"]["title"], video["videosdb"].get("filename",""), video["videosdb"].get("ipfs_hash", "")))
            ipfs_hash = self.add_file(videos_dir + "/" +
                                      video["videosdb"]["filename"],
                                      wrap_with_directory=True,
                                      nocopy=True)
            video_ref.set({
                "videosdb": {
                    "ipfs_hash": ipfs_hash
                }
            }, merge=True)

        self.update_dnslink()
