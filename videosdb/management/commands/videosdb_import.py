from django.core.management.base import BaseCommand, CommandError
from videosdb.models import Tag, Category, Video, Publication
import dataset

class Command(BaseCommand):

    def handle(self, *args, **options):
        db = dataset.connect("sqlite:///db.db")
        for v in db["videos"]:
            video = Video(
                youtube_id=v["youtube_id"],
                filename=v["filename"],
                ipfs_hash=v["ipfs_hash"],
                ipfs_thumbnail_hash=v["ipfs_thumbnail_hash"],
                title=v["title"])
            video.save()


        

