from django.conf.urls.static import static
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.urls import path, include, re_path

from core import settings


def permission_denied(_):
    raise PermissionDenied()


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.authentication.urls")),
    re_path(r"private_files", permission_denied),
    path("", include("apps.dashboard.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += (path("__debug__/", include(debug_toolbar.urls)),)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
