# Caching
# https://docs.djangoproject.com/en/4.0/topics/cache/

CACHES = {
    "default": {
        # like https://github.com/jazzband/django-redis
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}


# django-axes
# https://django-axes.readthedocs.io/en/latest/4_configuration.html#configuring-caches

AXES_CACHE = "default"
