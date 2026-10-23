"""Which sheet each document type goes on: the defaults, and the user's custom.md."""

import re
import tomllib
from pathlib import Path

DATA = Path(__file__).parent / "data"

# Bucket (sheet) -> the shape of document it holds. Billing and Reference documents
# share the invoice shape, so a type can move between them; a cheque can't become a bill.
BUCKETS = {
    "Billing documents": "invoice",
    "Reference documents": "invoice",
    "Payments": "payment",
    "Other": "other",
}
UNSURE = "Unsure"

_CONFIRMED = re.compile(r"^Confirmed by user:\s*(yes|no)\s*$", re.IGNORECASE | re.MULTILINE)
_SECTION = "## Document buckets"

TEMPLATE = """# Invoice reader settings

Tell the agent what you want to find and how you will use it. It maintains this file for you.
Requested fields can describe any printed information, including certificate measurements.
They cannot change the rules against guessing values or correcting the original.

Confirmed by user: {confirmed}

## Purpose

Review the document information requested by the user.

## Requested fields

| Key | Column | Find | Values | Required |
|---|---|---|---|---|

An empty table uses the standard document columns. Values is one or many; Required is yes or no.
Keep printed units and evidence. Use semicolons instead of vertical bars inside table cells.

{section}

| Document type | Bucket |
|---|---|
{rows}

Buckets: Billing documents, Reference documents, Payments, Other.
Any document type not listed here, and any document the reader is unsure about, goes on Other.
"""


class CustomError(Exception):
    """A problem in custom.md, explained for the person reading it."""


def default_types():
    with open(DATA / "document-types.toml", "rb") as f:
        return tomllib.load(f)["type"]


def default_text(confirmed=False):
    rows = "\n".join(f"| {t['name']} | {t['bucket']} |" for t in default_types())
    return TEMPLATE.format(confirmed="yes" if confirmed else "no", section=_SECTION, rows=rows)


def default_mapping():
    return {t["name"]: t["bucket"] for t in default_types()}


def read_custom(path):
    """Return (mapping of document type -> bucket, confirmed)."""
    text = Path(path).read_text(encoding="utf-8")
    confirmed = _CONFIRMED.search(text)
    if _SECTION not in text:
        raise CustomError(f"'{Path(path).name}' has no '{_SECTION}' section.")
    shapes = {t["name"].casefold(): t["shape"] for t in default_types()}
    known = {t["name"].casefold(): t["name"] for t in default_types()}
    mapping = default_mapping()
    seen = set()
    for line in text.split(_SECTION, 1)[1].splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if seen:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 2 or cells[0].casefold() == "document type" or set(cells[0]) <= {"-", ":"}:
            continue
        name, bucket = cells
        bucket = next((b for b in BUCKETS if b.casefold() == bucket.casefold()), None)
        if bucket is None:
            raise CustomError(f"'{cells[1]}' (for {name}) isn't a bucket. Use one of: {', '.join(BUCKETS)}.")
        if name.casefold() in seen:
            raise CustomError(f"'{name}' is listed twice.")
        seen.add(name.casefold())
        if name.casefold() == UNSURE.casefold() and bucket != "Other":
            raise CustomError("Documents the reader is unsure about always go on Other.")
        shape = shapes.get(name.casefold())
        if shape and BUCKETS[bucket] != shape:
            allowed = [b for b, s in BUCKETS.items() if s == shape]
            raise CustomError(
                f"{name} can't go on {bucket}: its details don't fit that sheet. "
                f"It can go on: {', '.join(allowed)}.")
        mapping[known.get(name.casefold(), name)] = bucket
    return mapping, bool(confirmed and confirmed[1].lower() == "yes")


def place(document_type, mapping):
    """Return (bucket, shape) for a document type. Unknown types and Unsure go on Other."""
    for name, bucket in mapping.items():
        if name.casefold() == str(document_type).casefold():
            return bucket, BUCKETS[bucket]
    return "Other", "other"
