from django.middleware.locale import LocaleMiddleware
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import activate

from apps.authentication.models import UserProfile
from apps.config.models import SiteConfiguration
from apps.config.views import maintenance_view


class CustomLocaleMiddleware(LocaleMiddleware):
    """
    Override Django LocaleMiddleware in order to read user preferences.
    """

    @staticmethod
    def __userHasLanguagePreference(request):
        if request.user.is_authenticated:
            profile = UserProfile.objects.get_or_create(user=request.user)[0]
            if profile.language:
                return True
        return False

    @staticmethod
    def __activateUserFavoriteLanguage(request):
        activate(request.user.userprofile.language)
        request.LANGUAGE_CODE = request.user.userprofile.language

    def process_request(self, request):
        if self.__userHasLanguagePreference(request):
            self.__activateUserFavoriteLanguage(request)
        else:
            super().process_request(request)


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.META.get("PATH_INFO")
        if path not in ("", "/") and not path.startswith("/admin"):
            is_closed = SiteConfiguration.get_solo().close_for_maintenance
            if is_closed:
                return maintenance_view(request)

        response = self.get_response(request)
        return response
