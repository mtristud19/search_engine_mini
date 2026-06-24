from rest_framework import serializers
from .models import Document, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class DocumentSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )

    class Meta:
        model = Document
        fields = [
            "id", "title", "content", "category", "category_id",
            "tags", "author", "is_published", "view_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "view_count", "created_at", "updated_at"]


class SearchResultSerializer(serializers.Serializer):
    """Serializer cho kết quả trả về từ Elasticsearch (không qua ORM)."""

    id = serializers.CharField()
    title = serializers.CharField()
    snippet = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    tags = serializers.ListField(child=serializers.CharField())
    score = serializers.FloatField()
