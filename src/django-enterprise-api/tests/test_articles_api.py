import json
from django.test import TestCase, Client
from apps.articles.models import Article
from apps.core.kafka_producer import kafka_producer


class ArticleAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        kafka_producer._test_mode = True
        kafka_producer.clear_test_events()

    def test_create_article_publishes_event(self):
        payload = {
            "title": "Cloud-Native Microservices",
            "content": "Deep dive into Kubernetes and Kafka event streaming.",
            "author": "architect_lead",
        }
        response = self.client.post(
            "/api/v1/articles/",
            data=json.dumps(payload),
            content_type="application/json",
            headers={"X-Request-ID": "test-req-001"}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], payload["title"])
        self.assertEqual(data["status"], "draft")
        self.assertEqual(response.headers.get("X-Request-ID"), "test-req-001")

        # Verify Kafka event
        events = kafka_producer.get_published_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"]["type"], "article.created")
        self.assertEqual(events[0]["event"]["data"]["title"], payload["title"])

    def test_publish_article_action(self):
        article = Article.objects.create(
            title="Draft Specification",
            content="Initial thoughts.",
            author="engineer",
            status=Article.STATUS_DRAFT,
        )
        kafka_producer.clear_test_events()

        response = self.client.post(f"/api/v1/articles/{article.id}/publish/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "published")
        self.assertIsNotNone(data["published_at"])

        # Verify published event
        events = kafka_producer.get_published_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"]["type"], "article.published")
