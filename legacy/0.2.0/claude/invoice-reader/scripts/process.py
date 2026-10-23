# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Check the extracted data, sort it into buckets, flag what needs a look, and write the workbook.

Usage:
  uv run process.py --extraction FILE_OR_FOLDER --out invoices.xlsx
                    [--profile company-profile.xlsx] [--custom custom.md] [--model-reported MODEL_ID]
"""

import argparse
import json
import sys
import tomllib
from datetime import date
from pathlib import Path

import workbook
from amounts import parse_amount
from buckets import BUCKETS, CustomError, default_mapping, place, read_custom
from checks import FAILED, NOT_CHECKABLE, PASSED, check_document, check_line
from company_profile import PURCHASE, SALES, ProfileError, direction, load_columns, read_profile
from dates import parse_date

DATA = Path(__file__).parent / "data"
MONEY_IN, MONEY_OUT = "Money in", "Money out"
_EXTRA_KEYS = {"unclear"}


class ExtractionError(Exception):
    """A problem in the extraction file, explained so the reading step can fix it."""


def _load_toml(name):
    with open(DATA / name, "rb") as f:
        return tomllib.load(f)


class Reasons:
    """Collects review reasons for one row as '<column labels>: <message>' lines."""

    def __init__(self, catalogue, labels):
        self.catalogue, self.labels, self.lines = catalogue, labels, []

    def add(self, reason_id, fields=None, **values):
        entry = self.catalogue[reason_id]
        keys = fields if entry["columns"] == "field" else entry["columns"]
        if fields is not None and entry["columns"] != "field":
            keys = [k for k in keys if k in fields]
        message = entry["message"].format(**values)
        prefix = ", ".join(self.labels[k] for k in keys if k in self.labels)
        line = f"{prefix}: {message}" if prefix else message[:1].upper() + message[1:]
        if line not in self.lines:
            self.lines.append(line)

    def text(self):
        return "\n".join(self.lines)


def _parse_fields(raw, specs, date_order, reasons, unclear):
    """Turn printed values into typed values. Returns (row values, parsed values)."""
    row, parsed = {}, {}
    for key, spec in specs.items():
        printed = raw.get(key)
        printed = None if printed is None else str(printed).strip()
        if key in unclear:
            # An unclear value is never kept: it stays blank and is flagged.
            reasons.add("unclear", [key])
            printed = None
        if not printed:
            row[key] = None
            parsed[key] = None
            continue
        kind = spec["kind"]
        if kind in ("amount", "number"):
            value, status = parse_amount(printed)
            if status == "unreadable" and not (printed.endswith("%") and kind == "amount"):
                reasons.add("unreadable_amount", [key])
            row[key] = value if status == "ok" else printed
            parsed[key] = value
        elif kind == "date":
            value, status = parse_date(printed, date_order)
            if status == "ambiguous":
                reasons.add("ambiguous_date", [key])
            elif status == "unreadable":
                reasons.add("unreadable_date", [key])
            row[key] = value if status == "ok" else printed
            parsed[key] = value
        else:
            row[key] = printed
            parsed[key] = printed
    return row, parsed


def _check_keys(where, given, allowed, guide):
    unknown = sorted(set(given) - set(allowed))
    if unknown:
        raise ExtractionError(
            f"{where} has unknown field(s) {', '.join(unknown)}. Use only the field names in {guide}.")


class Processor:
    def __init__(self, profile, catalogue, columns, mapping):
        self.profile, self.catalogue, self.mapping = profile, catalogue, mapping
        self.date_order = profile["date_order"] if profile else None
        self.specs = {name: {c["key"]: c for c in cols if c["source"] == "extracted"}
                      for name, cols in columns.items()}
        self.labels = {name: {c["key"]: c["label"] for c in cols} for name, cols in columns.items()}
        self.rows = {bucket: [] for bucket in BUCKETS}
        self.line_items, self.statement_lines = [], []

    def run(self, extraction):
        if extraction.get("set_aside"):
            raise ExtractionError(
                "set_aside is no longer used: every document goes in documents, with its type.")
        for number, doc in enumerate(extraction.get("documents", []), start=1):
            where = f"Document {number} ({doc.get('file', 'no file name')})"
            bucket, shape = place(doc.get("document_type", ""), self.mapping)
            row = getattr(self, f"_{shape}")(doc, where, bucket)
            row.update(file=doc.get("file"), pages=doc.get("pages"),
                       document_type=doc.get("document_type"), type_evidence=doc.get("type_evidence"),
                       bucket=bucket)
            self.rows[bucket].append(row)
        return self

    def _common(self, doc, where, table, guide):
        specs = self.specs[table]
        fields = doc.get("fields", {})
        _check_keys(f"{where} fields", fields, specs, guide)
        unclear = set(doc.get("unclear", []))
        _check_keys(f"{where} unclear", unclear, specs, guide)
        reasons = Reasons(self.catalogue, self.labels[table])
        row, parsed = _parse_fields(fields, specs, self.date_order, reasons, unclear)
        if row.get("document_title") is None and "document_title" not in unclear:
            reasons.add("no_title")
        return row, parsed, reasons, unclear

    def _finish(self, doc, row, reasons, table):
        specs = self.specs[table]
        if doc.get("handwritten"):
            checked = [k for k, s in specs.items()
                       if s["kind"] in ("amount", "date") and row.get(k) is not None]
            reasons.add("handwritten", checked)
        for note in doc.get("notes", []):
            note_fields = [k for k in note.get("columns", []) if k in specs]
            reasons.add("agent_note", note_fields, text=note.get("text", "").strip())
        row.update(needs_review="Yes" if reasons.lines else "No", review_reasons=reasons.text())
        return row

    def _invoice(self, doc, where, bucket):
        guide = "references/field-rules.md"
        row, parsed, reasons, _ = self._common(doc, where, "documents", guide)

        line_totals, any_line_flagged = [], False
        for line_number, item in enumerate(doc.get("line_items", []), start=1):
            _check_keys(f"{where} line {line_number}", set(item) - _EXTRA_KEYS,
                        self.specs["line_items"], guide)
            line_reasons = Reasons(self.catalogue, self.labels["line_items"])
            line_row, line_parsed = _parse_fields(item, self.specs["line_items"], self.date_order,
                                                  line_reasons, set(item.get("unclear", [])))
            status = check_line(line_parsed["quantity"], line_parsed["unit_price"],
                                line_parsed["line_discount"], line_parsed["line_total"])
            if status == FAILED:
                line_reasons.add("line_mismatch")
            line_totals.append(line_parsed["line_total"])
            line_row.update(file=doc.get("file"), document_number=row.get("document_number"),
                            line=line_number, line_check=status, review_reasons=line_reasons.text())
            any_line_flagged = any_line_flagged or bool(line_reasons.lines)
            self.line_items.append(line_row)

        for line_number, item in enumerate(doc.get("statement_lines", []), start=1):
            _check_keys(f"{where} statement line {line_number}", set(item) - _EXTRA_KEYS,
                        self.specs["statement_lines"], guide)
            line_reasons = Reasons(self.catalogue, self.labels["statement_lines"])
            line_row, _ = _parse_fields(item, self.specs["statement_lines"], self.date_order,
                                        line_reasons, set(item.get("unclear", [])))
            line_row.update(file=doc.get("file"), document_number=row.get("document_number"),
                            line=line_number, review_reasons=line_reasons.text())
            any_line_flagged = any_line_flagged or bool(line_reasons.lines)
            self.statement_lines.append(line_row)

        amounts = {k: parsed.get(k) for k in
                   ("subtotal", "discount", "shipping", "tax_amount", "total", "balance_due")}
        overall, failures = check_document(amounts, line_totals)
        present = [k for k, v in amounts.items() if v is not None]
        for failure in failures:
            reasons.add(failure, present + ["total"])
        if row.get("total") is None and row.get("balance_due") is not None:
            # Project rule: with no printed total, the balance due (or amount due) stands
            # for the total. Done here by rule, never left to the reading step to guess.
            row["total"] = row["balance_due"]
        if any_line_flagged:
            reasons.add("line_items_flagged")
        if str(doc.get("document_type", "")).casefold() == "invoice" and row.get("invoice_number") is None:
            # Project rule: an invoice's own number is its Invoice No., so every sheet can be
            # matched on one column. Copied by rule from the printed document number.
            row["invoice_number"] = row.get("document_number")

        value, reason = direction(self.profile, row.get("seller_name"), row.get("buyer_name"))
        if reason:
            reasons.add(reason)
        if self.profile and bucket == "Billing documents":
            for key in sorted(self.profile["required"]):
                if key in self.specs["documents"] and row.get(key) is None:
                    reasons.add("required_missing", [key])
        row.update(direction=value, arithmetic_check=overall)
        return self._finish(doc, row, reasons, "documents")

    def _payment(self, doc, where, bucket):
        guide = "references/field-rules-other.md"
        row, _, reasons, _ = self._common(doc, where, "payments", guide)
        _check_keys(f"{where}", set(doc) & {"line_items", "statement_lines"}, set(), guide)
        value, reason = direction(self.profile, row.get("payee"), row.get("payer"))
        value = {SALES: MONEY_IN, PURCHASE: MONEY_OUT}.get(value, value)
        if reason:
            reasons.add({"direction_none": "payment_direction_none",
                         "direction_both": "payment_direction_both"}.get(reason, reason))
        row["direction"] = value
        return self._finish(doc, row, reasons, "payments")

    def _other(self, doc, where, bucket):
        guide = "references/field-rules-other.md"
        row, _, reasons, _ = self._common(doc, where, "other", guide)
        _check_keys(f"{where}", set(doc) & {"line_items", "statement_lines"}, set(), guide)
        reasons.add("other_document")
        row["description"] = doc.get("description")
        return self._finish(doc, row, reasons, "other")


def _read_extraction(path):
    """One JSON file, or a folder of them (one per document), merged in name order."""
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    if not files:
        raise ValueError(f"no .json files in {path}")
    merged = {"documents": [], "set_aside": []}
    for file in files:
        part = json.loads(file.read_text(encoding="utf-8"))
        merged["documents"] += part.get("documents", [])
        merged["set_aside"] += part.get("set_aside", [])
    return merged


def _free_path(path):
    if not path.exists():
        return path
    for n in range(2, 1000):
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise SystemExit("Too many output files with the same name. Choose another name.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--profile")
    parser.add_argument("--custom")
    parser.add_argument("--model-reported", default="")
    args = parser.parse_args(argv)

    try:
        extraction = _read_extraction(Path(args.extraction))
    except (OSError, ValueError) as error:
        print(f"Problem: the extraction file couldn't be read ({error}).")
        return 2
    try:
        profile = read_profile(args.profile) if args.profile else None
    except ProfileError as error:
        print(f"Problem with the company profile: {error}")
        return 2
    try:
        mapping, confirmed = read_custom(args.custom) if args.custom else (default_mapping(), False)
    except (OSError, CustomError) as error:
        print(f"Problem with custom.md: {error}")
        return 2

    columns = load_columns()
    catalogue = _load_toml("review-reasons.toml")
    skill_set = _load_toml("set.toml") if (DATA / "set.toml").exists() else {}
    try:
        result = Processor(profile, catalogue, columns, mapping).run(extraction)
    except ExtractionError as error:
        print(f"Problem in the extraction file: {error}")
        return 2

    def sheet_columns(table, keys=None):
        by_key = {c["key"]: c for c in columns[table]}
        return [(k, by_key[k]["label"], by_key[k]["kind"]) for k in (keys or by_key)]

    invoice_keys = profile["columns"] if profile else None
    sheets = [
        ("Billing documents", sheet_columns("documents", invoice_keys), result.rows["Billing documents"]),
        ("Reference documents", sheet_columns("documents", invoice_keys), result.rows["Reference documents"]),
        ("Payments", sheet_columns("payments"), result.rows["Payments"]),
        ("Other", sheet_columns("other"), result.rows["Other"]),
        ("Line items", sheet_columns("line_items"), result.line_items),
        ("Statement lines", sheet_columns("statement_lines"), result.statement_lines),
    ]
    all_rows = [row for rows in result.rows.values() for row in rows]
    flagged = sum(1 for row in all_rows if row["needs_review"] == "Yes")
    if not args.custom:
        buckets_used = "Defaults (no custom.md)"
    else:
        buckets_used = f"{Path(args.custom).name} ({'confirmed' if confirmed else 'not yet confirmed'})"
    run_info = [
        ("Skill set", skill_set.get("name", "")),
        ("Skill set version", skill_set.get("version", "")),
        ("Evaluated on model", skill_set.get("evaluated_model", "")),
        ("Model (as reported by the agent)", args.model_reported or "Not reported"),
        ("Run date", date.today().isoformat()),
        ("Company profile", profile["file"] if profile else "None used"),
        ("Document buckets", buckets_used),
        ("Documents read", str(len(all_rows))),
    ] + [(f"  {bucket}", str(len(rows))) for bucket, rows in result.rows.items()] + [
        ("Documents that need review", str(flagged)),
    ]

    out = _free_path(Path(args.out))
    try:
        workbook.write(out, sheets, run_info)
    except PermissionError:
        print(f"Problem: '{out}' couldn't be saved. If it is open in Excel, close it and try again.")
        return 2

    print(f"Saved {out}")
    print(f"Documents read: {len(all_rows)} ("
          + ", ".join(f"{bucket} {len(rows)}" for bucket, rows in result.rows.items())
          + f"). Need review: {flagged}.")
    invoice_rows = result.rows["Billing documents"] + result.rows["Reference documents"]
    checks = {s: sum(1 for d in invoice_rows if d["arithmetic_check"] == s)
              for s in (PASSED, FAILED, NOT_CHECKABLE)}
    print("Arithmetic check: " + ", ".join(f"{s} {n}" for s, n in checks.items()) + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
