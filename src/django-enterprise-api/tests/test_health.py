from django.test import TestCase, Client
from django.urls import reverse
from apps.core.kafka_producer import kafka_producer


class HealthCheckTests(TestCase):
    def setUp(self):
        self.client = Client()
        kafka_producer._test_mode = True

    def test_healthz_liveness_probe(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["tier"], "app-tier")

    def test_readyz_readiness_probe(self):
        response = self.client.get(reverse("readyz"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["checks"]["database"])
        self.assertTrue(data["checks"]["kafka"])

    def test_metrics_probe(self):
        response = self.client.get(reverse("metrics"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("enterprise_db_connected 1", content)
        self.assertIn("enterprise_events_published_total", content)
