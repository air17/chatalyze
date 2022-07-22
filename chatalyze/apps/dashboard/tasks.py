import json

from celery import shared_task

from .analysis_utils import analyze_tg, analyze_wa, update_tg, analyze_fb, explain_error
from .const import TELEGRAM, WHATSAPP, FACEBOOK
from .models import ChatAnalysis


@shared_task
def analyze_chat_file(analysis_id):
    """Starts chat analysis"""
    analysis = ChatAnalysis.objects.get(pk=analysis_id)
    if analysis.chat_file.name.endswith(".json"):
        try:
            with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
                chat_file = json.load(f)
        except Exception as e:
            explain_error(analysis, e, "File format is wrong")

        if chat_file.get("participants"):
            analyze_fb(analysis)
        else:
            analyze_tg(analysis)

    elif analysis.chat_file.name.endswith(".txt"):
        analyze_wa(analysis)

    else:
        analysis.status = ChatAnalysis.AnalysisStatus.ERROR
        analysis.error_text = "Couldn't recognize message service."
        analysis.save()


@shared_task
def update_chat_analysis(analysis_id):
    """Starts updated chat analysis"""
    analysis = ChatAnalysis.objects.get(pk=analysis_id)
    if analysis.chat_platform == TELEGRAM:
        update_tg(analysis)
    elif analysis.chat_platform == WHATSAPP:
        analyze_wa(analysis)
    elif analysis.chat_platform == FACEBOOK:
        analyze_fb(analysis)
