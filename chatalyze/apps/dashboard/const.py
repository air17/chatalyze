TELEGRAM = "Telegram"
WHATSAPP = "WhatsApp"

_date_formats = (
    "%d.%m.%y",
    "%m.%d.%y",
    "%d.%m.%Y",
    "%m.%d.%Y",
    "%y.%m.%d",
    "%y.%d.%m",
    "%m/%d/%y",
    "%d/%m/%y",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%y/%d/%m",
    "%y/%m/%d",
)
_time_formats = (
    ", %H:%M",
    ", %H:%M:%S",
    " %H:%M",
    " %H:%M:%S",
    ", %H.%M",
    ", %H.%M.%S",
    " %H.%M",
    " %H.%M.%S",
    ", %H:%M %p",
    ", %H:%M:%S %p",
    " %H:%M %p",
    " %H:%M:%S %p",
    ", %H.%M %p",
    ", %H.%M.%S %p",
    " %H.%M %p",
    " %H.%M.%S %p",
    ", %H:%M%p",
    ", %H:%M:%S%p",
    " %H:%M%p",
    " %H:%M:%S%p",
    ", %H.%M%p",
    ", %H.%M.%S%p",
    " %H.%M%p",
    " %H.%M.%S%p",
)
DATETIME_FORMATS = []
for d in _date_formats:
    for t in _time_formats:
        DATETIME_FORMATS.append(d + t)
DATETIME_FORMATS = tuple(DATETIME_FORMATS)
