import json
from django.core.cache import cache
from django.test import TestCase, Client
from apps.articles.models import Article
from apps.core.kafka_producer import kafka_producer


class ArticleAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
        kafka_producer._test_mode = True
        kafka_producer.clear_test_events()

    def test_article_reads_are_cached_and_writes_invalidate_cache(self):
        article = Article.objects.create(
            title="Cached Article",
            content="Original content",
            author="engineer",
            status=Article.STATUS_DRAFT,
        )

        response = self.client.get("/api/v1/articles/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["title"], "Cached Article")

        with self.assertNumQueries(0):
            cached_response = self.client.get("/api/v1/articles/")
        self.assertEqual(cached_response.json()["results"][0]["title"], "Cached Article")

        response = self.client.patch(
            f"/api/v1/articles/{article.id}/",
            data=json.dumps({"title": "Updated Article"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/v1/articles/")
        self.assertEqual(response.json()["results"][0]["title"], "Updated Article")

        detail_url = f"/api/v1/articles/{article.id}/"
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.json()["title"], "Updated Article")
        with self.assertNumQueries(0):
            cached_detail = self.client.get(detail_url)
        self.assertEqual(cached_detail.json()["title"], "Updated Article")

        response = self.client.patch(
            detail_url,
            data=json.dumps({"content": "Updated content"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.json()["content"], "Updated content")

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
