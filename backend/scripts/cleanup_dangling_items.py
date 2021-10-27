import logging
from videosdb.models import Tag, Playlist
import os

from django.conf import settings


def run():
    for tag in Tag.objects.all():
        if tag.video_set.count() == 0:
            tag.delete()
    for cat in Playlist.objects.all():
        if cat.video_set.count() == 0:
            cat.delete()
