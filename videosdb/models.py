from uuslug import uuslug
from django.db import models
# Import slugify to generate slugs from strings
from django.utils.text import slugify


class Tag(models.Model):
    name = models.CharField(unique=True, max_length=256)
    slug = models.SlugField(unique=True, max_length=256,
                            null=True, db_index=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)
        super(Tag, self).save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField(unique=True, max_length=256)
    slug = models.SlugField(unique=True, max_length=256,
                            null=True, db_index=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)
        super(Category, self).save(*args, **kwargs)


class Video(models.Model):
    youtube_id = models.CharField(max_length=16, unique=True, db_index=True)
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
        return self.youtube_id + " - " + self.title

    def set_tags(self, tags):
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(name=tag)
            self.tags.add(tag_obj)
        self.save()

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = uuslug(self.title, instance=self)
        super(Video, self).save(*args, **kwargs)
