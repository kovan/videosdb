from uuslug import uuslug
from django.db import models
# Import slugify to generate slugs from strings
from django.utils.text import slugify 


class Tag(models.Model):
    name = models.CharField(unique=True, max_length=256)
    slug = models.SlugField(unique=True, null=True)
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)
        super(Tag, self).save(*args, **kwargs)

class Category(models.Model):
    name = models.CharField(unique=True, max_length=256)
    slug = models.SlugField(unique=True, null=True)
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)
        super(Category, self).save(*args, **kwargs)

class Video(models.Model):
    youtube_id = models.CharField(max_length=16, unique=True)
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
    duration = models.IntegerField(null=True)
    full_response = models.CharField(max_length=4096, null=True)
    transcript = models.TextField(null=True)
    thumbnail = models.FileField(null =True)

    def __str__(self):
        return self.youtube_id + " - " + self.title

    def set_tags(self, tags):
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(name=tag)
            self.tags.add(tag_obj)
        self.save()

class Publication(models.Model):
    video = models.OneToOneField(
            Video,
            on_delete = models.CASCADE,
            primary_key = True)
    published_date = models.DateTimeField(null=True)
    post_id = models.IntegerField(null=True)
    thumbnail_id = models.IntegerField(null=True)
    slug = models.SlugField(unique=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.video.title, instance=self)
        super(Publication, self).save(*args, **kwargs)
