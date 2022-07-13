import datetime
import json
import re
import statistics
from collections import Counter
from io import BytesIO
from typing import Optional, Union

import pandas as pd
import numpy as np

from PIL.Image import Image
from django.core.files.images import ImageFile
from django.utils import timezone
from wordcloud import WordCloud
from pymorphy2 import MorphAnalyzer

from .const import TELEGRAM, WHATSAPP
from .models import ChatAnalysis
from .stopwords import whatsapp_stoplist, stopwords_ru, stopwords_en, whatsapp_stoplist_no_media

morph = MorphAnalyzer()


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
    if e:
        raise Exception from e
    else:
        raise Exception(message)


def analyze_tg(analysis: ChatAnalysis) -> None:
    """Performs Telegram chat analysis and saves the results
    Args:
        analysis: analysis info model
    """
    try:
        with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
            chat_history = json.load(f)

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
        if chat_id:
            analysis_old = ChatAnalysis.objects.filter(telegram_id=chat_id).first()
            if analysis_old:
                analysis.delete()
                analysis = analysis_old
                analysis.messages_count = len(msg_list)
                analysis.status = analysis.AnalysisStatus.PROCESSING

        analysis.save()

        run_analyses(analysis, msg_list)


def update_tg(analysis: ChatAnalysis) -> None:
    """Performs Telegram chat analysis and updates the results
    Args:
        analysis: analysis info model
    """
    try:
        with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
            chat_history = json.load(f)

        if str(chat_history["id"]) != analysis.telegram_id:
            raise ValueError("Chat id doesn't match")

        msg_list = chat_history["messages"]
    except ValueError as e:
        explain_error(analysis, e, "You've uploaded a different chat history.")
    except Exception as e:
        explain_error(analysis, e, "File format is wrong.")
    else:
        analysis.messages_count = len(msg_list)
        analysis.status = analysis.AnalysisStatus.PROCESSING
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
    except ValueError as e:
        explain_error(analysis, e, "File format is wrong or this WhatsApp localization is not supported yet.")
    except Exception as e:
        explain_error(analysis, e, "File format is wrong")
    else:
        analysis.messages_count = len(msg_list)
        analysis.chat_platform = WHATSAPP
        analysis.status = analysis.AnalysisStatus.PROCESSING
        analysis.save()

        run_analyses(analysis, msg_list)


def run_analyses(analysis: ChatAnalysis, msg_list: list) -> None:
    """Starts analyses for provided messages and saves results to analysis object
    Args:
        analysis: analysis info model
        msg_list: list of messages in a format of message service
    """

    try:
        results = make_general_analysis(msg_list, analysis.chat_platform)
    except Exception as e:
        explain_error(analysis, e, "Couldn't make analysis. Some error.")
    else:
        analysis.results = json.dumps(results)
        analysis.save()

    try:
        wordcloud_pic = make_wordcloud(msg_list, analysis.chat_platform, analysis.language)
    except Exception as e:
        explain_error(analysis, e, "Couldn't build a wordcloud of your chat.")
    else:
        analysis.word_cloud_pic = pic_to_imgfile(wordcloud_pic, "wc.png")
        analysis.status = analysis.AnalysisStatus.READY
        analysis.updated = timezone.now()
        analysis.save()


def make_wordcloud(raw_messages: list, chat_platform: str, language: str) -> Image:
    """Produces wordcloud for provided messages
    Args:
        raw_messages: list of messages in a format of message service
        chat_platform: Name of chat platform
        language: Language of messages
    Returns a WordCloud in a PIL Image format
    """
    if chat_platform == TELEGRAM:
        msg_list_direct = remove_forwarded(raw_messages)
        msg_list_txt = get_msg_text_list_tg_wa(msg_list_direct)
    elif chat_platform == WHATSAPP:
        msg_list_txt = get_msg_text_list_tg_wa(raw_messages)
        msg_list_txt = filter_whatsapp_messages(msg_list_txt)
    else:
        raise ValueError("Wrong chat platform")

    filtered_msg_list_txt = filter_big_messages(msg_list_txt)

    words_list = get_words(filtered_msg_list_txt)

    if language == ChatAnalysis.AnalysisLanguage.RUSSIAN:
        normal_words = get_normalized_words_ru(words_list)

        # change the normal form of the word with a more common form
        normal_words = [word if word != "деньга" else "деньги" for word in normal_words]

        counted_words = get_word_count(normal_words)
        wordcloud_pic = get_pic_from_frequencies(counted_words)
    elif language == ChatAnalysis.AnalysisLanguage.ENGLISH:
        wc = WordCloud(
            max_words=200,
            width=1920,
            height=1080,
            color_func=get_colors_by_size,
            stopwords=stopwords_en,
            collocation_threshold=3,
            min_word_length=3,
        )
        word_cloud = wc.generate(" ".join(filtered_msg_list_txt))
        wordcloud_pic = word_cloud.to_image()
    else:
        raise ValueError("Wrong language")

    return wordcloud_pic


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


