import json
import yaml

from celery import shared_task

from .analysis_tools.main import analyze_tg, analyze_wa, analyze_fb, update_tg
from .const import TELEGRAM, WHATSAPP, FACEBOOK
from .models import ChatAnalysis
from .utils import explain_error


@shared_task
def analyze_chat_file(analysis_id):
    """Starts chat analysis"""
    analysis = ChatAnalysis.objects.get(pk=analysis_id)
    if analysis.chat_file.name.endswith(".json"):
        try:
            with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
                chat_file = json.load(f)
        except json.JSONDecodeError as e:
            try:
                if analysis.chat_file.file.size > 20e6:  # don't process files bigger than 20 MB as it's very slow
                    raise
                with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
                    chat_file = yaml.load(f, yaml.Loader)
            except Exception:
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
