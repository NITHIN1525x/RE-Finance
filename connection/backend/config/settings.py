"""Django settings for the QBO Connection Console (local sandbox demo).

Secrets come from environment variables, falling back to connection/.secrets/backend.env.
Nothing secret is defined in this file.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .envfile import load_env_file

BASE_DIR = Path(__file__).resolve().parent.parent            # connection/backend
SECRETS_DIR = BASE_DIR.parent / ".secrets"                     # connection/.secrets (owner-only)
ENV_FILE = Path(os.environ.get("QBO_BACKEND_ENV_FILE", SECRETS_DIR / "backend.env"))
load_env_file(ENV_FILE)


def required(name):
    value = os.environ.get(name, "")
    if not value:
        raise ImproperlyConfigured(f"{name} is not set (expected in {ENV_FILE} or the environment)")
    return value


SECRET_KEY = required("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# --- QuickBooks / Intuit ------------------------------------------------------------------
# Hard sandbox guard, part 1: refuse to start in any other environment. Part 2 is the API host
# allow-list in qbo/intuit.py; part 3 is the post-connect CompanyInfo check on the sandbox host.
QUICKBOOKS_ENVIRONMENT = os.environ.get("QUICKBOOKS_ENVIRONMENT", "sandbox")
if QUICKBOOKS_ENVIRONMENT != "sandbox":
    raise ImproperlyConfigured("QUICKBOOKS_ENVIRONMENT must be exactly 'sandbox'; production is refused by design")
FERNET_KEY = required("FERNET_KEY")
QUICKBOOKS_CLIENT_ID = os.environ.get("QUICKBOOKS_CLIENT_ID", "")          # may be empty until configured
QUICKBOOKS_CLIENT_SECRET = os.environ.get("QUICKBOOKS_CLIENT_SECRET", "")
QUICKBOOKS_REDIRECT_URI = os.environ.get("QUICKBOOKS_REDIRECT_URI", "http://localhost:8000/api/qbo/callback")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Token store the official MCP server reads via QUICKBOOKS_TOKEN_STORE_PATH (see DECISIONS_LOG D-08).
MCP_TOKEN_STORE_PATH = Path(os.environ.get("MCP_TOKEN_STORE_PATH", SECRETS_DIR / "mcp-server.env"))

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "qbo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# SQLite lives in the owner-only secrets dir: it holds encrypted tokens and the audit log.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", SECRETS_DIR / "db.sqlite3"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/api/auth/login/"
LOGIN_REDIRECT_URL = FRONTEND_URL + "/"
LOGOUT_REDIRECT_URL = LOGIN_URL

# Session cookie: HttpOnly (default) and SameSite=Lax so it is sent on the top-level redirect back
# from Intuit to /api/qbo/callback. Cookies are not port-scoped, so the Vite origin (:5173) and
# Django (:8000) share it on localhost.
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 8 * 60 * 60
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL]

# The Vite dev proxy makes /api same-origin; CORS is only for running the UI without the proxy.
CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],   # no browsable API
    "UNAUTHENTICATED_USER": None,
}

# runserver logs every request line, including the OAuth callback's ?code=&state=&realmId=.
# The filter redacts those values so authorization codes and full realm IDs never reach the console.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact_oauth": {"()": "qbo.logging_filters.RedactOAuthParams"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "filters": ["redact_oauth"]}},
    "loggers": {
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "qbo": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
