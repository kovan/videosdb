from dirtyfields import DirtyFieldsMixin
from django.conf import settings
import re
from uuslug import uuslug
from django.db import models
# Import slugify to generate slugs from strings
from django.utils.text import slugify
import json
import logging

logger = logging.getLogger("videosdb")


class Tag(DirtyFieldsMixin, models.Model):
    name = models.CharField(unique=True, max_length=256)
    slug = models.SlugField(unique=True, max_length=256,
                            null=True, db_index=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"])
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)
        super(Tag, self).save(*args, **kwargs)

    @property
    def popularity(self):
        return self.video_set.count()


class Category(DirtyFieldsMixin, models.Model):
    name = models.CharField(unique=True, max_length=256)
    slug = models.SlugField(unique=True, max_length=256,
                            null=True, db_index=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"])
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)
        super(Category, self).save(*args, **kwargs)


class Video(DirtyFieldsMixin, models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["youtube_id"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["id"])
        ]

    youtube_id = models.CharField(
        max_length=16, unique=True, db_index=True)
    title = models.CharField(max_length=256, null=True)
    description = models.TextField(null=True)
    added_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    yt_published_date = models.DateTimeField(null=True)
    categories = models.ManyToManyField(Category)
    excluded = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag)
    uploader = models.CharField(max_length=256, null=True)
    channel_id = models.CharField(max_length=256, null=True)
    duration = models.CharField(max_length=256, null=True)
    full_response = models.TextField(null=True)
    transcript = models.TextField(null=True)
    thumbnail = models.FileField(null=True)
    slug = models.SlugField(unique=True, max_length=4096,
                            null=True, db_index=True)
    published_date = models.DateTimeField(null=True)
    view_count = models.IntegerField(null=True)
    like_count = models.IntegerField(null=True)
    dislike_count = models.IntegerField(null=True)
    favorite_count = models.IntegerField(null=True)
    comment_count = models.IntegerField(null=True)
    definition = models.CharField(max_length=256, null=True)

    def __str__(self):
        return str(self.youtube_id) + " - " + str(self.title)

    def set_tags(self, tags):
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(name=tag)
            self.tags.add(tag_obj)

    def save(self, *args, **kwargs):
        if not self.is_dirty():
            return
        if not self.slug and self.title:
            self.slug = uuslug(self.title, instance=self)
        super(Video, self).save(*args, **kwargs)
        logger.debug("SAVED video: " + str(self))

    @property
    def thumbnails(self):
        if not self.full_response:
            return None
        full_response = json.loads(self.full_response)
        if "thumbnails" in full_response:
            return full_response["thumbnails"]
        return None

    @property
    def description_trimmed(self):
        # leave part of description specific to this video:
        match = re.search(
            settings.TRUNCATE_DESCRIPTION_AFTER, self.description)
        if match and match.start() != -1:
            return self.description[:match.start()]

        return self.description

    def load_from_youtube_info(self, info):
        from django.utils.dateparse import parse_datetime
        self.title = info["title"]
        self.description = info["description"]
        self.uploader = info["channelTitle"]
        self.channel_id = info["channelId"]
        self.yt_published_date = parse_datetime(
            info["publishedAt"])
        self.view_count = int(info.get("viewCount", 0))
        self.like_count = int(info.get("likeCount", 0))
        self.dislike_count = int(info.get("dislikeCount", 0))
        self.favorite_count = int(info.get("favoriteCount", 0))
        self.comment_count = int(info.get("commentCount", 0))
        self.definition = info["definition"]
        self.duration = info["duration"]

        if "tags" in info:
            self.set_tags(info["tags"])
        self.full_response = json.dumps(info)


class Publication(models.Model):
    video = models.OneToOneField(
        Video,
        on_delete=models.CASCADE,
        primary_key=True)
    published_date = models.DateTimeField(null=True)
    post_id = models.IntegerField(null=True)
    thumbnail_id = models.IntegerField(null=True)
