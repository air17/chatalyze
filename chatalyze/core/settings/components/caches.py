from core.settings.components import config

# Caching
# https://docs.djangoproject.com/en/4.0/topics/cache/

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("DJANGO_CACHE_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": config("REDIS_PASSWORD", default=""),
        },
    },
}


# django-axes
# https://django-axes.readthedocs.io/en/latest/4_configuration.html#configuring-caches

AXES_CACHE = "default"

# Django Sessions
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
