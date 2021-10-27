from django.contrib import admin

# Register your models here.
from .models import Video, Tag, Playlist

admin.site.register(Video)
admin.site.register(Tag)
admin.site.register(Playlist)
