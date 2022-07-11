from django.conf import settings


def cfg_assets_root(request):
    """Adds ASSETS_ROOT to Django Templates context"""
    return {"ASSETS_ROOT": settings.ASSETS_ROOT}
