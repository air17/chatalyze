import json
import yaml
from django.utils import timezone
from ftfy import ftfy

from apps.dashboard.const import TELEGRAM, WHATSAPP, FACEBOOK
from apps.dashboard.models import ChatAnalysis
from apps.dashboard.utils import explain_error, pic_to_imgfile, ProgressBar
from .general_analysis import get_msg_dict_wa, make_general_analysis
from .wordcloud_tools import make_wordcloud


def analyze_tg(analysis: ChatAnalysis) -> None:
    """Performs Telegram chat analysis and saves the results
    Args:
        analysis: analysis info model
    """
    try:
        try:
            with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
                chat_history = json.load(f)
        except json.JSONDecodeError:
            with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
                chat_history = yaml.safe_load(f)

        chat_id = str(chat_history["id"])
        chat_name = chat_history["name"]
        msg_list = chat_history["messages"]
    except Exception as e:
        explain_error(analysis, e, "File format is wrong")
    else:
        analysis.chat_name = chat_name if chat_name else "noname"
        analysis.telegram_id = chat_id
        analysis.messages_count = len(msg_list)
        analysis.chat_platform = TELEGRAM
        analysis.save()

        run_analyses(analysis, msg_list)


def update_tg(analysis: ChatAnalysis) -> None:
    """Performs Telegram chat analysis and updates the results
    Args:
        analysis: analysis info model
    """
    try:
        try:
            with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
                chat_history = json.load(f)
        except json.JSONDecodeError:
            with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
                chat_history = yaml.safe_load(f)

        if str(chat_history["id"]) != analysis.telegram_id:
            raise ValueError("Chat id doesn't match")

        msg_list = chat_history["messages"]
        stop_users = analysis.custom_stoplist
        if stop_users:
            msg_list = list(
                filter(
                    lambda msg: msg.get("from") not in stop_users and msg.get("from_id") not in stop_users, msg_list
                )
            )
    except ValueError as e:
        explain_error(analysis, e, "You've uploaded a different chat history.")
    except Exception as e:
        explain_error(analysis, e, "File format is wrong.")
    else:
        analysis.messages_count = len(msg_list)
        analysis.save()

        run_analyses(analysis, msg_list)


def analyze_wa(analysis: ChatAnalysis) -> None:
    """Performs Telegram chat analysis and saves the results
    Args:
        analysis: analysis info model
    """
    try:
        with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
            text = f.read()
        msg_list = get_msg_dict_wa(text)
        if stop_users := analysis.custom_stoplist:
            msg_list = list(filter(lambda msg: msg.get("from") not in stop_users, msg_list))
    except ValueError as e:
        explain_error(analysis, e, "File format is wrong or this WhatsApp localization is not supported yet.")
    except Exception as e:
        explain_error(analysis, e, "File format is wrong")
    else:
        analysis.messages_count = len(msg_list)
        analysis.chat_platform = WHATSAPP
        analysis.save()

        run_analyses(analysis, msg_list)


def analyze_fb(analysis: ChatAnalysis) -> None:
    """Performs Telegram chat analysis and saves the results
    Args:
        analysis: analysis info model
    """
    try:
        with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
            chat_history = json.load(f)

        chat_name = ftfy(chat_history["title"])
        msg_list_encoded = chat_history["messages"]
        msg_list = []
        for msg in msg_list_encoded:
            if msg.get("content"):
                msg["content"] = ftfy(msg.get("content"))
            if msg.get("sender_name"):
                msg["sender_name"] = ftfy(msg.get("sender_name"))
            msg_list.append(msg)
    except Exception as e:
        explain_error(analysis, e, "File format is wrong")
    else:
        analysis.chat_name = chat_name if chat_name else "noname"
        analysis.messages_count = len(msg_list)
        analysis.chat_platform = FACEBOOK
        analysis.save()

        run_analyses(analysis, msg_list)


def run_analyses(analysis: ChatAnalysis, msg_list: list) -> None:
    """Starts analyses for provided messages and saves results to analysis object
    Args:
        analysis: analysis info model
        msg_list: list of messages in a format of message service
    """
    progress = ProgressBar(analysis.progress_id)
    progress.value = 2
    try:
        results = make_general_analysis(msg_list, analysis.chat_platform, progress)
    except Exception as e:
        explain_error(analysis, e, "Couldn't make analysis. Some error.")
    else:
        analysis.results = json.dumps(results)
        analysis.save()
        progress.value = 50

    try:
        wordcloud_pic = make_wordcloud(msg_list, analysis.chat_platform, analysis.language, progress)
    except Exception as e:
        explain_error(analysis, e, "Couldn't build a wordcloud of your chat.")
    else:
        progress.value = 100
        analysis.word_cloud_pic = pic_to_imgfile(wordcloud_pic, "wc.png")
        analysis.status = analysis.AnalysisStatus.READY
        analysis.updated = timezone.now()
        analysis.save()
        del progress.value
