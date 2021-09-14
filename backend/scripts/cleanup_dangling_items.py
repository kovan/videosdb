import logging
from videosdb.models import Tag, Category
import os

from django.conf import settings


def run():
    for tag in Tag.objects.all():
        if tag.video_set.count() == 0:
            tag.delete()
    for cat in Category.objects.all():
        if cat.video_set.count() == 0:
            cat.delete()
