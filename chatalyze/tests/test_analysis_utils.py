import json
import os
from PIL import Image
import pytest

from apps.dashboard.analysis_tools.general_analysis import get_msg_dict_wa, make_general_analysis
from apps.dashboard.analysis_tools.wordcloud_tools import make_wordcloud
from apps.dashboard.utils import ProgressBar, load_chat_statistics
from apps.dashboard.const import WHATSAPP
from apps.dashboard.models import ChatAnalysis

if os.path.isdir("chatalyze"):
    os.chdir("chatalyze")

_dir = os.path.dirname(os.path.realpath(__file__))
TEST_FILES = _dir + "/test_files"
WHATSAPP_DATA = pytest.mark.datafiles(TEST_FILES + "/WhatsApp Chat with User.txt")

progress = ProgressBar("test")


@WHATSAPP_DATA
def test_get_msg_dict_wa(datafiles):
    path = str(datafiles)
    with open(path + "/WhatsApp Chat with User.txt", "r", encoding="UTF8") as f:
        text = f.read()
    msg_list = get_msg_dict_wa(text)
    assert "User:)" == msg_list[0]["from"]
    assert len(msg_list) == 16


@WHATSAPP_DATA
def test_make_general_analysis(datafiles):
    path = str(datafiles)
    with open(path + "/WhatsApp Chat with User.txt", "r", encoding="UTF8") as f:
        text = f.read()
    msg_list = get_msg_dict_wa(text)
    results = make_general_analysis(msg_list, WHATSAPP, progress)
    assert results["daily_year_msg"]["end_date"] == 1654981200.0
    assert results["top_day"] == "05.06.2022"
    assert results["top_weekday"] == 6
    assert results["hourly_messages"] == [0.5, 0.25, 0.08, 0.08, 0.17, 0.08, 0.17]
    assert results["msg_per_user"]["User1"] == 9
    assert results["msg_per_day"]["User:)"] == 0.6
    assert results["words_per_message"]["User:)"] == 1.5
    assert results["media_text_share"]["text"] == 81.25
    assert results["response_time"]["User1"] == 120.0
    assert results["response_time_hour"] == {"start": 1, "end": 2}


@WHATSAPP_DATA
def test_get_chat_statistics(datafiles):
    path = str(datafiles)
    with open(path + "/WhatsApp Chat with User.txt", "r", encoding="UTF8") as f:
        text = f.read()
    msg_list = get_msg_dict_wa(text)
    results = make_general_analysis(msg_list, WHATSAPP, progress)
    results_json = json.dumps(results)
    chat_statistics = load_chat_statistics(results_json)
    assert type(chat_statistics) is dict


@WHATSAPP_DATA
def test_make_wordcloud(datafiles):
    path = str(datafiles)
    with open(path + "/WhatsApp Chat with User.txt", "r", encoding="UTF8") as f:
        text = f.read()
    msg_list = get_msg_dict_wa(text)
    result = make_wordcloud(msg_list, WHATSAPP, ChatAnalysis.AnalysisLanguage.ENGLISH, progress)
    assert type(result) is Image.Image