def get_chat_name_wa(filename: str) -> Optional[str]:
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


def filter_whatsapp_messages(msg_list: list[str]) -> list[str]:
    """Filters out bare links and WhatsApp service messages from the list of messages
    Args:
        msg_list: List of messages
    Returns filtered list of messages
    """
    msg_list_clean = []

    for msg in msg_list:
        for phrase in whatsapp_stoplist:
            if phrase in msg:
                break
        else:
            msg_list_clean.append(msg.strip())

    return msg_list_clean


def remove_forwarded(msg_list: list[dict]) -> list[dict]:
    """Filters out forwarded messages
    Args:
        msg_list: List of Telegram messages
    Returns filtered list of messages
    """
    filtered_msg_list = []
    for msg in msg_list:
        if not msg.get("forwarded_from"):
            filtered_msg_list.append(msg)
    return filtered_msg_list


def get_msg_text_list_tg_wa(msg_list: list[dict]) -> list[str]:
    """Parses messages text from the list of message dictionaries
    Args:
        msg_list: List of Telegram messages
    Returns list of text messages
    """
    messages = []
    for msg in msg_list:
        msg_text = msg.get("text")
        if msg_text and type(msg_text) is str:
            messages.append(msg_text)
    return messages


def filter_big_messages(msg_list: list[str]) -> list[str]:
    """Filters messages with more than 55 words
    Args:
        msg_list: List of text messages
    Returns list of text messages
    """
    return list(filter(lambda msg: len(msg.split()) < 56, msg_list))


def remove_emojis(text: str) -> str:
    """Removes emojis from a string"""
    emojis = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002500-\U00002BEF"  # chinese char
        "\U00002702-\U000027B0"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+",
        re.UNICODE,
    )
    return re.sub(emojis, "", text)


def get_words(msg_list_txt: list[str]) -> list[str]:
    """Extracts all the words from a list of strings removing signs and emojis
    Args:
        msg_list_txt: list of strings
    Returns list of words
    """
    all_messages_text = " ".join(msg_list_txt)
    punctuation = '!"#$%&()*+,-./:;<=>?@[]^_`{|}~„“«»†*—/-‘’1234567890'

    clean_text = "".join(char for char in all_messages_text if char not in punctuation)
    clean_text = remove_emojis(clean_text)

    return clean_text.lower().split()


def get_normalized_words_ru(words: list[str]) -> list[str]:
    """Returns only nouns in russian in a normal form, filtering words in a stop-list
    Args:
        words: list of words in russian
    """
    normal_words = []
    for word in words:
        word_analysis = morph.parse(word)[0]
        if (
            word_analysis.tag.POS == "NOUN"
            and word not in stopwords_ru
            and word_analysis.normal_form not in stopwords_ru
            and len(word_analysis.normal_form) > 2
        ):
            normal_words.append(word_analysis.normal_form)

    return normal_words


def get_word_count(word_list: list[str]) -> dict[str:int]:
    """Returns dict of words and associated frequency
    Args:
        word_list: list of words
    """
    word_count = Counter()
    for word in word_list:
        word_count[word] += 1
    return dict(word_count.most_common())


def get_colors_by_size(
    word, font_size, position, orientation, font_path, random_state  # skipcq: PYL-W0613 # noqa
) -> Union[tuple, str]:
    """Returns a color depending on a font size for a WordCloud generating"""
    if font_size > 315:
        color = (200, 0, 255)  # violet
    elif font_size > 150:
        color = (255, 50, 0)  # red
    elif font_size > 85:
        color = "yellow"
    elif font_size > 42:
        color = "orange"
    elif font_size > 31:
        color = (0, 255, 100)  # green
    elif font_size > 22:
        color = "white"
    else:
        color = "cyan"
    return color


