import json
import logging
import re
import isodate

from django.conf import settings
from django.db import models
from django.db.models.fields import DateTimeField
from uuslug import uuslug

logger = logging.getLogger(__name__)


class Tag(models.Model):
    name = models.CharField(unique=True, max_length=256)
    slug = models.SlugField(unique=True, max_length=256,
                            null=True, db_index=True)

    def __str__(self):
        return self.name

    def create_slug(self):
        if self.slug:
            return
        self.slug = uuslug(self.name, instance=self)


class PersistentVideoData(models.Model):
    youtube_id = models.CharField(
        max_length=16, unique=True, db_index=True)
    # data that does not come from Youtube
    transcript = models.TextField(null=True)
    transcript_available = models.BooleanField(null=True)
    ipfs_hash = models.CharField(max_length=256, null=True)
    filename = models.CharField(max_length=256, null=True)


class Video(models.Model):

    # Here goes data that comes from Youtube only

    youtube_id = models.CharField(
        max_length=16, unique=True, db_index=True)
    yt_data = models.JSONField()
    slug = models.SlugField(unique=True, max_length=4096,
                            null=True, db_index=True)
    tags = models.ManyToManyField(Tag)
    related_videos = models.ManyToManyField(
        "self",  symmetrical=False)

    data = models.OneToOneField(
        PersistentVideoData, null=True, on_delete=models.SET_NULL)

    @classmethod
    def create(cls, yt_data):
        obj = cls(youtube_id=yt_data["id"], yt_data=yt_data)
        obj.slug = uuslug(yt_data["snippet"]["title"], instance=obj)
        return obj

    def __str__(self):
        return "Video " + str(self.youtube_id)

    def populate_tags(self):
        if not "tags" in self.yt_data["snippet"]:
            return
        for tag in self.yt_data["snippet"]["tags"]:
            tag_obj, created = Tag.objects.get_or_create(name=tag.lower())
            tag_obj.create_slug()
            tag_obj.save()
            self.tags.add(tag_obj)

    @property
    def description_trimmed(self):
        # leave part of description specific to this video:
        if not self.yt_data.description:
            return None

        match = re.search(
            settings.TRUNCATE_DESCRIPTION_AFTER, self.yt_data.description)

        if match and match.start() != -1:
            return self.yt_data.description[:match.start()]

        return self.yt_data.description

    @property
    def duration_seconds(self):
        return isodate.parse_duration(self.yt_data.duration).total_seconds()


class Playlist(models.Model):
    # Here goes data that comes from Youtube only
    youtube_id = models.CharField(
        max_length=256, unique=True, db_index=True)
    yt_data = models.JSONField()

    slug = models.SlugField(unique=True, max_length=256,
                            null=True, db_index=True)

    videos = models.ManyToManyField(Video)

    @classmethod
    def create(cls, yt_data):
        obj = cls(youtube_id=yt_data["id"], yt_data=yt_data)
        obj.slug = uuslug(yt_data["snippet"]["title"], instance=obj)
        return obj

    def __str__(self):
        return self.youtube_id

    def create_slug(self):
        if self.slug:
            return
        self.slug = uuslug(self.yt_data["snippet"]["title"], instance=self)

    def __str__(self):
        return "Playlist " + self.youtube_id
