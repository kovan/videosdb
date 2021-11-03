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

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = uuslug(self.name, instance=self)

        super(Tag, self).save(*args, **kwargs)
        logger.debug("SAVED tag: " + str(self))


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
        return cls(youtube_id=yt_data["id"], yt_data=yt_data)

    def __str__(self):
        return str(self.youtube_id)

    def set_tags(self, tags):
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(name=tag.lower())
            self.tags.add(tag_obj)
            if created:
                logger.debug("Discovered tag: " + str(self))

    def save(self, *args, **kwargs):
        if not self.slug and self.yt_data["title"]:
            self.slug = uuslug(self.yt_data["title"], instance=self)
        super(Video, self).save(*args, **kwargs)
        logger.debug("Saved video: " + str(self))

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
        return cls(youtube_id=yt_data["id"], yt_data=yt_data)

    def __str__(self):
        return self.youtube_id

    def save(self, *args, **kwargs):
        if not self.slug and self.yt_data["title"]:
            self.slug = uuslug(self.yt_data["title"], instance=self)
        super(Playlist, self).save(*args, **kwargs)
        logger.debug("SAVED Playlist: " + str(self))
