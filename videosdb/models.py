from django.db import models


class Tag(models.Model):
    name = models.CharField(db_index=True, max_length=256)
    def _str_(self):
        return self.name

class Category(models.Model):
    name = models.CharField(db_index=True, max_length=256)
    def _str_(self):
        return self.name

class Video(models.Model):
    youtube_id = models.CharField(max_length=16, db_index=True)
    title = models.CharField(max_length=256)
    filename = models.CharField(max_length=4096, null=True)
    ipfs_hash = models.CharField(max_length=256, null=True)
    ipfs_thumbnail_hash = models.CharField(max_length=256, null=True)
    publish_date = models.DateTimeField(null=True)
    categories = models.ManyToManyField(Category)
    published = models.BooleanField(default=False)
    excluded = models.BooleanField(default=False)
    post_id = models.IntegerField(null=True)
    #these come from youtube:
    tags = models.ManyToManyField(Tag)
    description = models.CharField(max_length=4096, null=True)
    uploader = models.CharField(max_length=256, null=True)
    upload_date = models.CharField(max_length=256, null=True)
    duration = models.IntegerField(null=True)
    channel_url = models.CharField(max_length=1024, null=True)
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

    def _str_(self):
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
            if tag_obj not in self.tags:
                self.tags.add(tag_obj)

        self.save()


#class Playlist(models.Model):
#    youtube_id = models.CharField(max_length=64, db_index=True)
#    videos = models.ManyToManyField(Video)
#    title = models.CharField(max_length=1024)
#    item_count = models.IntegerField()
#
#    def _str_(self):
#        return self.title
#    def url(self):
#        return "https://www.youtube.com/playlist?list=" + self.youtube_id

