from django.db import models


class Tag(models.Model):
    name = models.CharField(unique=True, max_length=256)
    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(unique=True, max_length=256)
    def __str__(self):
        return self.name

class Video(models.Model):
    youtube_id = models.CharField(max_length=16, unique=True)
    title = models.CharField(max_length=256, null=True)
    filename = models.CharField(max_length=4096, null=True)
    ipfs_hash = models.CharField(max_length=256, unique=True, null=True)
    ipfs_thumbnail_hash = models.CharField(max_length=256, null=True)
    publish_date = models.DateTimeField(null=True)
    categories = models.ManyToManyField(Category)
    published = models.BooleanField(default=False)
    excluded = models.BooleanField(default=False)
    post_id = models.IntegerField(null=True)
    thumbnail_id = models.IntegerField(null=True)
    thumbnail_url = models.CharField(null=True, max_length=1024)

    #these come from youtube:
    tags = models.ManyToManyField(Tag)
    description = models.CharField(max_length=4096, null=True)
    uploader = models.CharField(max_length=256, null=True)
    upload_date = models.CharField(max_length=256, null=True)
    duration = models.IntegerField(null=True)
    channel_url = models.CharField(max_length=1024, null=True)
    channel_id = models.CharField(max_length=256, null=True)
    uploader_url = models.CharField(max_length=1024, null=True)
    ext = models.CharField(max_length=256, null=True)
    format = models.CharField(max_length=256, null=True)
    format_note = models.CharField(max_length=256, null=True)
    fulltitle = models.CharField(max_length=256, null=True)
    width = models.IntegerField(null=True)
    height = models.IntegerField(null=True)
    view_count = models.IntegerField(null=True)
    abr = models.IntegerField(null=True)
    thumbnail = models.CharField(max_length=1024, null=True)

    def __str__(self):
        return self.title

    def parse_youtube_info(self, info):
        interesting_attrs = ["title",
                "description",
                "uploader",
                "uploader_url",
                "upload_date",
                "duration",
                "channel_url",
                "ext",
                "format",
                "format_note",
                "fulltitle",
                "is_live",
                "playlist",
                "width",
                "height",
                "view_count",
                "thumbnail",
                "abr"]

        for attr in interesting_attrs:
            setattr(self, attr, info[attr])

        for tag in info["tags"]:
            tag_obj, created = Tag.objects.get_or_create(name=tag)
            self.tags.add(tag_obj)

        self.save()


