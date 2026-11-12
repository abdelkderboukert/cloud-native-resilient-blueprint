"""
Kubernetes Health and Readiness Probes View Handlers
"""

import logging
from django.db import connection
from django.http import JsonResponse, HttpResponse
from django.views import View
from apps.core.kafka_producer import kafka_producer

logger = logging.getLogger(__name__)


class HealthCheckView(View):
    """
    Kubernetes Liveness Probe (/healthz).
    Returns 200 OK if the Django application process is alive.
    """

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            "status": "healthy",
            "service": "django-enterprise-api",
            "tier": "app-tier",
        }, status=200)


class ReadinessCheckView(View):
    """
    Kubernetes Readiness Probe (/readyz).
    Verifies that the application can service client traffic by checking:
    1. PostgreSQL database connectivity (CNPG primary)
    2. Kafka broker availability (Event Streaming)
    """

    def get(self, request, *args, **kwargs):
        checks = {
            "database": False,
            "kafka": False,
        }

        # 1. Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
                if row and row[0] == 1:
                    checks["database"] = True
        except Exception as exc:
            logger.error("Readiness check: Database check failed: %s", exc)
            checks["database"] = False

        # 2. Kafka check
        try:
            checks["kafka"] = kafka_producer.check_connection()
        except Exception as exc:
            logger.warning("Readiness check: Kafka check failed: %s", exc)
            checks["kafka"] = False

        # Determine overall readiness
        all_ready = checks["database"] and checks["kafka"]
        http_status = 200 if all_ready else 503

        return JsonResponse({
            "status": "ready" if all_ready else "degraded",
            "service": "django-enterprise-api",
            "checks": checks,
        }, status=http_status)


class MetricsView(View):
    """
    Prometheus Telemetry Endpoint (/metrics).
    Outputs operational metrics in Prometheus exposition format.
    """

    def get(self, request, *args, **kwargs):
        events_published = len(kafka_producer.get_published_events())
        db_status = 1
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
        except Exception:
            db_status = 0

        kafka_status = 1 if kafka_producer.check_connection() else 0

        metrics = [
            "# HELP django_http_service_info Information about the Django microservice",
            "# TYPE django_http_service_info gauge",
            'django_http_service_info{service="django-enterprise-api",tier="app-tier",version="1.0.0"} 1',
            "",
            "# HELP enterprise_db_connected Database connectivity state (1 = connected, 0 = disconnected)",
            "# TYPE enterprise_db_connected gauge",
            f"enterprise_db_connected {db_status}",
            "",
            "# HELP enterprise_kafka_connected Kafka connectivity state (1 = connected, 0 = disconnected)",
            "# TYPE enterprise_kafka_connected gauge",
            f"enterprise_kafka_connected {kafka_status}",
            "",
            "# HELP enterprise_events_published_total Total lifecycle events published since startup",
            "# TYPE enterprise_events_published_total counter",
            f"enterprise_events_published_total {events_published}",
            "",
        ]

        return HttpResponse("\n".join(metrics), content_type="text/plain; version=0.0.4; charset=utf-8")
