import re
from typing import Union
from wordcloud import WordCloud
from pymorphy2 import MorphAnalyzer
from PIL.Image import Image
from collections import Counter

from ..utils import ProgressBar
from ..const import TELEGRAM, WHATSAPP, FACEBOOK
from ..models import ChatAnalysis
from .stopwords import whatsapp_stoplist, get_stopwords_for

morph = MorphAnalyzer()


def make_wordcloud(raw_messages: list, chat_platform: str, language: str, progress: ProgressBar) -> Image:
    """Produces wordcloud for provided messages
    Args:
        raw_messages: list of messages in a format of message service
        chat_platform: Name of chat platform
        language: Language of messages
        progress: Task progress object
    Returns a WordCloud in a PIL Image format
    """
    if chat_platform == TELEGRAM:
        msg_list_direct = remove_forwarded(raw_messages)
        msg_list_txt = get_msg_text_list(msg_list_direct)
    elif chat_platform == WHATSAPP:
        msg_list_txt = get_msg_text_list(raw_messages)
        msg_list_txt = filter_whatsapp_messages(msg_list_txt)
    elif chat_platform == FACEBOOK:
        msg_list_txt = filter_facebook_messages(raw_messages)
        msg_list_txt = get_msg_text_list(msg_list_txt, text_key="content")
    else:
        raise ValueError("Wrong chat platform")

    filtered_msg_list_txt = filter_big_messages(msg_list_txt)

    words_list = get_words(filtered_msg_list_txt)

    progress.value = 53
    if language == ChatAnalysis.AnalysisLanguage.RUSSIAN:
        normal_words = get_normalized_words_ru(words_list, progress)
        progress.value = 85

        # change the normal form of the word with a more common form
        normal_words = [word if word != "деньга" else "деньги" for word in normal_words]

        counted_words = get_word_count(normal_words)
        progress.value = 90
        wordcloud_pic = get_pic_from_frequencies(counted_words)
    else:
        if language == ChatAnalysis.AnalysisLanguage.ENGLISH:
            stopwords = get_stopwords_for("english")
        elif language == ChatAnalysis.AnalysisLanguage.UKRAINIAN:
            stopwords = get_stopwords_for("ukrainian")
        elif language == ChatAnalysis.AnalysisLanguage.UKRAINIAN_RUSSIAN:
            stopwords = get_stopwords_for("ukrainian") + get_stopwords_for("russian")
        else:
            raise ValueError("Wrong language")

        wc = WordCloud(
            max_words=200,
            width=1920,
            height=1080,
            color_func=get_colors_by_size,
            stopwords=stopwords,
            collocation_threshold=3,
            min_word_length=3,
        )
        word_cloud = wc.generate(" ".join(filtered_msg_list_txt))
        wordcloud_pic = word_cloud.to_image()

    return wordcloud_pic


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


def filter_facebook_messages(msg_list: list[dict]) -> list[dict]:
    """Removes Facebook service messages
    Args:
        msg_list: List of Telegram messages
    Returns filtered list of messages
    """
    filtered_msg_list = []
    for msg in msg_list:
        if msg.get("type") == "Generic":
            filtered_msg_list.append(msg)
    return filtered_msg_list


def get_msg_text_list(msg_list: list[dict], text_key: str = "text") -> list[str]:
    """Parses messages text from the list of message dictionaries
    Args:
        msg_list: List of Telegram or WhatsApp messages
        text_key: Message text key name in the dicts
    Returns list of text messages
    """
    messages = []
    for msg in msg_list:
        msg_text = msg.get(text_key)
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


def get_normalized_words_ru(words: list[str], progress: ProgressBar) -> list[str]:
    """Returns only nouns in russian in a normal form, filtering words in a stop-list
    Args:
        words: list of words in russian
        progress: task progress tracking object
    """
    normal_words = []
    progress_total = len(words)
    progress_current = 0
    init_percent = progress.value
    stopwords_ru = get_stopwords_for("russian")
    for word in words:
        progress_current += 1
        word_analysis = morph.parse(word)[0]
        progress.value = init_percent + int(32 * progress_current / progress_total)
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


# skipcq: PYL-W0613
def get_colors_by_size(word, font_size, position, orientation, font_path, random_state) -> Union[tuple, str]:  # noqa
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
