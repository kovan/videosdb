from rest_framework import serializers
from rest_framework import viewsets
from .models import Tag, Category, Video, Publication

class TagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]

class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name","slug"]



class PublicationSerializer(serializers.HyperlinkedModelSerializer):
    title = serializers.CharField(source="video.title")
    youtube_id = serializers.CharField(source="video.youtube_id")
    description = serializers.CharField(source="video.description")
    thumbnail = serializers.CharField(source="video.thumbnail")
    yt_published_date = serializers.CharField(source="video.yt_published_date")
    class Meta:
        model = Publication
        fields = "__all__"



class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()



class PublicationViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationSerializer
    queryset = Publication.objects.all()
