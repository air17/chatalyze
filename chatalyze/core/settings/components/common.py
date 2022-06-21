"""
Django settings for server project.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their config, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
import os.path
from typing import Tuple

from core.settings.components import BASE_DIR, config

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

SECRET_KEY = config("DJANGO_SECRET_KEY")

# Application definition:

INSTALLED_APPS: Tuple[str, ...] = (
    "apps.authentication",
    "apps.dashboard",
    # Django Cleanup
    "django_cleanup.apps.CleanupConfig",
    # Default django apps:
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # django-admin:
    "django.contrib.admin",
    "django.contrib.admindocs",
    # Security:
    "axes",
    # Health checks:
    # You may want to enable other checks as well,
    # see: https://github.com/KristianOellegaard/django-health-check
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.storage",
    # Celery:
    "django_celery_results",
)


# Logs email
ADMINS = [("Admin", config("ADMIN_EMAIL", default="admin@localhost"))]

MIDDLEWARE: Tuple[str, ...] = (
    # Django:
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Axes:
    "axes.middleware.AxesMiddleware",
    # Django HTTP Referrer Policy:
    "django_http_referrer_policy.middleware.ReferrerPolicyMiddleware",
    # WhiteNoise:
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

ROOT_URLCONF = "core.urls"

WSGI_APPLICATION = "core.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="POSTGRES_DB"),
        "USER": config("POSTGRES_USER", default="POSTGRES_USER"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="POSTGRES_PASSWORD"),
        "HOST": config("DJANGO_DATABASE_HOST", default="localhost"),
        "PORT": config("DJANGO_DATABASE_PORT", cast=int, default=5432),
        "CONN_MAX_AGE": config("CONN_MAX_AGE", cast=int, default=60),
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=15000ms",
        },
    },
}


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Istanbul"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Assets Management
ASSETS_ROOT = os.getenv("ASSETS_ROOT", "/static/assets")


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)


# Templates
# https://docs.djangoproject.com/en/4.0/ref/templates/api

TEMPLATES = [
    {
        "APP_DIRS": True,
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR.joinpath("templates"),
        ],
        "OPTIONS": {
            "context_processors": [
                # Default template context processors:
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.media",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                # Assets finder
                "apps.context_processors.cfg_assets_root",
            ],
        },
    }
]


# Media files
# Media root dir is commonly changed in production
# (see development.py and production.py).
# https://docs.djangoproject.com/en/4.0/topics/files/

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR.joinpath("media")

# Django authentication system
# https://docs.djangoproject.com/en/4.0/topics/auth/

AUTHENTICATION_BACKENDS = (
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
)

PASSWORD_HASHERS = (
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.BCryptPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
)

LOGOUT_REDIRECT_URL = "/"
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/login"

# Security
# https://docs.djangoproject.com/en/4.0/topics/security/

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

X_FRAME_OPTIONS = "DENY"

AXES_FAILURE_LIMIT = 10
AXES_NEVER_LOCKOUT_WHITELIST = True
AXES_IP_WHITELIST = ("127.0.0.1",)

# https://github.com/DmytroLitvinov/django-http-referrer-policy
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referrer-Policy
REFERRER_POLICY = "same-origin"


# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


# Celery settings
CELERY_BROKER_URL = "pyamqp://guest:guest@localhost:5672/"
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
