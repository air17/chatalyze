import datetime
import json
import re
from io import BytesIO
from typing import Optional

from PIL.Image import Image
from django.core.cache import cache
from django.core.files.images import ImageFile
from django.utils.translation import gettext_lazy as _

from apps.dashboard.models import ChatAnalysis


class ProgressBar:
    """Progress bar value stored in cache"""

    def __init__(self, progress_id: str, timeout: int = 60 * 60):
        self.progress_id = progress_id
        self._value = 0
        self.timeout = timeout

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val: int):
        if self._value != val:
            self._value = val
            cache.set(f"task-progress:{self.progress_id}", val, timeout=self.timeout)

    @value.deleter
    def value(self):
        self._value = None
        cache.delete(f"task-progress:{self.progress_id}")


def explain_error(analysis: ChatAnalysis, e: Optional[BaseException] = None, message: Optional[str] = None) -> None:
    """Saves error message and raises exception
    Args:
        analysis: analysis info model
        e: Exception
        message: error message to display for a user
    """
    analysis.refresh_from_db()
    analysis.status = analysis.AnalysisStatus.ERROR
    analysis.error_text = message if message else "Couldn't process your file"
    analysis.save()
    cache.delete(f"task-progress:{analysis.progress_id}")
    if e:
        raise Exception from e
    else:
        raise Exception(message)


def pic_to_imgfile(pic: Image, name: str = "output.png", ext: Optional[str] = None) -> ImageFile:
    """Turns PIL image to Django ImageFile which can be assigned to ImageField
    Args:
        pic: PIL Image
        name: picture name
        ext: picture extension supported by PIL
    Returns Django ImageFile
    """
    if not ext:
        name_split = name.split(".")
        ext = name_split[-1].upper() if len(name_split) > 1 else "PNG"
    output = BytesIO()
    pic.save(output, format=ext)
    return ImageFile(output, name=name)


def get_whatsapp_chat_name(filename: str) -> Optional[str]:
    """Extracts chat name from WhatsApp exported file name.
    Args:
        filename: name of WhatsApp chat export file
    Returns chat name or None on failure
    """
    name_regex_ru = re.search(r"Чат WhatsApp с (.*)\.txt$", filename)
    name_regex_en = re.search(r"WhatsApp Chat with (.*)\.txt$", filename)
    if name_regex_ru:
        return name_regex_ru.group(1)
    elif name_regex_en:
        return name_regex_en.group(1)


def generate_dates(end_date: float, n: int, step_days: int = 1) -> list[str]:
    """Generates list of dates with specified parameters
    Args:
        end_date: the last day in the UNIX timestamp format for the generated dates list
        n: number of generated dates
        step_days: step between generated dates in days
    Returns list of dates in the format of dd.mm.yyyy
    """
    dt = datetime.datetime.fromtimestamp(end_date)
    step = datetime.timedelta(days=step_days)
    result = []
    while n != 0:
        result.append(dt.strftime("%d.%m.%Y"))
        dt -= step
        n -= 1
    result.reverse()
    return result


def load_chat_statistics(results_json: str) -> dict:
    """Loads json data to dict and adapts it for ChartJS"""
    chat_statistics = json.loads(results_json)
    chat_statistics["daily_year_msg"]["dates"] = generate_dates(
        end_date=chat_statistics["daily_year_msg"]["end_date"],
        n=len(chat_statistics["daily_year_msg"]["values"]),
    )
    chat_statistics["msg_per_user"] = {
        "labels": list(chat_statistics["msg_per_user"].keys()),
        "data": list(chat_statistics["msg_per_user"].values()),
    }
    chat_statistics["words_per_message"] = {
        "labels": list(chat_statistics["words_per_message"].keys()),
        "data": list(chat_statistics["words_per_message"].values()),
    }
    chat_statistics["msg_per_day"] = {
        "labels": list(chat_statistics["msg_per_day"].keys()),
        "data": list(chat_statistics["msg_per_day"].values()),
    }
    chat_statistics["response_time"] = {
        "labels": list(chat_statistics["response_time"].keys()),
        "data": list(chat_statistics["response_time"].values()),
    }
    if type(chat_statistics["top_weekday"]) is int:
        days = {
            0: _("Monday"),
            1: _("Tuesday"),
            2: _("Wednesday"),
            3: _("Thursday"),
            4: _("Friday"),
            5: _("Saturday"),
            6: _("Sunday"),
        }

        chat_statistics["top_weekday"] = days[chat_statistics["top_weekday"]]

    return chat_statistics
