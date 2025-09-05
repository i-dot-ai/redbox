# mypy: ignore-errors
import logging
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import environ
import sentry_sdk
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from import_export.formats.base_formats import CSV
from sentry_sdk.integrations.django import DjangoIntegration
from storages.backends import s3boto3
from yarl import URL

from redbox_app.setting_enums import Classification, Environment

logger = logging.getLogger(__name__)


load_dotenv()

env = environ.Env()

ALLOW_SIGN_UPS = env.bool("ALLOW_SIGN_UPS")

SECRET_KEY = env.str("DJANGO_SECRET_KEY")
ENVIRONMENT = Environment[env.str("ENVIRONMENT").upper()]
WEBSOCKET_SCHEME = "ws" if ENVIRONMENT.is_test else "wss"
LOGIN_METHOD = env.str("LOGIN_METHOD", None)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG")

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_URL = "static/"
STATIC_ROOT = "staticfiles/"
STATICFILES_DIRS = [
    Path(BASE_DIR) / "static/",
    Path(BASE_DIR) / "frontend/dist/",
]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]


SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Application definition
INSTALLED_APPS = [
    "daphne",
    "redbox_app.redbox_core",
    "django.contrib.admin.apps.SimpleAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "single_session",
    "storages",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.openid_connect",
    "import_export",
    "django_q",
    "rest_framework",
    "adminplus",
    "waffle",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_permissions_policy.PermissionsPolicyMiddleware",
    "csp.middleware.CSPMiddleware",
    "redbox_app.redbox_core.middleware.nocache_middleware",
    "redbox_app.redbox_core.middleware.security_header_middleware",
    "waffle.middleware.WaffleMiddleware",
]

ROOT_URLCONF = "redbox_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [
            BASE_DIR / "redbox_app" / "templates",
            BASE_DIR / "redbox_app" / "templates" / "auth",
        ],
        "OPTIONS": {
            "environment": "redbox_app.jinja2.environment",
        },
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "redbox_app" / "templates",
        ],
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

WSGI_APPLICATION = "redbox_app.wsgi.application"
ASGI_APPLICATION = "redbox_app.asgi.application"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 10,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-GB"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1
AUTH_USER_MODEL = "redbox_core.User"

# OAuth2 Settings
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "homepage"
LOGOUT_REDIRECT_URL = "/"

# Allauth Settings
ACCOUNT_EMAIL_VERIFICATION = "none"

# Social Account Settings
SOCIALACCOUNT_ONLY = True
SOCIALACCOUNT_LOGIN_ON_GET = True

SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "APPS": [
            {
                "provider_id": "gds",
                "name": "GDS Internal Access",
                "client_id": env.str("SOCIAL_AUTH_OIDC_KEY"),
                "secret": env.str("SOCIAL_AUTH_OIDC_SECRET"),
                "settings": {
                    "server_url": env.str("SOCIAL_AUTH_OIDC_ENDPOINT", "https://sso.service.security.gov.uk"),
                    "scope": ["openid", "email", "profile"],
                },
            }
        ]
    }
}

# CSP settings https://content-security-policy.com/
# https://django-csp.readthedocs.io/
CSP_DEFAULT_SRC = (
    "'self'",
    "s3.amazonaws.com",
    "plausible.io",
)
CSP_SCRIPT_SRC = (
    "'self'",
    "'sha256-GUQ5ad8JK5KmEWmROf3LZd9ge94daqNvd8xy9YS1iDw='",
    "plausible.io",
    "eu.i.posthog.com",
    "eu-assets.i.posthog.com",
)
CSP_OBJECT_SRC = ("'none'",)
CSP_REQUIRE_TRUSTED_TYPES_FOR = ("'script'",)
CSP_TRUSTED_TYPES = ("dompurify", "dompurifyMermaid", "lit-html", "default")
CSP_REPORT_TO = "csp-endpoint"
CSP_FONT_SRC = (
    "'self'",
    "s3.amazonaws.com",
)
CSP_STYLE_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'self'",)  # 'self' needed for printing chats


