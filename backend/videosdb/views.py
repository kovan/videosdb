from datetime import date, timedelta

from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Category, Tag, Video


@api_view(["GET"])
def random_video(request):
    video = Video.objects.filter(excluded=False).order_by("?").first()
    serializer = VideoListSerializer(video)
    return Response(serializer.data)


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
        fields = ["id", "youtube_id", "yt_published_date",
                  "categories", "tags", "duration_humanized", "transcript", "thumbnail",
                  "slug", "view_count", "dislike_count",
                  "favorite_count", "comment_count", "title", "thumbnails",
                  "description_trimmed", "filename", "ipfs_hash"]


class VideoListSerializer(serializers.ModelSerializer):
    thumbnails = serializers.ListSerializer

    class Meta:
        model = Video
        lookup_field = "slug"
        fields = ["id", "youtube_id", "yt_published_date",
                  "categories", "duration_humanized", "thumbnail",
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

    lookup_field = "slug"
    serializer_class = VideoSerializer
    filter_backends = [filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend]
    ordering_fields = ["yt_published_date", "view_count",
                       "comment_count", "favorited_count", "like_count", "title"]
    search_fields = ["title", "description",
                     "transcript", "tags__name", "categories__name"]
    filterset_fields = ["tags", "categories"]

    action_serializers = {
        'retrieve': VideoSerializer,
        'list': VideoListSerializer
    }

    def get_serializer_class(self):
        serializer_class = self.action_serializers.get(self.action, None)
        if not serializer_class:
            serializer_class = super().get_serializer_class()
        return serializer_class

    def get_queryset(self):
        queryset = Video.objects.exclude(excluded=True).exclude(title=None)
        period = self.request.query_params.get('period', None)
        if period:

            if period == "last_week":
                start_date = timezone.now() - timedelta(weeks=1)
            elif period == "last_month":
                start_date = timezone.now() - timedelta(weeks=4)
            elif period == "last_year":
                start_date = timezone.now() - timedelta(weeks=54)
            else:
                start_date = date(1, 1, 1)
            end_date = timezone.now() + timedelta(days=1)

            queryset = queryset.filter(yt_published_date__range=[
                                       start_date, end_date])
        return queryset
