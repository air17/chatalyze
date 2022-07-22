from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


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
