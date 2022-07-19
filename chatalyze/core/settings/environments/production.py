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
STATIC_ROOT = ".staticfiles" if _COLLECTSTATIC_DRYRUN else "staticfiles"

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

_PASS = "django.contrib.auth.password_validation"  # noqa: S105
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"{_PASS}.UserAttributeSimilarityValidator"},
    {"NAME": f"{_PASS}.MinimumLengthValidator"},
    {"NAME": f"{_PASS}.CommonPasswordValidator"},
    {"NAME": f"{_PASS}.NumericPasswordValidator"},
]


# Security
# https://docs.djangoproject.com/en/4.0/topics/security/

SECURE_HSTS_SECONDS = 31536000  # the same as Caddy has
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = (
    "https://" + config("DOMAIN_NAME"),
    "http://" + config("DOMAIN_NAME"),
    "http://localhost:8000",
)

USE_X_FORWARDED_PORT = True

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
        "logfile": {
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "server.log"),  # noqa: F821
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["logfile"],
            "level": "INFO",
            "propagare": True,
        },
    },
}

DEBUG_PROPAGATE_EXCEPTIONS = True
