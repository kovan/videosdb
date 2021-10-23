from rest_framework import serializers

from .models import Category, Tag, Video


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        lookup_field = "slug"
        fields = ["id", "name", "slug"]


class CategorySerializer(serializers.ModelSerializer):
    use_count = serializers.IntegerField(read_only=True)
    last_updated = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Category
        lookup_field = "slug"
        fields = ["id", "name", "slug", "use_count",  "last_updated"]


class RelatedVideoSrializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ["id", "youtube_id", "yt_published_date",
                  "duration_seconds", "title", "thumbnails", "slug"]


class VideoSerializer(serializers.ModelSerializer):
    thumbnails = serializers.ListSerializer
    categories = CategorySerializer(
        many=True, read_only=True)
    tags = TagSerializer(
        many=True, read_only=True)
    related_videos = RelatedVideoSrializer(
        many=True, read_only=True)

    class Meta:
        model = Video
        lookup_field = "slug"
        fields = ["id", "youtube_id", "yt_published_date",
                  "categories", "tags", "duration_seconds", "transcript", "thumbnail",
                  "slug", "view_count", "dislike_count", "duration",
                  "favorite_count", "comment_count", "title", "thumbnails",
                  "description_trimmed", "filename", "ipfs_hash", "related_videos"]


class VideoListSerializer(serializers.ModelSerializer):
    thumbnails = serializers.ListSerializer

    class Meta:
        model = Video
        lookup_field = "slug"
        fields = ["id", "youtube_id", "yt_published_date",
                  "duration_seconds", "thumbnail",
                  "slug", "view_count", "dislike_count",
                  "favorite_count", "comment_count", "title", "thumbnails",
                  "description_trimmed", "modified_date", "filename"]