def get_pic_from_frequencies(counted_words: dict[str:int]) -> Image:
    """Generates a word cloud picture from words and frequencies
    Args:
        counted_words: dict of words and associated frequency
    Returns a word cloud in a PIL Image format
    """
    wc = WordCloud(
        max_words=200,
        width=1920,
        height=1080,
        collocations=False,
        color_func=get_colors_by_size,
    )
    word_cloud = wc.generate_from_frequencies(counted_words)
    return word_cloud.to_image()


def get_msg_dict_wa(text: str) -> list[dict]:
    """Parses WhatsApp export file
    Args:
        text: WhatsApp export file text
    Returns list of messages
    """
    link_regex = re.compile(
        r"""(?i)\b(?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,6}/)(?:[^\s()<>]+|\((?:[^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’])"""
    )

    msg_pattern = re.compile(
        r"(?P<datetime>\d{1,2}[\/|\.]\d{1,2}[\/|\.]\d{2,4},?\s\d{2}[:|\.]\d{2}(?:[:|\.]\d{2})?(?:\s[APap][Mm])?)\s-\s(?P<sender>\S+|[^:]*):\s(?P<text>.*)"
    )

    msg_list = []

    for line_text in text.splitlines():
        for phrase in whatsapp_stoplist_no_media:
            if phrase in line_text:
                break
        else:
            message = msg_pattern.search(line_text)
            if message:
                msg = {
                    "from": message.group("sender") or "You",
                    "date": message.group("datetime"),
                    "text": message.group("text"),
                    "media_type": None,
                }
                if link_regex.search(line_text):
                    msg["media_type"] = "url"
                    msg["text"] = ""
                elif "Без медиафайлов" in msg["text"] or "Media omitted" in msg["text"]:
                    msg["media_type"] = "media"
                    msg["text"] = ""
                msg_list.append(msg)
            else:
                if msg_list:
                    msg_list[-1]["text"] += "\n" + line_text
    if len(msg_list) < 3:
        raise ValueError("msg_list is too short")
    return msg_list


def df_from_tg(msg_list: list[dict]) -> pd.DataFrame:
    """Makes DataFrame of Telegram messages adding needed info and filtering out service messages
    Args:
        msg_list: List of Telegram messages
    Returns Pandas Dataframe with messages
    """

    df = pd.DataFrame(msg_list)
    df = df[df.type == "message"].drop("type", axis=1).reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df.date)
    df["from"] = df["from"].fillna("Deleted user")
    return df


def df_from_wa(msg_list: list[dict]) -> pd.DataFrame:
    """Makes DataFrame of WhatsApp messages adding needed info
    Args:
        msg_list: List of WhatsApp messages
    Returns Pandas Dataframe with messages
    """

    df = pd.DataFrame(msg_list)
    df["timestamp"] = pd.to_datetime(df["date"], dayfirst=True)
    df.insert(0, "id", np.array(range(0, len(df))))
    return df


def make_general_analysis(msg_list: list[dict], chat_platform: str) -> dict:
    """Returns dict of analyses values
    Args:
        msg_list: List of Telegram messages
        chat_platform: The chat platform name
    """
    if chat_platform == TELEGRAM:
        df = df_from_tg(msg_list)
    elif chat_platform == WHATSAPP:
        df = df_from_wa(msg_list)
    else:
        raise ValueError("Unsupported chat platform")
    df = generate_more_data(df)
    df_unique_seq = df.drop_duplicates(subset=["seq"]).reset_index(drop=True)
    if chat_platform == TELEGRAM:
        df_no_forwarded = df[pd.isna(df["forwarded_from"])].drop("forwarded_from", axis=1).reset_index(drop=True)
    elif chat_platform == WHATSAPP:
        df_no_forwarded = df.query("`text`.str.len() < 230")
    else:
        df_no_forwarded = df

    results = {
        "daily_year_msg": get_daily_msg_amount(df, 365),
        "top_day": get_top_day(df_unique_seq),
        "top_weekday": get_top_weekday(df_unique_seq),
        "hourly_messages": get_avg_for_each_hour(df),
        "msg_per_user": get_msg_count_per_user(df),
        "msg_per_day": get_user_msg_per_day(df),
        "words_per_message": get_words_per_message(df_no_forwarded),
        "media_text_share": get_media_share(df),
        "response_time": get_response_time(df),
        "response_time_hour": get_response_hours(df),
    }
    return results


