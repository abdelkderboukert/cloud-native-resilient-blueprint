"""Article API endpoints and event publishing."""

from datetime import datetime, timezone
from django.conf import settings
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.articles.models import Article
from apps.articles.serializers import ArticleSerializer
from apps.core.kafka_producer import kafka_producer


def _cache_article_read(view_method):
    if not settings.API_CACHE_ENABLED or settings.API_CACHE_TTL <= 0:
        return view_method
    return method_decorator(
        cache_page(settings.API_CACHE_TTL, key_prefix="articles")
    )(view_method)


class ArticleViewSet(viewsets.ModelViewSet):
    """Provide article CRUD operations and publish lifecycle events."""

    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    @_cache_article_read
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @_cache_article_read
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        article = serializer.save()
        cache.clear()
        kafka_producer.publish_article_event(
            event_type="article.created",
            article_data=ArticleSerializer(article).data,
        )

    def perform_update(self, serializer):
        article = serializer.save()
        cache.clear()
        kafka_producer.publish_article_event(
            event_type="article.updated",
            article_data=ArticleSerializer(article).data,
        )

    def perform_destroy(self, instance):
        article_id = str(instance.id)
        article_data = {"id": article_id, "title": instance.title, "status": "deleted"}
        instance.delete()
        cache.clear()
        kafka_producer.publish_article_event(
            event_type="article.deleted",
            article_data=article_data,
        )

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        """Transition an article from draft to published."""
        article = self.get_object()
        article.status = Article.STATUS_PUBLISHED
        article.published_at = datetime.now(timezone.utc)
        article.save()
        cache.clear()

        serialized = ArticleSerializer(article).data
        kafka_producer.publish_article_event(
            event_type="article.published",
            article_data=serialized,
        )
        return Response(serialized, status=status.HTTP_200_OK)
