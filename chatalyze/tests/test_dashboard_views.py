import json
import pytest
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from pytest_django.asserts import assertTemplateUsed

from apps.dashboard.const import TELEGRAM
from apps.dashboard.models import ChatAnalysis
from apps.dashboard.views import analyze, analysis_update


def test_index(admin_client):
    response = admin_client.get("")
    assert response.status_code == 200
    assertTemplateUsed(response, "home/index.html")


def test_analyze(rf, admin_user):
    request = rf.post("")
    request.user = admin_user
    request.FILES["chatfile"] = SimpleUploadedFile("file.txt", b"file_content")
    response = analyze(request)
    assert response.status_code == 400
    request = rf.post("/", data={"lang": ChatAnalysis.AnalysisLanguage.ENGLISH})
    request.user = admin_user
    request.FILES["chatfile"] = SimpleUploadedFile("file.txt", b"file_content")
    response = analyze(request)
    assert response.status_code == 302
    request.FILES["chatfile"] = SimpleUploadedFile("file.py", b"file_content")
    response = analyze(request)
    assert response.status_code == 400


def test_analysis_update(rf, admin_user, django_user_model):
    analysis = ChatAnalysis.objects.create(author=admin_user, chat_platform=TELEGRAM)
    request = rf.post("")
    request.user = admin_user
    response = analysis_update(request, analysis.pk)
    assert response.status_code == 400
    request.FILES["chatfile"] = SimpleUploadedFile("file.txt", b"file_content")
    response = analysis_update(request, analysis.pk)
    assert response.status_code == 400
    request.FILES["chatfile"] = SimpleUploadedFile("file.json", b"file_content")
    response = analysis_update(request, analysis.pk)
    assert response.status_code == 302
    user = django_user_model.objects.create_user(username="user", email="user@user.us", password="1234")
    request.user = user
    with pytest.raises(PermissionDenied):
        analysis_update(request, analysis.pk)


def test_results(admin_client):
    response = admin_client.get("/results")
    assert response.status_code == 200
    assertTemplateUsed(response, "home/results.html")
    assert len(response.context["results"]) == 0


def test_analysis_result(admin_client, admin_user):
    analysis = ChatAnalysis.objects.create(author=admin_user)
    response = admin_client.get("/result/" + str(analysis.pk))
    assert response.status_code == 200
    assertTemplateUsed(response, "home/result.html")
    assert isinstance(response.context["result"], ChatAnalysis)


def test_discard_error(admin_client, admin_user):
    analysis = ChatAnalysis.objects.create(
        author=admin_user,
        status=ChatAnalysis.AnalysisStatus.ERROR,
        error_text="Error",
    )
    response = admin_client.get("/result/" + str(analysis.pk) + "/discard-error")
    assert response.status_code == 400

    analysis.word_cloud_pic = SimpleUploadedFile("file.png", b"file_content")
    analysis.save()
    response = admin_client.get("/result/" + str(analysis.pk) + "/discard-error")
    assert response.status_code == 200
    analysis.refresh_from_db()
    assert analysis.error_text == ""


def test_delete_analysis(admin_client, admin_user):
    analysis = ChatAnalysis.objects.create(author=admin_user)
    response = admin_client.get("/result/" + str(analysis.pk) + "/delete")
    assert response.status_code == 302
    response = admin_client.get("/result/" + str(analysis.pk) + "/delete")
    assert response.status_code == 404


def test_rename_analysis(admin_client, admin_user):
    analysis = ChatAnalysis.objects.create(author=admin_user, chat_name="Name")
    response = admin_client.get("/result/" + str(analysis.pk) + "/rename")
    assert response.status_code == 400
    response1 = admin_client.get("/result/" + str(analysis.pk) + "/rename?name=New name")
    assert response1.status_code == 200
    analysis.refresh_from_db()
    assert analysis.chat_name == "New name"


def test_shared_result(admin_client, admin_user, client):
    analysis = ChatAnalysis.objects.create(author=admin_user)
    response = admin_client.get("/result/" + str(analysis.pk) + "/share-chat")
    link = json.loads(response.getvalue().decode())["link"]
    response_result = client.get(link)
    assert response_result.status_code == 200
    assertTemplateUsed(response_result, "home/share.html")
    assert isinstance(response_result.context["result"], ChatAnalysis)


def test_share_analysis(admin_client, admin_user):
    analysis = ChatAnalysis.objects.create(author=admin_user)
    response = admin_client.get("/result/" + str(analysis.pk) + "/share-chat")
    assert response.status_code == 200
    link = json.loads(response.getvalue().decode())["link"]
    new_response = admin_client.get("/result/" + str(analysis.pk) + "/share-chat?new_link=true")
    new_link = json.loads(new_response.getvalue().decode())["link"]
    assert response.status_code == 200
    assert link != new_link
