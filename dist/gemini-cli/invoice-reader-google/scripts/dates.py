"""Turn a date as printed into a date, and say when it can't be done safely."""

import re
from datetime import date

_MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july",
                "august", "september", "october", "november", "december"]
_MONTHS = {name: number for number, name in enumerate(_MONTH_NAMES, start=1)}
_MONTHS.update({name[:3]: number for name, number in list(_MONTHS.items())})
_MONTHS["sept"] = 9

_ORDINAL = re.compile(r"(\d)(st|nd|rd|th)\b")
_ISO = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
_NUMERIC = re.compile(r"^(\d{1,2})[-/. ](\d{1,2})[-/. ](\d{2}|\d{4})$")
_DAY_MONTH_YEAR = re.compile(r"^(\d{1,2})[ \-/.]+([a-z]+)\.?[ \-/.]+(\d{2}|\d{4})$")
_MONTH_DAY_YEAR = re.compile(r"^([a-z]+)\.?[ \-/.]+(\d{1,2})[ ]+(\d{2}|\d{4})$")

DATE_ORDERS = ("Day/Month/Year", "Month/Day/Year")


def _year(text):
    return int(text) + 2000 if len(text) == 2 else int(text)


def _result(year, month, day):
    try:
        return date(year, month, day), "ok"
    except (TypeError, ValueError):
        return None, "unreadable"


def parse_date(printed, date_order=None):
    """Return (date or None, status).

    status is "blank", "ok", "ambiguous" or "unreadable". date_order is one of
    DATE_ORDERS from the company profile, or None when the profile doesn't say.
    """
    if printed is None or not str(printed).strip():
        return None, "blank"
    text = _ORDINAL.sub(r"\1", str(printed).lower()).replace(",", " ")
    text = " ".join(text.split())

    if match := _ISO.match(text):
        return _result(int(match[1]), int(match[2]), int(match[3]))
    if match := _DAY_MONTH_YEAR.match(text):
        return _result(_year(match[3]), _MONTHS.get(match[2]), int(match[1]))
    if match := _MONTH_DAY_YEAR.match(text):
        return _result(_year(match[3]), _MONTHS.get(match[1]), int(match[2]))

    if match := _NUMERIC.match(text):
        first, second, year = int(match[1]), int(match[2]), _year(match[3])
        if date_order == "Day/Month/Year":
            return _result(year, second, first)
        if date_order == "Month/Day/Year":
            return _result(year, first, second)
        day_first, _ = _result(year, second, first)
        month_first, _ = _result(year, first, second)
        if day_first and month_first and day_first != month_first:
            return None, "ambiguous"
        value = day_first or month_first
        return (value, "ok") if value else (None, "unreadable")

    return None, "unreadable"
