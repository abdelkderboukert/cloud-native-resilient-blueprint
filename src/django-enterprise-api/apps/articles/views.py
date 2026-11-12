"""
Article API ViewSets with Asynchronous Event Streaming
"""

from datetime import datetime, timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.articles.models import Article
from apps.articles.serializers import ArticleSerializer
from apps.core.kafka_producer import kafka_producer


class ArticleViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Articles with asynchronous Kafka lifecycle event publishing:
    - article.created
    - article.updated
    - article.deleted
    - article.published
    """

    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def perform_create(self, serializer):
        article = serializer.save()
        # Asynchronously broadcast article.created event to Kafka
        kafka_producer.publish_article_event(
            event_type="article.created",
            article_data=ArticleSerializer(article).data,
        )

    def perform_update(self, serializer):
        article = serializer.save()
        # Asynchronously broadcast article.updated event to Kafka
        kafka_producer.publish_article_event(
            event_type="article.updated",
            article_data=ArticleSerializer(article).data,
        )

    def perform_destroy(self, instance):
        article_id = str(instance.id)
        article_data = {"id": article_id, "title": instance.title, "status": "deleted"}
        instance.delete()
        # Asynchronously broadcast article.deleted event to Kafka
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

        serialized = ArticleSerializer(article).data
        # Asynchronously broadcast article.published event to Kafka
        kafka_producer.publish_article_event(
            event_type="article.published",
            article_data=serialized,
        )
        return Response(serialized, status=status.HTTP_200_OK)
