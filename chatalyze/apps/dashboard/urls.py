from django.urls import path, re_path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="home"),
    path("analyze", views.analyze, name="analyze"),
    path("results", views.results, name="results"),
    path("result/<int:pk>", views.analysis_result, name="result"),
    path("result/<int:pk>/check", views.check_status, name="check_status"),
    path("result/<int:pk>/delete", views.delete_analysis, name="delete_analysis"),
    path("result/<int:pk>/rename", views.rename_analysis, name="rename_analysis"),
    path("result/<int:pk>/update", views.analysis_update, name="analysis_update"),
    path("result/<int:pk>/discard-error", views.discard_error, name="discard_error"),
    path("result/<int:pk>/share-chat", views.share_analysis, name="share_analysis"),
    path("share/<str:pk>", views.shared_result, name="shared_result"),
]
