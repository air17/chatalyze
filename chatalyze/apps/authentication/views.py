from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseNotAllowed, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.utils.translation import gettext_lazy as _

from .models import UserProfile
from .forms import LoginForm, SignUpForm, ProfileForm, ChangePasswordForm


def login_view(request):
    """Custom login view"""
    form = LoginForm(request.POST or None)

    msg = None

    if request.method == "POST":

        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("/")
            else:
                msg = _("Invalid credentials")
        else:
            msg = _("Error validating the form")

    return render(request, "accounts/login.html", {"form": form, "msg": msg})


def register_user(request):
    """Custom registration view"""
    msg = None
    success = False

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(request, username=username, password=raw_password)

            if user is not None:
                login(request, user)
                return redirect("/")

        else:
            msg = _("Form is not valid")
    else:
        form = SignUpForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form, "msg": msg, "success": success},
    )


@login_required
def settings(request):
    """Displays and processes profile settings forms"""
    profile = UserProfile.objects.get_or_create(user=request.user)[0]
    profile_data = {
        "username": request.user.username,
        "email": request.user.email,  # noqa
        "language": profile.language,
    }
    context = {
        "segment": "settings",
        "profile": profile,
        "form": ProfileForm(profile_data, initial=profile_data),
        "password_form": ChangePasswordForm(),
    }
    if request.method == "POST":
        if request.POST.get("form_type") == "profile":
            profile_form = ProfileForm(data=request.POST, initial=profile_data)
            if not profile_form.has_changed():
                return redirect("settings")
            if profile_form.is_valid():
                user = User.objects.get(pk=request.user.pk)
                user.username = profile_form.cleaned_data.get("username")
                user.email = profile_form.cleaned_data.get("email")
                user.save()

                profile.language = profile_form.cleaned_data.get("language")
                profile.save()

                return redirect("settings")
            else:
                context["form"] = profile_form
        elif request.POST.get("form_type") == "password":
            pass_form = ChangePasswordForm(request.POST)
            if pass_form.is_valid():
                u = User.objects.get(pk=request.user.pk)
                u.set_password(pass_form.cleaned_data.get("password2"))
                u.save()
                user = authenticate(
                    request,
                    username=u.username,
                    password=pass_form.cleaned_data.get("password2"),
                )

                if user is not None:
                    login(request, user)
                    return redirect("settings")
                else:
                    return HttpResponseBadRequest()

            else:
                context["password_form"] = pass_form
        else:
            return HttpResponseBadRequest()
    elif request.method != "GET":
        return HttpResponseNotAllowed(permitted_methods=["GET", "POST"])

    return render(request, "home/settings.html", context)


@login_required
def delete_profile(request):
    """Deletes user profile"""
    if request.POST.get("sure"):
        u = User.objects.get(pk=request.user.pk)
        u.delete()
        return redirect("dashboard:home")
    else:
        return HttpResponseForbidden()
