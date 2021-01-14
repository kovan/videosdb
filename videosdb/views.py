from rest_framework import serializers
from rest_framework import viewsets
from .models import Tag, Category, Video


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        lookup_field = "slug"
        fields = ["id", "name", "slug"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        lookup_field = "slug"
        fields = ["id", "name", "slug"]


class VideoSerializer(serializers.ModelSerializer):
    thumbnails = serializers.ListSerializer

    class Meta:
        model = Video
        lookup_field = "slug"
        fields = ["id", "youtube_id", "description", "yt_published_date",
                  "categories", "tags", "duration", "transcript", "thumbnail",
                  "slug", "view_count", "dislike_count",
                  "favorite_count", "comment_count", "title", "thumbnails"]


class TagViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class CategoryViewSet(viewsets.ModelViewSet):
    pagination_class = None
    lookup_field = "slug"
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


class VideoViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    serializer_class = VideoSerializer
    queryset = Video.objects.filter(excluded=False)