CSP_CONNECT_SRC = [
    "'self'",
    f"{WEBSOCKET_SCHEME}://{ENVIRONMENT.hosts[0]}/ws/chat/",
    "plausible.io",
    "eu.i.posthog.com",
    "eu-assets.i.posthog.com",
]


for csp in CSP_CONNECT_SRC:
    logger.info("CSP=%s", csp)


# https://pypi.org/project/django-permissions-policy/
PERMISSIONS_POLICY: dict[str, list] = {
    "accelerometer": [],
    "autoplay": [],
    "camera": [],
    "display-capture": [],
    "encrypted-media": [],
    "fullscreen": [],
    "gamepad": [],
    "geolocation": [],
    "gyroscope": [],
    "microphone": [],
    "midi": [],
    "payment": [],
}

CSRF_COOKIE_HTTPONLY = True

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_ENGINE = "django.contrib.sessions.backends.db"

LOG_ROOT = "."
LOG_HANDLER = "console"
BUCKET_NAME = env.str("BUCKET_NAME")
AWS_S3_REGION_NAME = env.str("AWS_REGION")
APPEND_SLASH = True

#  Property added to each S3 file to make them downloadable by default
AWS_S3_OBJECT_PARAMETERS = {"ContentDisposition": "attachment"}
AWS_STORAGE_BUCKET_NAME = BUCKET_NAME  # this duplication is required for django-storage
OBJECT_STORE = env.str("OBJECT_STORE")

STORAGES = {
    "default": {
        "BACKEND": s3boto3.S3Boto3Storage,
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

if ENVIRONMENT.uses_minio:
    AWS_S3_SECRET_ACCESS_KEY = env.str("AWS_SECRET_KEY")
    AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY")
    MINIO_HOST = env.str("MINIO_HOST")
    MINIO_PORT = env.str("MINIO_PORT")
    MINIO_ENDPOINT = f"http://{MINIO_HOST}:{MINIO_PORT}"
    AWS_S3_ENDPOINT_URL = MINIO_ENDPOINT
else:
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security
    # Mozilla guidance max-age 2 years
    SECURE_HSTS_SECONDS = 2 * 365 * 24 * 60 * 60
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SESSION_COOKIE_SECURE = True

if ENVIRONMENT.is_test:
    ALLOWED_HOSTS = ENVIRONMENT.hosts
else:
    LOCALHOST = socket.gethostbyname(socket.gethostname())
    ALLOWED_HOSTS = [LOCALHOST, *ENVIRONMENT.hosts]

if not ENVIRONMENT.is_local:

    def filter_transactions(event):
        url_string = event["request"]["url"]
        parsed_url = urlparse(url_string)
        if parsed_url.path.startswith("/admin"):
            return None
        return event

    SENTRY_DSN = env.str("SENTRY_DSN", None)
    SENTRY_ENVIRONMENT = env.str("SENTRY_ENVIRONMENT", None)
    if SENTRY_DSN and SENTRY_ENVIRONMENT:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
            ],
            environment=SENTRY_ENVIRONMENT,
            send_default_pii=False,
            traces_sample_rate=1.0,
            profiles_sample_rate=0.0,
            before_send_transaction=filter_transactions,
        )
SENTRY_REPORT_TO_ENDPOINT = URL(env.str("SENTRY_REPORT_TO_ENDPOINT", "")) or None

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("POSTGRES_DB"),
        "USER": env.str("POSTGRES_USER"),
        "PASSWORD": env.str("POSTGRES_PASSWORD"),
        "HOST": env.str("POSTGRES_HOST"),
        "PORT": "5432",
    }
}

LOG_LEVEL = env.str("DJANGO_LOG_LEVEL", "WARNING")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"verbose": {"format": "%(asctime)s %(levelname)s %(module)s: %(message)s"}},
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "application": {
            "handlers": [LOG_HANDLER],
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}