def generate_more_data(df: pd.DataFrame) -> pd.DataFrame:
    def get_seq(series: pd.Series) -> np.ndarray:
        """Returns count of consequential items that are different from previous"""
        seq = np.zeros(len(series)).astype(int)
        _count = 1
        sender = series[0]
        seq[0] = _count

        for i in range(1, len(series)):
            if series[i] != sender:
                _count += 1
                sender = series[i]
            seq[i] = _count
        return seq

    def get_seq_difference(seq: pd.Series, diff: pd.Series, delta_max: str = "1 day") -> pd.Series:
        """Returns time between different sequences or
        NA if they are the same or time between them is more than delta_max"""
        prev_seq = None
        seq_diff = []
        for row in zip(seq, diff):
            if prev_seq is None:
                prev_seq = row[0]
            if row[0] == prev_seq:
                seq_diff.append(pd.NA)
            else:
                prev_seq = row[0]
                if row[1] < pd.Timedelta(delta_max):
                    seq_diff.append(row[1].seconds)
                else:
                    seq_diff.append(pd.NA)
        return pd.Series(seq_diff)

    df["hour"] = df["timestamp"].dt.hour
    df["date"] = df.timestamp.dt.date
    df["from"] = df["from"].astype("category")
    df["word"] = df["text"].apply(lambda text: len(text.split()) if type(text) is str else 0)
    df["weekday"] = df["timestamp"].dt.day_name()
    df["diff"] = np.insert(np.diff(df["timestamp"]), 0, 0)
    df["seq"] = get_seq(df["from"])
    df["seq_diff"] = get_seq_difference(df["seq"], df["diff"], "5 hours")

    return df


def get_daily_msg_amount(df: pd.DataFrame, days: int = 365) -> dict:
    """Generates data for daily amount of messages chart
    Args:
        df: DataFrame to analyze
        days: amount of days until the final message date
    Returns a dict, where
        values: list[int]: daily number of messages list
        end_date: float: the last day in the unix timestamp format
        average: float: average message amount for all days from the first to the last message in the chat
    """
    daily_msg = df[["timestamp", "id"]].set_index("timestamp").resample("D").count().reset_index()
    end_date = daily_msg.iloc[-1:].timestamp.dt.to_pydatetime()[0].timestamp()
    average_msg_amount = statistics.mean(daily_msg["id"].to_list())
    return {
        "values": daily_msg.iloc[-days:]["id"].to_list(),
        "end_date": end_date,
        "average": average_msg_amount,
    }


