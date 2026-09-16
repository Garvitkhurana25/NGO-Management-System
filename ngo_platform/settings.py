"""
Django settings for the NGO Operations Management Platform.

Configuration is read from environment variables (optionally via a .env file).
See .env.example for the full list of supported variables and defaults.
"""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is optional: without it, rely on real environment variables.
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

# Make the apps/ directory importable so apps are referenced as top-level
# packages ("core", "payments", "reports") rather than "apps.core", etc.
APPS_DIR = BASE_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
).split(",")

# Vite dev server origin(s). The browser's Origin header (http://localhost:5174
# or :5173) reaches Django through the dev proxy on unsafe methods (PATCH/POST/
# DELETE); CSRF now requires it to match a trusted origin. Covers the default
# port and the ports Vite falls back to when the default is taken.
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
    "http://localhost:5176", "http://localhost:5177", "http://localhost:5178",
    "http://localhost:5179", "http://localhost:5180",
    "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175",
    "http://127.0.0.1:5176", "http://127.0.0.1:5177", "http://127.0.0.1:5178",
    "http://127.0.0.1:5179", "http://127.0.0.1:5180",
]

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Project apps
    "core.apps.CoreConfig",
    "payments.apps.PaymentsConfig",
    "reports.apps.ReportsConfig",
    "api.apps.ApiConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ngo_platform.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "ngo_platform.wsgi.application"
ASGI_APPLICATION = "ngo_platform.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Default is SQLite (zero-setup, ideal for a scaffold / single instance).
# For Supabase (PostgreSQL) set the DJANGO_DB_* vars in .env — see .env.example
# for the exact set. The short engine name "postgresql" is expanded to Django's
# full backend path below.
DB_ENGINE = os.environ.get("DJANGO_DB_ENGINE", "django.db.backends.sqlite3")
if DB_ENGINE == "postgresql":
    DB_ENGINE = "django.db.backends.postgresql"

DATABASES = {
    "default": {
        "ENGINE": DB_ENGINE,
        "NAME": os.environ.get("DJANGO_DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.environ.get("DJANGO_DB_USER", ""),
        "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", ""),
        "HOST": os.environ.get("DJANGO_DB_HOST", ""),
        "PORT": os.environ.get("DJANGO_DB_PORT", ""),
    }
}

# Supabase (and managed Postgres generally) requires TLS on external
# connections; "require" is safe for any Postgres-compatible host.
if DB_ENGINE.endswith("postgresql"):
    DATABASES["default"]["OPTIONS"] = {
        "sslmode": os.environ.get("DJANGO_DB_SSLMODE", "require"),
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth & passwords
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "admin:login"
LOGIN_REDIRECT_URL = "admin:index"

# ---------------------------------------------------------------------------
# i18n / timezone
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Razorpay
# ---------------------------------------------------------------------------
# Razorpay works in paise (1 INR = 100 paise). Amounts are stored in the DB as
# INR decimals and converted to paise only at the gateway boundary.
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
# Relative URL prefix under which a webhook endpoint is mounted. Only used by
# the local dev server (ngrok/cloudflared) forwarding; set to the public base
# URL when deploying. e.g. "https://your-domain.example"
RAZORPAY_WEBHOOK_BASE_URL = os.environ.get("RAZORPAY_WEBHOOK_BASE_URL", "")

# Currency used for all donations in this instance.
DONATION_CURRENCY = os.environ.get("DONATION_CURRENCY", "INR")

# Default reply-to / from address embedded in automated acknowledgement emails.
DONATION_ACK_FROM_EMAIL = os.environ.get("DONATION_ACK_FROM_EMAIL", "")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "payments": {"level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"), "handlers": ["console"], "propagate": False},
        "core": {"level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"), "handlers": ["console"], "propagate": False},
    },
}