import json
import re
from collections import Counter
from io import BytesIO

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


def analyze_tg(analysis):
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

        make_wordcloud(msg_list, analysis)


def update_tg(analysis):
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
