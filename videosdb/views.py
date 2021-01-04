from rest_framework import serializers
from rest_framework import viewsets
from .models import Tag, Category, Video, Publication

class TagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Tag
        lookup_field = "slug"
        fields = ["id", "name", "slug"]

class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        lookup_field = "slug"
        fields = ["id", "name","slug"]



class PublicationSerializer(serializers.HyperlinkedModelSerializer):
    title = serializers.CharField(source="video.title")
    youtube_id = serializers.CharField(source="video.youtube_id")
    description = serializers.CharField(source="video.description")
    thumbnail = serializers.CharField(source="video.thumbnail")
    yt_published_date = serializers.CharField(source="video.yt_published_date")
    class Meta:
        model = Publication
        lookup_field = "slug"
        fields = ["title", "youtube_id", "description", "thumbnail", "yt_published_date", "slug"] #"__all__"



class TagViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class CategoryViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    serializer_class = CategorySerializer
    queryset = Category.objects.all()



class PublicationViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    serializer_class = PublicationSerializer
    queryset = Publication.objects.all()
