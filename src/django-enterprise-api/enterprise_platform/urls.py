"""
Enterprise Event-Driven Micro-Platform URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from apps.core.health import HealthCheckView, ReadinessCheckView, MetricsView

urlpatterns = [
    # Health and Telemetry Probes (Kubernetes Liveness / Readiness)
    path("healthz/", HealthCheckView.as_view(), name="healthz"),
    path("readyz/", ReadinessCheckView.as_view(), name="readyz"),
    path("metrics/", MetricsView.as_view(), name="metrics"),

    # Django Admin
    path("admin/", admin.site.urls),

    # Enterprise REST APIs (v1)
    path("api/v1/articles/", include("apps.articles.urls")),
    path("api/v1/users/", include("apps.users.urls")),
]
