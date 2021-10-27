import os
from datetime import date, timedelta

from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django.views.decorators.cache import never_cache
from django.db.models import Max

from rest_framework import filters, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response


from .models import Playlist, Tag, Video
from .serializers import VideoListSerializer, TagSerializer, PlaylistSerializer, VideoSerializer


@never_cache
@api_view(["GET"])
def random_video(request):
    video = Video.objects.all().order_by("?").first()
    serializer = VideoListSerializer(video)
    return Response(serializer.data)


@never_cache
@api_view(["GET"])
def version(request):
    return Response(os.environ.get("TAG"))


class AllowNoPaginationViewSet(viewsets.ReadOnlyModelViewSet):
    def paginate_queryset(self, queryset):
        if self.paginator and "no_pagination" in self.request.query_params:
            return None
        return super().paginate_queryset(queryset)


class TagViewSet(AllowNoPaginationViewSet):
    lookup_field = "slug"
    serializer_class = TagSerializer
    filter_backends = [filters.OrderingFilter,
                       DjangoFilterBackend,
                       filters.SearchFilter]
    ordering_fields = ["name"]
    search_fields = ["name"]
    queryset = Tag.objects.all()


class PlaylistViewSet(AllowNoPaginationViewSet):
    pagination_class = None
    lookup_field = "slug"
    serializer_class = PlaylistSerializer
    filter_backends = [filters.OrderingFilter,
                       DjangoFilterBackend,
                       filters.SearchFilter]
    ordering_fields = ["name", "use_count", "last_updated"]
    search_fields = ["name"]
    queryset = Playlist.objects.annotate(use_count=Count(
        "videos"), last_updated=Max("videos__yt_data__yt_data.publishedAt"))


class VideoViewSet(AllowNoPaginationViewSet):

    lookup_field = "slug"
    serializer_class = VideoSerializer
    filter_backends = [filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend]
    ordering_fields = ["yt_data.publishedAt", "view_count",
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
        queryset = Video.objects.all().order_by("-yt_data.publishedAt")
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

            queryset = queryset.filter(yt_data__publishedAt__range=[
                                       start_date, end_date])
        return queryset
