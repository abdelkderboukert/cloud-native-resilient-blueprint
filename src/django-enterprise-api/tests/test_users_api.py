import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.core.kafka_producer import kafka_producer


class UserAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        kafka_producer._test_mode = True
        kafka_producer.clear_test_events()

    def test_user_registration_publishes_event(self):
        payload = {
            "username": "johndoe",
            "email": "johndoe@enterprise.local",
            "password": "StrongPassword123!",
            "tier": "enterprise",
            "department": "Platform Engineering",
        }
        response = self.client.post(
            "/api/v1/users/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["username"], "johndoe")

        # Verify profile creation
        user = User.objects.get(username="johndoe")
        self.assertEqual(user.profile.tier, "enterprise")
        self.assertEqual(user.profile.department, "Platform Engineering")

        # Verify Kafka event
        events = kafka_producer.get_published_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"]["type"], "user.registered")
        self.assertEqual(events[0]["event"]["data"]["username"], "johndoe")
