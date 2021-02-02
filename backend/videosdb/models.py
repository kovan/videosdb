import json
import logging
import re
import isodate

from dirtyfields import DirtyFieldsMixin
from django.conf import settings
from django.db import models
from django.db.models.fields import DateTimeField
from uuslug import uuslug

logger = logging.getLogger(__name__)


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
        if not self.slug and self.name:
            self.slug = uuslug(self.name, instance=self)
        if not self.is_dirty():
            return
        super(Tag, self).save(*args, **kwargs)


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
        if not self.slug and self.name:
            self.slug = uuslug(self.name, instance=self)
        if not self.is_dirty():
            return
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
    title = models.CharField(max_length=256, null=True,
                             help_text="title")
    description = models.TextField(null=True, help_text="description")
    added_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    yt_published_date = models.DateTimeField(
        null=True, help_text="publishedAt")
    categories = models.ManyToManyField(Category)
    excluded = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag)
    uploader = models.CharField(
        max_length=256, null=True, help_text="channelTitle")
    channel_id = models.CharField(
        max_length=256, null=True, help_text="channelId")
    duration = models.CharField(
        max_length=256, null=True, help_text="duration")
    full_response = models.TextField(null=True)
    transcript = models.TextField(null=True)
    transcript_available = models.BooleanField(null=True)
    thumbnail = models.FileField(null=True)
    slug = models.SlugField(unique=True, max_length=4096,
                            null=True, db_index=True)
    published_date = models.DateTimeField(null=True)
    view_count = models.IntegerField(
        null=True, help_text="viewCount")
    like_count = models.IntegerField(
        null=True, help_text="likeCount")
    dislike_count = models.IntegerField(
        null=True, help_text="dislikeCount")
    favorite_count = models.IntegerField(
        null=True, help_text="favoriteCount")
    comment_count = models.IntegerField(null=True, help_text="commentCount")
    definition = models.CharField(
        max_length=256, null=True, help_text="definition")
    related_videos = models.ManyToManyField("self")

    @staticmethod
    def list_fields_imported_from_yt():
        return [field for field in Video._meta.fields if field.help_text != ""]

    def is_missing_yt_info(self):
        values = [getattr(self, field.name)
                  for field in Video.list_fields_imported_from_yt()]

        for value in values:
            if value is None:
                return True
        return False

    def __str__(self):
        return str(self.youtube_id) + " - " + str(self.title)

    def set_tags(self, tags):
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(name=tag.lower())
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
            return dict()
        full_response = json.loads(self.full_response)
        if "thumbnails" in full_response:
            return full_response["thumbnails"]
        return dict()

    @property
    def description_trimmed(self):
        # leave part of description specific to this video:
        if not self.description:
            return None

        match = re.search(
            settings.TRUNCATE_DESCRIPTION_AFTER, self.description)
        if match and match.start() != -1:
            return self.description[:match.start()]

        return self.description

    @property
    def duration_humanized(self):
        return str(isodate.parse_duration(self.duration))

    def load_from_youtube_info(self, info):
        from django.utils.dateparse import parse_datetime

        for field in Video.list_fields_imported_from_yt():
            if type(field) == models.IntegerField:
                value = info.get(field.help_text, 0)
            elif type(field) == models.DateTimeField:
                value = parse_datetime(info.get(field.help_text))
            else:
                value = info.get(field.help_text)

            setattr(self, field.name, value)

        if "tags" in info:
            self.set_tags(info["tags"])

        self.full_response = json.dumps(info)
