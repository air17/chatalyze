import datetime
import json
import re
import statistics
from collections import Counter
from io import BytesIO
import pandas as pd
import numpy as np

from PIL.Image import Image
from django.core.files.images import ImageFile
from django.utils import timezone
from wordcloud import WordCloud
from pymorphy2 import MorphAnalyzer

from .const import TELEGRAM, WHATSAPP
from .models import ChatAnalysis
from .stopwords import whatsapp_stoplist, stopwords_ru, stopwords_en

morph = MorphAnalyzer()


def explain_error(analysis, e=None, message=None):
    analysis.refresh_from_db()
    analysis.status = analysis.AnalysisStatus.ERROR
    analysis.error_text = message if message else "Couldn't process your file"
    analysis.save()
    if e:
        raise Exception from e
    else:
        raise Exception(message)


def read_tg_file(path):
    with open(path, "r", encoding="UTF8") as f:
        return json.load(f)


def analyze_tg(analysis):
    try:
        chat_history = read_tg_file(analysis.chat_file.path)

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

        try:
            results = make_general_analysis(msg_list)
        except Exception as e:
            explain_error(analysis, e, "Couldn't make analysis. Some error.")
        else:
            analysis.results = json.dumps(results)
            analysis.save()

            make_wordcloud(msg_list, analysis)


def update_tg(analysis):
    try:
        chat_history = read_tg_file(analysis.chat_file.path)

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

        results = make_general_analysis(msg_list)
        analysis.results = json.dumps(results)
        analysis.save()

        make_wordcloud(msg_list, analysis)


def analyze_wa(analysis):
    try:
        with open(analysis.chat_file.path, "r", encoding="UTF8") as f:
            text = f.read()
        msg_list = get_msg_text_list_wa(text)
    except ValueError as e:
        explain_error(analysis, e, "File format is wrong or this WhatsApp localization is not supported yet.")
    except Exception as e:
        explain_error(analysis, e, "File format is wrong")
    else:
        analysis.messages_count = len(msg_list)
        analysis.chat_platform = WHATSAPP
        analysis.save()

        make_wordcloud(msg_list, analysis)


def make_wordcloud(raw_messages, analysis):
    if analysis.chat_platform == TELEGRAM:
        msg_list_direct = remove_forwarded(raw_messages)
        msg_list_txt = get_msg_text_list_tg(msg_list_direct)
    else:
        msg_list_txt = raw_messages

    try:
        filtered_msg_list_txt = filter_big_messages(msg_list_txt)

        words_list = get_words(filtered_msg_list_txt)

        if analysis.language == analysis.AnalysisLanguage.RUSSIAN:
            normal_words = get_normalized_words_ru(words_list)

            # change the normal form of the word with a more common form
            normal_words = [word if word != "деньга" else "деньги" for word in normal_words]

            counted_words = get_word_count(normal_words)
            wordcloud_pic = get_pic_from_frequencies(counted_words)
        elif analysis.language == analysis.AnalysisLanguage.ENGLISH:
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

    except Exception as e:
        explain_error(analysis, e, "Couldn't build a wordcloud of your chat.")
    else:
        analysis.word_cloud_pic = pic_to_imgfile(wordcloud_pic, "wc.png")
        analysis.status = analysis.AnalysisStatus.READY
        analysis.updated = timezone.now()
        analysis.save()


def pic_to_imgfile(pic: Image, name="output.png", ext=None) -> ImageFile:
    """Saves PIL image to Django ImageFile which can be assigned to ImageField."""
    if not ext:
        name_split = name.split(".")
        ext = name_split[-1].upper() if len(name_split) > 1 else "PNG"
    output = BytesIO()
    pic.save(output, format=ext)
    return ImageFile(output, name=name)


def get_chat_name_wa(filename: str) -> str:
    """Extracts chat name from WhatsApp exported file name. Returns chat name or empty string on failure."""
    name_regex_ru = re.search(r"Чат WhatsApp с (.*)\.txt$", filename)
    name_regex_en = re.search(r"WhatsApp Chat with (.*)\.txt$", filename)
    if name_regex_ru:
        return name_regex_ru.group(1)
    elif name_regex_en:
        return name_regex_en.group(1)
    else:
        return ""


def get_msg_text_list_wa(text: str) -> list:
    msg_list1 = re.split(r"\n*\d+/\d+/\d+, \d+:\d+ - \S+: ", text)
    msg_list2 = re.split(r"\n*\d+.\d+.\d+, \d+:\d+ - [^:]*: ", text)
    msg_list = msg_list1 if len(msg_list1) > len(msg_list2) else msg_list2
    if len(msg_list) < 3:
        raise ValueError("msg_list is too short")

    msg_list_clean = []
    link_regex = re.compile(
        r"https?://(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_+.~#?&/=]*"
    )

    for msg in msg_list:
        for phrase in whatsapp_stoplist:
            if phrase in msg:
                break
        else:
            if not link_regex.search(msg):
                msg_list_clean.append(msg.strip())

    return msg_list_clean


def remove_forwarded(msg_list: list) -> list:
    filtered_msg_list = []
    for msg in msg_list:
        if not msg.get("forwarded_from"):
            filtered_msg_list.append(msg)
    return filtered_msg_list


def get_msg_text_list_tg(msg_list: list) -> list:
    messages = []
    for msg in msg_list:
        msg_text = msg.get("text")
        if msg_text and type(msg_text) is str:
            messages.append(msg_text)
    return messages


