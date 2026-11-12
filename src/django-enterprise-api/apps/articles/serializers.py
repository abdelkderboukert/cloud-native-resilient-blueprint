"""
Article REST Serializers
"""

from rest_framework import serializers
from apps.articles.models import Article


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "author",
            "status",
            "created_at",
            "updated_at",
            "published_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at", "published_at"]
