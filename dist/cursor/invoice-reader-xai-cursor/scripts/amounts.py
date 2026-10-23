"""Turn a readable amount into a Decimal using the configured notation convention.

English number format only: "," groups thousands and "." marks decimals.
"""

import re
from decimal import Decimal

_CURRENCY = re.compile(r"HK\$|US\$|NZ\$|[SAC]\$|[$£€¥₹]|\b[A-Za-z]{3}\b|\bRM\b")
_CREDIT_SUFFIX = re.compile(r"\s*\b(CR|DR)\.?$", re.IGNORECASE)
_GROUPED = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")
_PLAIN = re.compile(r"^(\d+(\.\d+)?|\.\d+)$")
AMOUNT_DASH_CHOICES = ('auto', 'unknown', 'end-mark', 'negative')
AMOUNT_ORIGINS = ('handwritten', 'computer-generated', 'unknown')
DEFAULT_AMOUNT_DASH = 'auto'


def parse_amount(printed, *, cheque_amount=False, trailing_dash=DEFAULT_AMOUNT_DASH, origin='unknown'):
    """Return (Decimal or None, status).

    status is "blank", "ok", "ambiguous" or "unreadable". A blank input stays blank; it never
    becomes zero. "(1,234.50)" and "1,234.50 CR" are negative.
    In auto mode, one terminal ASCII dash is a positive ending only when this
    amount's notation is identified as handwritten. Other origins stay ambiguous.
    Explicit conventions override auto. None disables this amount-only rule.
    """
    if trailing_dash is not None and trailing_dash not in AMOUNT_DASH_CHOICES:
        raise ValueError('Unknown trailing amount dash convention')
    if origin not in AMOUNT_ORIGINS:
        raise ValueError('Unknown amount notation origin')
    if trailing_dash == 'auto':
        trailing_dash = 'end-mark' if origin == 'handwritten' else 'unknown'
    if printed is None or not str(printed).strip():
        return None, "blank"
    text = str(printed).strip()
    if trailing_dash is not None and text.endswith('-'):
        unsigned = _CURRENCY.sub('', text[:-1]).replace(' ', '')
        if _GROUPED.fullmatch(unsigned) or _PLAIN.fullmatch(unsigned):
            if trailing_dash == 'unknown':
                return None, 'ambiguous'
            value = Decimal(unsigned.replace(',', ''))
            return (-value if trailing_dash == 'negative' else value), 'ok'
    # Only the cheque amount field admits a terminal stroke. Never strip an
    # internal slash (fractions/rates), or apply this to quantities/invoice totals.
    if cheque_amount and text.endswith('/'):
        text = text[:-1].rstrip()

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
