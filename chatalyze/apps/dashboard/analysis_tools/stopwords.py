from os import path

whatsapp_stoplist_except_media = (
    "Пропущенный аудиозвонок",
    "Пропущенный видеозвонок",
    "Missed voice call",
    "Missed video",
    "защищены сквозным шифрованием",
    "No one outside of this chat, not even WhatsApp",
    "Messages to this chat and calls are now secured",
    "Данное сообщение удалено",
    "Вы удалили данное сообщение",
    "deleted this message",
    "was deleted",
    "Your security code with",
)

whatsapp_stoplist = (
    "Без медиафайлов",
    "Media omitted",
) + whatsapp_stoplist_except_media


def get_stopwords_for(language: str):
    filename = language + ".txt"
    file_path = path.join("apps", "dashboard", "analysis_tools", "stopwords", filename)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.readlines()
