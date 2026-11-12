import uuid
from django.test import TestCase
from apps.core.kafka_producer import EnterpriseKafkaProducer


class KafkaProducerUnitTests(TestCase):
    def setUp(self):
        self.producer = EnterpriseKafkaProducer()
        self.producer._test_mode = True
        self.producer.clear_test_events()

    def test_event_envelope_structure(self):
        payload = {"title": "Test Title", "status": "draft"}
        envelope = self.producer.publish_event(
            topic="test.topic",
            event_type="test.created",
            key="item-123",
            payload=payload,
        )

        self.assertEqual(envelope["specversion"], "1.0")
        self.assertEqual(envelope["type"], "test.created")
        self.assertEqual(envelope["data"], payload)
        self.assertTrue(uuid.UUID(envelope["id"]))
        self.assertTrue(uuid.UUID(envelope["correlation_id"]))
        self.assertIn("/enterprise/django-api/", envelope["source"])

    def test_article_event_publishing(self):
        article_data = {"id": str(uuid.uuid4()), "title": "Architecture Overview"}
        self.producer.publish_article_event("article.created", article_data)

        events = self.producer.get_published_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["topic"], "article.lifecycle.events")
        self.assertEqual(events[0]["event"]["type"], "article.created")
        self.assertEqual(events[0]["event"]["data"]["title"], "Architecture Overview")

    def test_user_event_publishing(self):
        user_data = {"id": 42, "username": "platform_admin"}
        self.producer.publish_user_event("user.registered", user_data)

        events = self.producer.get_published_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["topic"], "user.lifecycle.events")
        self.assertEqual(events[0]["key"], "42")
