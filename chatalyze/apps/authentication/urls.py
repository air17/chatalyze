from django.urls import path

from . import views
from .views import login_view, register_user, register_guest
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", register_user, name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("settings/", views.settings, name="settings"),
    path("delete-profile/", views.delete_profile, name="delete-profile"),
    path("register-guest/", register_guest, name="register-guest"),
]