def generate_dates(end_date: float, n: int, step_days: int = 1) -> list[str]:
    """Generates dates with specified parameters
    Args:
        end_date: the last day in the unix timestamp format for the generated dates list
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


def get_top_day(df: pd.DataFrame) -> str:
    """Returns date of the highest amount of messages in the format of dd.mm.yyyy"""
    amount_by_date = df[["id", "date", "seq"]].groupby("date").count()
    sorted_dates = amount_by_date.sort_values("id", ascending=False).reset_index()
    return sorted_dates.date[0].strftime("%d.%m.%Y")


def get_top_weekday(df: pd.DataFrame) -> str:
    """Returns name of the weekday with the highest average amount of messages"""
    weekdays = df[["id", "weekday", "seq"]].groupby("weekday").count()
    sorted_weekdays = weekdays.sort_values("id", ascending=False).reset_index()
    return sorted_weekdays.weekday[0]


def get_days_duration(df: pd.DataFrame) -> int:
    """Returns duration of the chat in days"""
    date_start = df[["timestamp"]].iloc[0]
    date_end = df[["timestamp"]].iloc[-1]
    days = int((date_end - date_start).dt.days) + 1
    return days


def get_avg_for_each_hour(df: pd.DataFrame) -> list[float]:
    """Returns list of average amount of messages for each hour from 0 to 23"""
    days = get_days_duration(df)
    hourly_msg_avg = df[["id", "hour", "seq"]].groupby("hour").count()["id"].to_list()
    hourly_msg_avg = [*map(lambda x: round(x / days, 2), hourly_msg_avg)]
    return hourly_msg_avg


def get_msg_count_per_user(df: pd.DataFrame) -> dict:
    """Returns dict containing amount of messages for top 4 users and sum for others"""
    total = len(df)
    users = df["from"].cat.categories.to_list()
    user_msg_count = df[["id", "from"]].groupby("from").count().sort_values("id", ascending=False)
    if len(users) > 5:
        user_msg_count = user_msg_count[:4].to_dict()["id"]
        user_msg_count["others"] = total - sum(user_msg_count.values())
    else:
        user_msg_count = user_msg_count.to_dict()["id"]
    return user_msg_count


def get_user_msg_per_day(df: pd.DataFrame) -> dict:
    """Returns dict containing average amount of messages per day for top-5 users"""
    users = df["from"].cat.categories.to_list()
    average_msg = {}
    for user in users:
        user_messages = df[["timestamp", "id", "from"]][df["from"] == user]
        msg_per_day = user_messages.set_index("timestamp").resample("D").count()["id"].tolist()
        msg_per_day.sort()
        five_perc = int(len(msg_per_day) * 0.05)
        msg_per_day_cut = msg_per_day[five_perc:-five_perc]
        msg_per_day = msg_per_day_cut if msg_per_day_cut else msg_per_day
        average_msg[user] = round(statistics.mean(msg_per_day), 1)
    average_msg = dict(sorted(average_msg.items(), key=lambda item: item[1], reverse=True))
    if len(average_msg) > 5:
        average_msg = {k: average_msg[k] for k in list(average_msg)[:5]}
    return average_msg


def get_words_per_message(df: pd.DataFrame) -> dict:
    """Returns dict containing average amount of words per message for top-5 users"""
    df_without_media = df[df.media_type.isna()].reset_index()
    user_word_count = df_without_media[["from", "word"]].groupby("from").sum("word")
    user_word_count = user_word_count.to_dict()["word"]

    total = df_without_media[["from", "word"]].groupby("from").count().to_dict()["word"]

    for user in list(user_word_count):
        if total[user] == 0:
            user_word_count[user] = 0
            continue
        user_word_count[user] = round(user_word_count[user] / total[user], 2)
    sorted_user_word_count = dict(sorted(user_word_count.items(), key=lambda item: item[1], reverse=True))
    if len(sorted_user_word_count) > 5:
        sorted_user_word_count = {k: sorted_user_word_count[k] for k in list(sorted_user_word_count)[:5]}

    return sorted_user_word_count


def get_media_share(df: pd.DataFrame) -> dict:
    """Returns dict containing the share of text messages and the share of other messages in percents"""
    text_perc = round(100 * df.media_type.isna().sum() / len(df), 2)
    media_perc = round(100 - text_perc, 2)
    return {"text": text_perc, "media": media_perc}


def get_response_time(df: pd.DataFrame) -> dict:
    """Returns dict containing average time (in seconds) between messages from different users for top-5 users"""
    answer_time = df[["from", "seq_diff"]].groupby("from").seq_diff.apply(np.mean)
    return answer_time.sort_values()[:5].to_dict()


def get_response_hours(df: pd.DataFrame) -> dict[str:int]:
    """Returns dict containing start and end hours for the fastest response time."""
    answer_time = df[["hour", "seq_diff"]].groupby("hour").seq_diff.apply(np.mean)
    answer_time = answer_time.sort_values()
    hour_list = answer_time.index

    hot_hours = []
    for hour in hour_list:
        if not hot_hours:
            hot_hours.append(hour)
            continue
        for prev_hour in hot_hours:
            if prev_hour == 23:
                if hour in (22, 0):
                    hot_hours.append(hour)
                    break
            elif prev_hour == 0:
                if hour in (23, 1):
                    hot_hours.append(hour)
                    break
            else:
                if hour in (prev_hour - 1, prev_hour + 1):
                    hot_hours.append(hour)
                    break
        else:
            break
    hot_hours = hot_hours[:5]

    hot_hours = sorted(hot_hours)

    if 0 in hot_hours and 23 in hot_hours:
        lower = filter(lambda h: h >= 12, hot_hours)
        higher = filter(lambda h: h < 12, hot_hours)
        hot_hours = [*lower, *higher]

    return {"start": hot_hours[0], "end": hot_hours[-1] + 1}
