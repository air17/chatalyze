from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel


class SiteConfiguration(SingletonModel):
    """Model for site-wide settings.

    Attributes:
        close_for_maintenance: Defines if site is closed for users
        max_file_size: Max size of the uploaded chat file
    """

    close_for_maintenance = models.BooleanField(
        default=False,
        help_text=_("Close this site (except home page) for visitors."),
        verbose_name=_("Close for maintenance"),
    )
    max_file_size = models.IntegerField(
        validators=(MinValueValidator(1),),
        default=100,
        help_text=_("Maximum size for the uploaded chat file in MB."),
        verbose_name=_("Max. file size"),
    )

    def __str__(self):
        return str(_("Site Configuration"))

    class Meta:
        verbose_name = _("Site Configuration")
