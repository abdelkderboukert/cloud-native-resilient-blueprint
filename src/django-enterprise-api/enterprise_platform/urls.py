"""
Enterprise Event-Driven Micro-Platform URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from apps.core.health import HealthCheckView, ReadinessCheckView, MetricsView

urlpatterns = [
    # Health and metrics endpoints
    path("healthz/", HealthCheckView.as_view(), name="healthz"),
    path("readyz/", ReadinessCheckView.as_view(), name="readyz"),
    path("metrics/", MetricsView.as_view(), name="metrics"),

    # Admin site
    path("admin/", admin.site.urls),

    # API v1 routes
    path("api/v1/articles/", include("apps.articles.urls")),
    path("api/v1/users/", include("apps.users.urls")),
]
