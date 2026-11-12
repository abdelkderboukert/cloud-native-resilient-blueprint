"""
Enterprise Event-Driven Micro-Platform (EEMP)
Django Settings Configuration
"""

import os
from pathlib import Path
from urllib.parse import urlparse, unquote

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security configuration
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    os.getenv(
        "DJANGO_SECRET_KEY",
        "django-insecure-development-key-replace-in-production-vault"
    ),
)

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

allowed_hosts_raw = os.getenv(
    "ALLOWED_HOSTS",
    "api.enterprise.local,django-service,django-service.app-tier.svc.cluster.local,localhost,127.0.0.1,*"
)
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(",") if host.strip()]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "corsheaders",
    # Platform tier domain apps
    "apps.core.apps.CoreConfig",
    "apps.articles.apps.ArticlesConfig",
    "apps.users.apps.UsersConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.core.middleware.CorrelationIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "enterprise_platform.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "enterprise_platform.wsgi.application"
ASGI_APPLICATION = "enterprise_platform.asgi.application"

# Helper function to parse database URLs safely
def parse_db_url(url: str):
    if not url or "sqlite" in url or os.getenv("USE_SQLITE", "False").lower() in ("true", "1"):
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    parsed = urlparse(url)
    engine = "django.db.backends.postgresql"
    database = parsed.path.lstrip("/")
    user = unquote(parsed.username) if parsed.username else ""
    password = unquote(parsed.password) if parsed.password else ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    return {
        "ENGINE": engine,
        "NAME": database,
        "USER": user,
        "PASSWORD": password,
        "HOST": host,
        "PORT": port,
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
    }

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgres://app_user:secure_password@postgres-cluster-rw.data-tier.svc.cluster.local:5432/enterprise_db"
)

# In test runners or local development without postgres running, allow fallback
if os.getenv("DJANGO_TESTING") == "1" or os.getenv("USE_SQLITE", "False").lower() in ("true", "1"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    try:
        import dj_database_url
        DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, conn_health_checks=True)}
    except ImportError:
        DATABASES = {"default": parse_db_url(DATABASE_URL)}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

API_CACHE_TTL = int(os.getenv("API_CACHE_TTL", "60"))
API_CACHE_ENABLED = os.getenv("API_CACHE_ENABLED", "True").lower() in ("true", "1", "yes")
REDIS_URL = os.getenv("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": (
            "django_redis.cache.RedisCache"
            if REDIS_URL
            else "django.core.cache.backends.locmem.LocMemCache"
        ),
        "LOCATION": REDIS_URL or "enterprise-platform-api",
        "TIMEOUT": API_CACHE_TTL,
        "OPTIONS": (
            {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
                "DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS": True,
            }
            if REDIS_URL
            else {}
        ),
    }
}

# Django REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
}

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka-broker-0.kafka-headless.messaging-tier.svc.cluster.local:9092"
)
KAFKA_USER_EVENTS_TOPIC = os.getenv("KAFKA_USER_EVENTS_TOPIC", "user.lifecycle.events")
KAFKA_ARTICLE_EVENTS_TOPIC = os.getenv("KAFKA_ARTICLE_EVENTS_TOPIC", "article.lifecycle.events")
KAFKA_CLIENT_ID = os.getenv("KAFKA_CLIENT_ID", "django-enterprise-api")
KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "True").lower() in ("true", "1", "yes")

# CORS
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "False").lower() in ("true", "1", "yes")
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://api.enterprise.local",
    "https://api.enterprise.local",
]

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

try:
    import pythonjsonlogger
    formatter_config = {
        "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
        "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(message)s %(request_id)s",
    }
except ImportError:
    formatter_config = {
        "format": "[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "app_formatter": formatter_config,
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "app_formatter",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
