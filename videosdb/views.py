from rest_framework import serializers, viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Tag, Category, Video


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        lookup_field = "slug"
        fields = ["id", "name", "slug",  "popularity"]


class CategorySerializer(serializers.ModelSerializer):
    popularity = serializers.SerializerMethodField()

    class Meta:
        model = Category
        lookup_field = "slug"
        fields = ["id", "name", "slug", "popularity"]

    def get_popularity(self, category):
        return category.video_set.count()


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


class TagViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    serializer_class = TagSerializer
    filter_backends = [filters.OrderingFilter,
                       DjangoFilterBackend,
                       filters.SearchFilter]
    ordering_fields = ["name", "popularity"]
    search_fields = ["name"]
    queryset = Tag.objects.all()


class CategoryViewSet(viewsets.ModelViewSet):
    pagination_class = None
    lookup_field = "slug"
    serializer_class = CategorySerializer
    filter_backends = [filters.OrderingFilter,
                       DjangoFilterBackend,
                       filters.SearchFilter]
    ordering_fields = ["name", "popularity"]
    search_fields = ["name"]
    queryset = Category.objects.all()


class VideoViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    serializer_class = VideoSerializer
    filter_backends = [filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend]
    ordering_fields = ["yt_published_date", "view_count",
                       "comment_count", "favorited_count", "like_count"]
    search_fields = ["title", "description"]
    filterset_fields = ["tags", "categories"]
    queryset = Video.objects.filter(excluded=False)