def filter_big_messages(msg_list: list) -> list:
    # filtering messages with more than 55 words
    return list(filter(lambda msg: len(msg.split()) < 56, msg_list))


def remove_emojis(text: str) -> str:
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


def get_words(msg_list_txt: list) -> list:
    all_messages_text = " ".join(msg_list_txt)
    punct = '!"#$%&()*+,-./:;<=>?@[]^_`{|}~„“«»†*—/-‘’1234567890'

    clean_text = "".join(char for char in all_messages_text if char not in punct)
    clean_text = remove_emojis(clean_text)

    return clean_text.lower().split()


def get_normalized_words_ru(words: list) -> list:
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


def get_word_count(word_list: list) -> dict:
    word_count = Counter()
    for word in word_list:
        word_count[word] += 1
    return dict(word_count.most_common())


def get_colors_by_size(word, font_size, position, orientation, font_path, random_state) -> tuple:  # skipcq: PYL-W0613
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


def get_pic_from_frequencies(counted_words: dict) -> Image:
    wc = WordCloud(
        max_words=200,
        width=1920,
        height=1080,
        collocations=False,
        color_func=get_colors_by_size,
    )
    word_cloud = wc.generate_from_frequencies(counted_words)
    return word_cloud.to_image()


def df_from_tg(msg_list):
    def get_seq(series):  # get chat sequences.
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

    def get_seq_difference(seq, diff, delta_max="1 day"):
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

    df = pd.DataFrame(msg_list)
    df = df[df.type == "message"].drop("type", axis=1).reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df.date)
    df["hour"] = df["timestamp"].dt.hour
    df["date"] = df.timestamp.dt.date
    df["from"] = df["from"].fillna("Deleted user")
    df["from"] = df["from"].astype("category")
    df["word"] = df["text"].apply(lambda text: len(text.split()) if type(text) == str else 0)
    df["weekday"] = df["timestamp"].dt.day_name()
    df["diff"] = np.insert(np.diff(df["timestamp"]), 0, 0)
    df["seq"] = get_seq(df["from"])
    df["seq_diff"] = get_seq_difference(df["seq"], df["diff"], "5 hours")
    return df


def make_general_analysis(msg_list):
    df = df_from_tg(msg_list)
    df_unique_seq = df.drop_duplicates(subset=["seq"]).reset_index(drop=True)
    df_no_forwarded = df[pd.isna(df["forwarded_from"])].drop("forwarded_from", axis=1).reset_index(drop=True)

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


def get_daily_msg_amount(df: pd.DataFrame, days: int = 365):
    # msgAmountYear; график: количество сообщений(y) от дня(x) (за всю ситорию чата)
    daily_msg = df[["timestamp", "id"]].set_index("timestamp").resample("D").count().reset_index()
    end_date = daily_msg.iloc[-1:].timestamp.dt.to_pydatetime()[0].timestamp()
    average_msg_amount = statistics.mean(daily_msg["id"].to_list())
    return {
        "values": daily_msg.iloc[-days:]["id"].to_list(),
        "end_date": end_date,
        "average": average_msg_amount,
    }


def generate_dates(end_date: float, n: int, step_days: int = 1) -> list:
    # generate n days till end date
    # n = len(msg_amount)
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
    amount_by_date = df[["id", "date", "seq"]].groupby("date").count()
    sorted_dates = amount_by_date.sort_values("id", ascending=False).reset_index()
    return sorted_dates.date[0].strftime("%d.%m.%Y")


def get_top_weekday(df):
    weekdays = df[["id", "weekday", "seq"]].groupby("weekday").count()
    sorted_weekdays = weekdays.sort_values("id", ascending=False).reset_index()
    return sorted_weekdays.weekday[0]


def get_days_duration(df):
    date_start = df[["timestamp"]].iloc[0]
    date_end = df[["timestamp"]].iloc[-1]
    days = int((date_end - date_start).dt.days) + 1
    return days


def get_avg_for_each_hour(df):
    days = get_days_duration(df)
    hourly_msg_avg = df[["id", "hour", "seq"]].groupby("hour").count()["id"].to_list()
    hourly_msg_avg = [*map(lambda x: round(x / days, 2), hourly_msg_avg)]
    return hourly_msg_avg


def get_msg_count_per_user(df: pd.DataFrame) -> dict:
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


def get_words_per_message(df) -> dict:
    # average word per message
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


def get_media_share(df) -> dict:
    text_perc = round(100 * df.media_type.isna().sum() / len(df), 2)
    media_perc = round(100 - text_perc, 2)
    return {"text": text_perc, "media": media_perc}


def get_response_time(df) -> dict:
    answer_time = df[["from", "seq_diff"]].groupby("from").seq_diff.apply(np.mean)
    return answer_time.sort_values()[:5].to_dict()


def get_response_hours(df) -> dict:
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
                if hour == 0 or hour == 22:
                    hot_hours.append(hour)
                    break
            elif prev_hour == 0:
                if hour == 23 or hour == 1:
                    hot_hours.append(hour)
                    break
            else:
                if prev_hour - 1 == hour or prev_hour + 1 == hour:
                    hot_hours.append(hour)
                    break
        else:
            break
    hot_hours = hot_hours[:5]

    hot_hours = sorted(hot_hours)

    if 0 in hot_hours and 23 in hot_hours:
        lower = filter(lambda x: x >= 12, hot_hours)
        higher = filter(lambda x: x < 12, hot_hours)
        hot_hours = [*lower, *higher]

    return {"start": hot_hours[0], "end": hot_hours[-1] + 1}