# Email
EMAIL_BACKEND_TYPE = env.str("EMAIL_BACKEND_TYPE")
FROM_EMAIL = env.str("FROM_EMAIL")
CONTACT_EMAIL = env.str("CONTACT_EMAIL")

if EMAIL_BACKEND_TYPE == "FILE":
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = env.str("EMAIL_FILE_PATH")
elif EMAIL_BACKEND_TYPE == "CONSOLE":
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
elif EMAIL_BACKEND_TYPE == "GOVUKNOTIFY":
    EMAIL_BACKEND = "django_gov_notify.backends.NotifyEmailBackend"
    GOVUK_NOTIFY_API_KEY = env.str("GOVUK_NOTIFY_API_KEY")
    GOVUK_NOTIFY_PLAIN_EMAIL_TEMPLATE_ID = env.str("GOVUK_NOTIFY_PLAIN_EMAIL_TEMPLATE_ID")
else:
    message = f"Unknown EMAIL_BACKEND_TYPE of {EMAIL_BACKEND_TYPE}"
    raise ValueError(message)


IMPORT_FORMATS = [CSV]

CHAT_TITLE_LENGTH = 30
FILE_EXPIRY_IN_SECONDS = env.int("FILE_EXPIRY_IN_DAYS") * 24 * 60 * 60
SUPERUSER_EMAIL = env.str("SUPERUSER_EMAIL", None)
MAX_SECURITY_CLASSIFICATION = Classification[env.str("MAX_SECURITY_CLASSIFICATION")]

SECURITY_TXT_REDIRECT = URL("https://vdp.cabinetoffice.gov.uk/.well-known/security.txt")
REDBOX_VERSION = os.environ.get("REDBOX_VERSION", "not set")

Q_CLUSTER = {
    "name": "redbox_django",
    "timeout": env.int("Q_TIMEOUT", 300),
    "retry": env.int("Q_RETRY", 900),
    "catch_up": False,
    "orm": "default",
    "max_attempts": env.int("Q_MAX_ATTEMPTS", 1),
    "ack_failures": True,
}

GOOGLE_ANALYTICS_TAG = env.str("GOOGLE_ANALYTICS_TAG", " ")
GOOGLE_ANALYTICS_LINK = env.str("GOOGLE_ANALYTICS_LINK", " ")
LIT_SSR_URL = env.str("LIT_SSR_URL", "localhost")


MESSAGE_THROTTLE_SECONDS_MIN = env.int("MESSAGE_THROTTLE_SECONDS_MIN", 1)
MESSAGE_THROTTLE_SECONDS_MAX = env.int("MESSAGE_THROTTLE_SECONDS_MAX", 10)
MESSAGE_THROTTLE_RATE = env.float("MESSAGE_THROTTLE_RATE", 0.1)

ALLOWED_EMAIL_DOMAINS = [domain.strip() for domain in env.str("ALLOWED_EMAIL_DOMAINS", ".gov.uk").split(",")]


if credentials := os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    file_path = Path.home() / "google-application-credentials"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(file_path)
    with Path.open(file_path, "w") as f:
        f.write(credentials)

METRICS_FILE_NAME = "metrics.csv"
USER_FILE_NAME = "users.csv"


ELASTIC_CHAT_MESSAGE_INDEX = env.str("ELASTIC_CHAT_MESSAGE_INDEX", None)

if ELASTIC_CHAT_MESSAGE_INDEX is None:
    ELASTIC_CLIENT = None
else:
    cloud_id = env.str("ELASTIC_CLOUD_ID")
    api_key = env.str("ELASTIC_API_KEY")
    client = Elasticsearch(cloud_id=cloud_id, api_key=api_key)

    try:
        if not client.indices.exists(index=ELASTIC_CHAT_MESSAGE_INDEX):
            client.indices.create(index=ELASTIC_CHAT_MESSAGE_INDEX)
    except ConnectionError:
        pass

    ELASTIC_CLIENT = client.options(request_timeout=30, retry_on_timeout=True, max_retries=3)
