from rest_framework import serializers, viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Tag, Category, Video
from django.db.models import Count


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        lookup_field = "slug"
        fields = ["id", "name", "slug"]


class CategorySerializer(serializers.ModelSerializer):
    use_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        lookup_field = "slug"
        fields = ["id", "name", "slug", "use_count"]


class VideoSerializer(serializers.ModelSerializer):
    thumbnails = serializers.ListSerializer
    categories = CategorySerializer(
        many=True, read_only=True)
    tags = TagSerializer(
        many=True, read_only=True)

    class Meta:
        model = Video
        lookup_field = "slug"
        fields = ["id", "youtube_id", "description", "yt_published_date",
                  "categories", "tags", "duration", "transcript", "thumbnail",
                  "slug", "view_count", "dislike_count",
                  "favorite_count", "comment_count", "title", "thumbnails",
                  "description_trimmed"]


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"
    serializer_class = TagSerializer
    filter_backends = [filters.OrderingFilter,
                       DjangoFilterBackend,
                       filters.SearchFilter]
    ordering_fields = ["name"]
    search_fields = ["name"]
    queryset = Tag.objects.all()


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = None
    lookup_field = "slug"
    serializer_class = CategorySerializer
    filter_backends = [filters.OrderingFilter,
                       DjangoFilterBackend,
                       filters.SearchFilter]
    ordering_fields = ["name", "use_count"]
    search_fields = ["name"]
    queryset = Category.objects.annotate(use_count=Count("video"))


class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    ordering = ["-yt_published_date"]
    lookup_field = "slug"
    serializer_class = VideoSerializer
    filter_backends = [filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend]
    ordering_fields = ["yt_published_date", "view_count",
                       "comment_count", "favorited_count", "like_count"]
    search_fields = ["title", "description"]
    filterset_fields = ["tags", "categories"]
    queryset = Video.objects.exclude(excluded=True).exclude(title=None)
