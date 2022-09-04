from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_noop, gettext_lazy as _


class UserProfile(models.Model):
    """Stores analysis results and chat information

    Attributes:
        user: Related User model
        language: User's preferred language

    """

    class ProfileLanguage(models.TextChoices):
        """Enumerated string choices."""

        _ = ""
        ENGLISH = "en", gettext_noop("English")
        RUSSIAN = "ru", gettext_noop("Russian")
        UKRAINIAN = "uk", gettext_noop("Ukrainian")

    user = models.OneToOneField(
        to=User,
        on_delete=models.CASCADE,
    )
    language = models.CharField(
        default="",
        blank=True,
        choices=ProfileLanguage.choices,
        max_length=10,
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        constraints = (
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_language_valid",
                check=models.Q(language__in=["", "en", "ru", "uk"]),
            ),
        )

    def __str__(self):
        return str(self.user)
