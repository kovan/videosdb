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
    added_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    published_date = models.DateTimeField(null=True)
    categories = models.ManyToManyField(Category)
    published = models.BooleanField(default=False)
    excluded = models.BooleanField(default=False)
    post_id = models.IntegerField(null=True)
    thumbnail_id = models.IntegerField(null=True)
    thumbnail_url = models.CharField(null=True, max_length=1024)
    tags = models.ManyToManyField(Tag)
    uploader = models.CharField(max_length=256, null=True)
    channel_id = models.CharField(max_length=256, null=True)
    duration = models.IntegerField(null=True)
    full_response = models.CharField(max_length=4096, null=True)

    def __str__(self):
        return self.youtube_id + " - " + self.title

    def set_tags(self, tags):
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(name=tag)
            self.tags.add(tag_obj)
        self.save()


