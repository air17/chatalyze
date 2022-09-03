import statistics
from datetime import datetime
import re
import numpy as np
import pandas as pd
from typing import Sequence, Optional

from apps.dashboard.const import TELEGRAM, WHATSAPP, FACEBOOK, DATETIME_FORMATS
from .stopwords import whatsapp_stoplist_except_media
from apps.dashboard.utils import ProgressBar


def make_general_analysis(msg_list: list[dict], chat_platform: str, progress: ProgressBar) -> dict:
    """Returns dict of analyses values
    Args:
        msg_list: List of Telegram messages
        chat_platform: The chat platform name
        progress: Task progress object
    """
    if chat_platform == TELEGRAM:
        df = df_from_tg(msg_list)
    elif chat_platform == WHATSAPP:
        df = df_from_wa(msg_list)
    elif chat_platform == FACEBOOK:
        df = df_from_fb(msg_list)
    else:
        raise ValueError("Unsupported chat platform")
    progress.value = 20
    df = generate_more_data(df)
    df_unique_seq = df.drop_duplicates(subset=["seq"]).reset_index(drop=True)
    if chat_platform == TELEGRAM and "forwarded_from" in df:
        df_no_forwarded = df[pd.isna(df["forwarded_from"])].drop("forwarded_from", axis=1).reset_index(drop=True)
    elif chat_platform == WHATSAPP:
        df_no_forwarded = df.query("`text`.str.len() < 230")
    else:
        df_no_forwarded = df
    progress.value = 35

    daily_year_msg = get_daily_msg_amount(df, 365)
    top_day = get_top_day(df_unique_seq)
    top_weekday = get_top_weekday(df_unique_seq)
    hourly_messages = get_avg_for_each_hour(df)
    msg_per_user = get_msg_count_per_user(df)
    progress.value += 5
    msg_per_day = get_user_msg_per_day(df)
    progress.value += 5
    words_per_message = get_words_per_message(df_no_forwarded)
    media_text_share = get_media_share(df)
    response_time = get_response_time(df)
    response_time_hour = get_response_hours(df)
    results = {
        "daily_year_msg": daily_year_msg,
        "top_day": top_day,
        "top_weekday": top_weekday,
        "hourly_messages": hourly_messages,
        "msg_per_user": msg_per_user,
        "msg_per_day": msg_per_day,
        "words_per_message": words_per_message,
        "media_text_share": media_text_share,
        "response_time": response_time,
        "response_time_hour": response_time_hour,
    }
    return results


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
        r"(?P<datetime>\d{1,2}[\/|\.]\d{1,2}[\/|\.]\d{2,4},?\s\d{2}[:|\.]\d{2}(?:[:|\.]\d{2})?(?:\s?[APap][Mm])?)\s-\s(?P<sender>\S+|[^:]*):\s(?P<text>.*)"
    )

    msg_list = []

    for line_text in text.splitlines():
        for phrase in whatsapp_stoplist_except_media:
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
    df["from"] = df["from"].fillna(df["from_id"])
    if "media_type" not in df:
        df.insert(-1, "media_type", np.nan)
    return df


def detect_datetime_format(date_list: Sequence[str]) -> Optional[str]:
    """Guesses datetime format suitable for all dates
    Args:
        date_list: dates list of any iterable type
    Returns datetime format that is common for all dates in the list. If fails to guess format returns None.
    """
    if len(date_list) > 200:
        total = len(date_list)
        new_date_list = [
            *date_list[:50],
            *date_list[int(0.5 * total - 25) : int(0.5 * total + 25)],
            *date_list[-50:],
        ]
        date_list = new_date_list
    detected_formats: list[set] = []
    for date in date_list:
        possible_formats = set()
        for dt_format in DATETIME_FORMATS:
            try:
                dt = datetime.strptime(date, dt_format)
            except ValueError:
                pass
            else:
                if dt < datetime.now() and dt.year >= 2009:  # WhatsApp was released in 2009
                    possible_formats.add(dt_format)
        if not possible_formats:
            return
        detected_formats.append(possible_formats)
    last_format = detected_formats.pop()
    result = last_format.intersection(*detected_formats)
    if len(result) == 1:
        return result.pop()
    else:
        return


def df_from_wa(msg_list: list[dict]) -> pd.DataFrame:
    """Makes DataFrame of WhatsApp messages adding needed info
    Args:
        msg_list: List of WhatsApp messages
    Returns Pandas Dataframe with messages
    """

    df = pd.DataFrame(msg_list)
    df["timestamp"] = pd.to_datetime(df["date"], format=detect_datetime_format(df.date))
    df.insert(0, "id", np.array(range(0, len(df))))
    return df


def df_from_fb(msg_list):
    df = pd.DataFrame(msg_list)
    df = df.iloc[::-1]
    df = df[(df["type"] == "Generic")].drop("type", axis=1).reset_index(drop=True)
    df["media_type"] = np.where(df["content"].isna(), "media", pd.NA)  # noqa
    df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms")
    df.rename(columns={"sender_name": "from", "content": "text"}, inplace=True)
    df.insert(0, "id", np.array(range(0, len(df))))
    return df


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
    df["weekday"] = df["timestamp"].dt.weekday
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


def get_top_day(df: pd.DataFrame) -> str:
    """Returns date of the highest amount of messages in the format of dd.mm.yyyy"""
    amount_by_date = df[["id", "date", "seq"]].groupby("date").count()
    sorted_dates = amount_by_date.sort_values("id", ascending=False).reset_index()
    return sorted_dates.date[0].strftime("%d.%m.%Y")


def get_top_weekday(df: pd.DataFrame) -> int:
    """Returns name of the weekday with the highest average amount of messages"""
    weekdays = df[["id", "weekday", "seq"]].groupby("weekday").count()
    sorted_weekdays = weekdays.sort_values("id", ascending=False).reset_index()
    return int(sorted_weekdays.weekday[0])


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
    df_without_media = df[df["media_type"].isna()].reset_index()
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
