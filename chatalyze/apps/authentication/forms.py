from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import UserProfile


class LoginForm(forms.Form):
    """Login form"""

    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": _("Username"), "class": "form-control"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": _("Password"), "class": "form-control"})
    )


class SignUpForm(UserCreationForm):
    """Custom registration form"""

    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder": _("Username"), "class": "form-control"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": _("Email"), "class": "form-control"}))
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": _("Password"), "class": "form-control"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": _("Password check"), "class": "form-control"})
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ProfileForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": _("Enter your username"), "class": "form-control"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "name@domain.com", "class": "form-control"})
    )
    language = forms.ChoiceField(
        choices=UserProfile.ProfileLanguage.choices,
        widget=forms.Select(attrs={"class": "form-select mb-0"}),
        required=False,
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if "email" in self.changed_data and User.objects.filter(email=email).exists():
            raise ValidationError(_("A user with such an email already exists"))
        return email

    def clean_username(self):
        username = self.cleaned_data["username"]
        if "username" in self.changed_data and User.objects.filter(username=username).exists():
            raise ValidationError(_("Username already exists"))
        return username


class ChangePasswordForm(forms.Form):
    """Password change form"""

    error_messages = {
        "password_mismatch": _("The two password fields didn't match."),
    }
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Enter your new password"),
                "class": "form-control",
            }
        ),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Repeat your new password"),
                "class": "form-control",
            }
        ),
        strip=False,
    )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages["password_mismatch"],
                code="password_mismatch",
            )
        return password2
