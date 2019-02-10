from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=256)

class Category(models.Model):
    name = models.CharField(max_length=256)

class Video(models.Model):
    youtube_id = models.CharField(max_length=256)
    title = models.CharField(max_length=256)
    filename = models.CharField(max_length=4096)
    ipfs_hash = models.CharField(max_length=256)
    ipfs_thumbnail_hash = models.CharField(max_length=256)

# this come from Youtube:
class VideoDetails(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag)
    description = models.CharField(max_length=4096)
    uploader = models.CharField(max_length=256)
    upload_date = models.CharField(max_length=256, null=True)
    duration = models.IntegerField()
    channel_url = models.CharField(max_length=1024, null=True)
    uploader_url = models.CharField(max_length=256)
    ext = models.CharField(max_length=256)
    format = models.CharField(max_length=256)
    format_note = models.CharField(max_length=256)
    fulltitle = models.CharField(max_length=256)
    width = models.IntegerField()
    height = models.IntegerField()
    view_count = models.IntegerField()
    abr = models.IntegerField()
    thumbnail = models.CharField(max_length=1024, null=True)

class Publication(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    publish_date = models.DateTimeField()
    categories = models.ManyToManyField(Category)
    tags = models.ManyToManyField(Tag)
    published = models.BooleanField()
    excluded = models.BooleanField()
    src_channel = models.CharField(max_length=256)
