from videosdb.models import Video
from videosdb.backend.ipfs import IPFS
import re


def run():
    ipfs = IPFS()
    files = ipfs.api.files.ls("/videos")
    if not files["Entries"]:
        return
    for file in files["Entries"]:
        match = re.search(r'\[(.{11})\]\.', file["Name"])
        if not match:
            continue
        youtube_id = match.groups(1)
        try:
            video = Video.objects.get(youtube_id=youtube_id)
            video.filename = file["Name"]
            video.ipfs_hash = file["Hash"]
            video.save()
        except Video.DoesNotExist:
            continue
