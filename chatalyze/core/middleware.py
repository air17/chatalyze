from django.middleware.locale import LocaleMiddleware
from django.utils.translation import activate

from apps.authentication.models import UserProfile


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
