"""
This file contains all the settings used in production.

This file is required and if development.py is present these
values are overridden.
"""

from core.settings.components import config

# Production flags:
# https://docs.djangoproject.com/en/4.0/howto/deployment/

DEBUG = False

ALLOWED_HOSTS = [
    config("DOMAIN_NAME"),
    # We need this value for `healthcheck` to work:
    "localhost",
]


# Staticfiles
# https://docs.djangoproject.com/en/4.0/ref/contrib/staticfiles/

# This is a hack to allow a special flag to be used with `--dry-run`
# to test things locally.
_COLLECTSTATIC_DRYRUN = config(
    "DJANGO_COLLECTSTATIC_DRYRUN",
    cast=bool,
    default=False,
)
# Adding STATIC_ROOT to collect static files via 'collectstatic':
STATIC_ROOT = ".static" if _COLLECTSTATIC_DRYRUN else "static"

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

_PASS = "django.contrib.auth.password_validation"  # noqa: S105
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "{0}.UserAttributeSimilarityValidator".format(_PASS)},
    {"NAME": "{0}.MinimumLengthValidator".format(_PASS)},
    {"NAME": "{0}.CommonPasswordValidator".format(_PASS)},
    {"NAME": "{0}.NumericPasswordValidator".format(_PASS)},
]


# Security
# https://docs.djangoproject.com/en/4.0/topics/security/

SECURE_HSTS_SECONDS = 31536000  # the same as Caddy has
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [
    # This is required for healthcheck to work:
    "^health/",
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "%(asctime)s [%(process)d] [%(levelname)s] "
                + "pathname=%(pathname)s lineno=%(lineno)s "
                + "funcname=%(funcName)s %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "null": {
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
        "console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "testlogger": {
            "handlers": ["console"],
            "level": "INFO",
        }
    },
}

DEBUG_PROPAGATE_EXCEPTIONS = True
