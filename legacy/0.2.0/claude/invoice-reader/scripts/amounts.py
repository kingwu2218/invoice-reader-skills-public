"""Turn an amount as printed into a Decimal, without guessing.

English number format only: "," groups thousands and "." marks decimals.
"""

import re
from decimal import Decimal

_CURRENCY = re.compile(r"HK\$|US\$|NZ\$|[SAC]\$|[$£€¥₹]|\b[A-Za-z]{3}\b|\bRM\b")
_CREDIT_SUFFIX = re.compile(r"\s*\b(CR|DR)\.?$", re.IGNORECASE)
_GROUPED = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")
_PLAIN = re.compile(r"^(\d+(\.\d+)?|\.\d+)$")


def parse_amount(printed):
    """Return (Decimal or None, status).

    status is "blank", "ok" or "unreadable". A blank input stays blank; it never
    becomes zero. "(1,234.50)" and "1,234.50 CR" are negative.
    """
    if printed is None or not str(printed).strip():
        return None, "blank"
    text = str(printed).strip()

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1]
    if match := _CREDIT_SUFFIX.search(text):
        negative = negative or match[1].upper() == "CR"
        text = text[: match.start()]

    text = _CURRENCY.sub("", text).replace(" ", "")
    if text.startswith("-"):
        negative, text = not negative, text[1:]
    elif text.startswith("+"):
        text = text[1:]
    text = _CURRENCY.sub("", text)

    if _GROUPED.match(text):
        text = text.replace(",", "")
    elif not _PLAIN.match(text):
        return None, "unreadable"
    value = Decimal(text)
    return (-value if negative else value), "ok"
