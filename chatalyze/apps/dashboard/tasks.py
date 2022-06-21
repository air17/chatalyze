from celery import shared_task

from .analysis_utils import analyze_tg, analyze_wa, update_tg
from .const import TELEGRAM, WHATSAPP
from .models import ChatAnalysis


@shared_task
def analyze_chat_file(analysis_id):
    analysis = ChatAnalysis.objects.get(pk=analysis_id)
    if analysis.chat_file.name.endswith(".json"):
        analyze_tg(analysis)
    elif analysis.chat_file.name.endswith(".txt"):
        analyze_wa(analysis)
    else:
        analysis.status = ChatAnalysis.AnalysisStatus.ERROR
        analysis.error_text = "Couldn't recognize message service."
        analysis.save()


@shared_task
def update_chat_analysis(analysis_id):
    analysis = ChatAnalysis.objects.get(pk=analysis_id)
    if analysis.chat_platform == TELEGRAM:
        update_tg(analysis)
    elif analysis.chat_platform == WHATSAPP:
        analyze_wa(analysis)
