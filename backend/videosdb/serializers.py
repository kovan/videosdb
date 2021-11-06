from rest_framework import serializers

from .models import Playlist, Tag, Video, PersistentVideoData

VIDEO_FIELDS = ["id", "youtube_id", "yt_data",
                "categories", "tags", "duration_seconds",
                "slug",
                "description_trimmed", "related_videos"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        lookup_field = "slug"
        fields = ["id", "name", "slug"]


class PlaylistSerializer(serializers.ModelSerializer):
    use_count = serializers.IntegerField(read_only=True)
    last_updated = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Playlist
        lookup_field = "slug"
        fields = ["id", "youtube_id", "yt_data",
                  "slug", "use_count",  "last_updated"]


class RelatedVideoSrializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = VIDEO_FIELDS


class VideoSerializer(serializers.ModelSerializer):
    thumbnails = serializers.ListSerializer
    categories = PlaylistSerializer(
        many=True, read_only=True)
    tags = TagSerializer(
        many=True, read_only=True)
    related_videos = RelatedVideoSrializer(
        many=True, read_only=True)

    class Meta:
        model = Video
        lookup_field = "slug"
        fields = VIDEO_FIELDS


class VideoListSerializer(serializers.ModelSerializer):
    thumbnails = serializers.ListSerializer

    class Meta:
        model = Video
        lookup_field = "slug"
        fields = VIDEO_FIELDS


class PersistentVideoDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersistentVideoData
        fields = ["filename", "ipfs_hash",  "transcript", "youtube_id"]
