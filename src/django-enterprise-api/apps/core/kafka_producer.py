"""Publish lifecycle events to Kafka."""

import json
import logging
import os
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from django.conf import settings
from apps.core.middleware import get_current_request_id

logger = logging.getLogger(__name__)


class EnterpriseKafkaProducer:
    """Publish lifecycle events and retain a local copy for fallback and tests."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._producer = None
        self._is_connected = False
        self._test_mode = os.getenv("KAFKA_TEST_MODE", "False").lower() in ("true", "1")
        self._published_events = []  # In-memory buffer for testing and fallback
        self._lock = threading.Lock()
        self._initialized = True

    def _get_producer(self):
        """Lazy-initialize the Kafka producer client."""
        if not settings.KAFKA_ENABLED or self._test_mode:
            return None

        if self._producer is not None:
            return self._producer

        try:
            from kafka import KafkaProducer

            bootstrap_servers = [
                s.strip()
                for s in settings.KAFKA_BOOTSTRAP_SERVERS.split(",")
                if s.strip()
            ]

            self._producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                client_id=getattr(settings, "KAFKA_CLIENT_ID", "django-enterprise-api"),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                retries=3,
                request_timeout_ms=5000,
                max_block_ms=3000,
                acks=1,
            )
            self._is_connected = True
            logger.info("Connected to Kafka cluster at %s", bootstrap_servers)
            return self._producer
        except Exception as exc:
            self._is_connected = False
            logger.warning("Kafka producer unavailable (%s). Falling back to resilient buffer.", exc)
            return None

    def publish_event(self, topic: str, event_type: str, key: str, payload: dict) -> dict:
        """
        Publish an enterprise lifecycle event wrapped with cloud-native envelope metadata.
        """
        event_id = str(uuid.uuid4())
        correlation_id = get_current_request_id() or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        envelope = {
            "specversion": "1.0",
            "id": event_id,
            "source": f"/enterprise/django-api/{socket.gethostname()}",
            "type": event_type,
            "time": now,
            "datacontenttype": "application/json",
            "correlation_id": correlation_id,
            "data": payload,
        }

        with self._lock:
            self._published_events.append({
                "topic": topic,
                "key": key,
                "event": envelope,
            })

        producer = self._get_producer()
        if producer is not None:
            try:
                future = producer.send(topic, key=key, value=envelope)
                logger.info(
                    "Published event %s [%s] to topic %s with key %s",
                    event_id, event_type, topic, key
                )
            except Exception as exc:
                logger.error(
                    "Failed to deliver event %s to topic %s: %s",
                    event_id, topic, exc
                )
        else:
            logger.debug(
                "Simulated publish event %s [%s] to topic %s (mock/fallback mode)",
                event_id, event_type, topic
            )

        return envelope

    def publish_article_event(self, event_type: str, article_data: dict) -> dict:
        """Publish article lifecycle telemetry event."""
        topic = getattr(settings, "KAFKA_ARTICLE_EVENTS_TOPIC", "article.lifecycle.events")
        key = str(article_data.get("id", ""))
        return self.publish_event(topic, event_type, key, article_data)

    def publish_user_event(self, event_type: str, user_data: dict) -> dict:
        """Publish user lifecycle telemetry event."""
        topic = getattr(settings, "KAFKA_USER_EVENTS_TOPIC", "user.lifecycle.events")
        key = str(user_data.get("id", user_data.get("username", "")))
        return self.publish_event(topic, event_type, key, user_data)

    def check_connection(self) -> bool:
        """Verify broker connectivity for Kubernetes readiness probe."""
        if self._test_mode or not getattr(settings, "KAFKA_ENABLED", True):
            return True

        producer = self._get_producer()
        if producer is not None:
            return True

        # Check the broker socket if the producer could not connect.
        try:
            servers = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")
            first_host_port = servers[0].strip().split(":")
            host = first_host_port[0]
            port = int(first_host_port[1]) if len(first_host_port) > 1 else 9092
            with socket.create_connection((host, port), timeout=2.0):
                return True
        except Exception:
            return False

    def get_published_events(self):
        """Retrieve buffer of published events (useful for verification and tests)."""
        with self._lock:
            return list(self._published_events)

    def clear_test_events(self):
        """Clear test event buffer."""
        with self._lock:
            self._published_events.clear()


kafka_producer = EnterpriseKafkaProducer()
