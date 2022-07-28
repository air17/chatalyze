from django.shortcuts import render


def maintenance_view(request):
    """Notifies the user that the site is down for maintenance"""
    return render(request, "maintenance.html")
