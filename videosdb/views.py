from rest_framework import serializers
from rest_framework import viewsets
from .models import Tag, Category, Video


class TagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Tag
        lookup_field = "slug"
        fields = ["id", "name", "slug"]


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        lookup_field = "slug"
        fields = ["id", "name", "slug"]


class TagViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class CategoryViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
