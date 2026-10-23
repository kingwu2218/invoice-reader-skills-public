"""Generate the printed test documents and add their rows to the answer key.

Every name, address and number here is invented. Addresses use the made-up town
"Exampleton" and e-mail addresses use the reserved .example domain.

The answer key is the source of truth once a case is in it: this script only adds
cases that are missing and never overwrites a row. A case's `fields` are its expected
values; `printed` controls what appears on the page.

Usage: python eval/tools/make_cases.py      (needs reportlab and openpyxl)
"""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL.parent / "core" / "scripts"))
from company_profile import load_columns  # noqa: E402

D = Decimal
rl_config.invariant = 1  # same input, same PDF bytes

KESTREL = {
    "seller_name": "Kestrel Lane Stationers Ltd",
    "seller_tax_id": "XX 123 4567 89",
    "seller_address": "Unit 4, 18 Fennick Road, Exampleton, EX1 2AB",
}
TALLOWMERE = {
    "buyer_name": "Tallowmere Consulting Ltd",
    "buyer_address": "22 Quarry Mews, Exampleton, EX4 9QT",
}

CASES = [
    {
        "id": "printed-001",
        "axes": {"type": "invoice", "medium": "printed-pdf", "direction": "AP", "hard": []},
        "expected_type": "Invoice",
        "expected_direction": "Purchase (AP)",
        "expected_bucket": "Billing documents",
        "flag_expected": "No",
        "email": "accounts@kestrel-lane.example",
        "fields": {
            "document_title": "INVOICE", "document_number": "KLS-2026-0417",
            "invoice_number": "KLS-2026-0417",
            "issue_date": date(2026, 9, 14), "due_date": date(2026, 10, 14),
            **KESTREL, **TALLOWMERE, "reference": "TC-PO-3381", "currency": "GBP",
            "subtotal": D("245.00"), "tax_rate": "20%", "tax_amount": D("49.00"),
            "total": D("294.00"),
        },
        "meta": [("Invoice No.:", "document_number"), ("Invoice date:", "issue_date"),
                 ("Due date:", "due_date"), ("Your PO No.:", "reference")],
        "summary": [("Subtotal", "subtotal"), ("VAT 20%", "tax_amount"), ("Total GBP", "total")],
        "footer": ["All amounts in GBP. Payment terms: 30 days.", "Thank you for your business."],
        "lines": [
            {"description": "A4 copy paper, 80gsm (box of 5 reams)", "quantity": D("6"),
             "unit": "box", "unit_price": D("24.50"), "line_total": D("147.00")},
            {"description": "Black ballpoint pens (pack of 50)", "quantity": D("4"),
             "unit": "pack", "unit_price": D("12.75"), "line_total": D("51.00")},
            {"description": "Lever arch files, assorted colours", "quantity": D("20"),
             "unit": "each", "unit_price": D("2.35"), "line_total": D("47.00")},
        ],
    },
    {
        "id": "printed-002",
        "axes": {"type": "invoice", "medium": "printed-pdf", "direction": "AP", "hard": ["no-subtotal"]},
        "expected_type": "Invoice",
        "expected_direction": "Purchase (AP)",
        "expected_bucket": "Billing documents",
        "flag_expected": "No",
        "email": "orders@brackenfold.example",
        "fields": {
            "document_title": "TAX INVOICE", "document_number": "BCS/7781",
            "invoice_number": "BCS/7781",
            "issue_date": date(2026, 9, 30), "due_date": date(2026, 10, 30),
            "seller_name": "Brackenfold Catering Supplies Ltd",
            "seller_tax_id": "XX 987 6543 21",
            "seller_address": "3 Mill Yard, Exampleton, EX2 7LP",
            **TALLOWMERE, "currency": "GBP",
            "tax_rate": "20%", "tax_amount": D("18.50"), "total": D("111.00"),
        },
        "meta": [("Invoice number:", "document_number"), ("Date:", "issue_date"),
                 ("Payment due:", "due_date")],
        "summary": [("VAT 20%", "tax_amount"), ("Total due GBP", "total")],
        "footer": ["Prices in GBP."],
        "lines": [
            {"description": "Coffee beans, house blend (1 kg)", "quantity": D("5"),
             "unit": "bag", "unit_price": D("14.20"), "line_total": D("71.00")},
            {"description": "Paper cups, 8 oz (sleeve of 50)", "quantity": D("10"),
             "unit": "sleeve", "unit_price": D("2.15"), "line_total": D("21.50")},
        ],
    },
    {
        "id": "printed-003",
        "axes": {"type": "invoice", "medium": "printed-pdf", "direction": "AP", "hard": ["no-total"]},
        "expected_type": "Invoice",
        "expected_direction": "Purchase (AP)",
        "expected_bucket": "Billing documents",
        "flag_expected": "No",
        "email": "hello@ostrowe-windows.example",
        "fields": {
            # No total is printed: by the project rule the amount due stands for the total.
            "document_title": "INVOICE", "document_number": "0193",
            "invoice_number": "0193",
            "issue_date": date(2026, 10, 1),
            "seller_name": "Ostrowe Window Cleaning",
            "seller_tax_id": "XX 555 0102 33",
            "seller_address": "41 Larch Close, Exampleton, EX3 1QD",
            **TALLOWMERE, "currency": "GBP",
            "subtotal": D("180.00"), "tax_rate": "20%", "tax_amount": D("36.00"),
            "total": D("216.00"), "balance_due": D("216.00"),
        },
        "meta": [("Invoice:", "document_number"), ("Date:", "issue_date")],
        "summary": [("Subtotal", "subtotal"), ("VAT 20%", "tax_amount"),
                    ("Amount due GBP", "balance_due")],
        "footer": ["Window cleaning, September 2026. Please pay within 14 days."],
        "lines": [
            {"description": "External window cleaning, office (monthly)", "quantity": D("1"),
             "unit": "", "unit_price": D("120.00"), "line_total": D("120.00")},
            {"description": "Skylight cleaning", "quantity": D("2"),
             "unit": "", "unit_price": D("30.00"), "line_total": D("60.00")},
        ],
    },
    {
        "id": "printed-004",
        "axes": {"type": "credit-note", "medium": "printed-pdf", "direction": "AP", "hard": []},
        "expected_type": "Credit note",
        "expected_direction": "Purchase (AP)",
        "expected_bucket": "Billing documents",
        "flag_expected": "No",
        "email": "accounts@kestrel-lane.example",
        "fields": {
            # Amounts are printed without a minus sign, so the key has none either.
            "document_title": "CREDIT NOTE", "document_number": "KLS-CN-0052",
            "invoice_number": "KLS-2026-0417",
            "issue_date": date(2026, 10, 2),
            **KESTREL, **TALLOWMERE, "currency": "GBP",
            "subtotal": D("11.75"), "tax_rate": "20%", "tax_amount": D("2.35"),
            "total": D("14.10"),
        },
        "meta": [("Credit note No.:", "document_number"), ("Date:", "issue_date"),
                 ("Original invoice:", "invoice_number")],
        "summary": [("Subtotal", "subtotal"), ("VAT 20%", "tax_amount"),
                    ("Total credit GBP", "total")],
        "footer": ["Credit for goods returned damaged."],
        "lines": [
            {"description": "Lever arch files, assorted colours (returned, damaged)",
             "quantity": D("5"), "unit": "each", "unit_price": D("2.35"), "line_total": D("11.75")},
        ],
    },
    {
        "id": "printed-005",
        "axes": {"type": "receipt", "medium": "printed-pdf", "direction": "AP", "hard": []},
        "expected_type": "Receipt",
        "expected_direction": "Purchase (AP)",
        "expected_bucket": "Reference documents",
        "flag_expected": "No",
        "email": "orders@brackenfold.example",
        "party_label": "Received from:",
        "fields": {
            "document_title": "OFFICIAL RECEIPT", "document_number": "R-20461",
            "invoice_number": "BCS/7781",
            "issue_date": date(2026, 10, 9),
            "seller_name": "Brackenfold Catering Supplies Ltd",
            "seller_tax_id": "XX 987 6543 21",
            "seller_address": "3 Mill Yard, Exampleton, EX2 7LP",
            **TALLOWMERE, "currency": "GBP",
            "subtotal": D("30.00"), "tax_rate": "20%", "tax_amount": D("6.00"),
            "total": D("36.00"),
        },
        "meta": [("Receipt No.:", "document_number"), ("Date:", "issue_date"),
                 ("For invoice:", "invoice_number")],
        "summary": [("Subtotal", "subtotal"), ("VAT 20%", "tax_amount"), ("Total GBP", "total")],
        "footer": ["Paid by card. Thank you."],
        "lines": [
            {"description": "Milk, semi-skimmed (2 litre)", "quantity": D("4"),
             "unit": "bottle", "unit_price": D("1.75"), "line_total": D("7.00")},
            {"description": "Biscuits, assorted (tin)", "quantity": D("2"),
             "unit": "tin", "unit_price": D("11.50"), "line_total": D("23.00")},
        ],
    },
]


def long_date(value):
    return f"{value.day} {value:%B %Y}"


def money(value):
    return f"{value:,.2f}"


def shown(value):
    return long_date(value) if isinstance(value, date) else str(value)


def draw_invoice(case, path):
    f = case["fields"]
    styles = getSampleStyleSheet()
    small = styles["Normal"]
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"{f['document_title'].title()} {f['document_number']}", author="")
    story = [
        Paragraph(f"<b>{f['seller_name']}</b>", styles["Title"]),
        Paragraph(f"{f['seller_address']}<br/>{case['email']}", small),
        Paragraph(f"VAT No.: {f['seller_tax_id']}", small),
        Spacer(1, 8 * mm),
        Paragraph(f"<b>{f['document_title']}</b>", styles["Heading1"]),
    ]
    left = [case.get("party_label", "Bill to:"), f["buyer_name"], f["buyer_address"].replace(", ", "\n", 1)]
    right = [(label, shown(f[key])) for label, key in case["meta"]]
    rows = []
    for index in range(max(len(left), len(right))):
        label, value = right[index] if index < len(right) else ("", "")
        rows.append([left[index] if index < len(left) else "", "", label, value])
    meta = Table(rows, colWidths=[70 * mm, 20 * mm, 35 * mm, 45 * mm])
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                              ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold")]))
    story += [meta, Spacer(1, 8 * mm)]

    rows = [["Description", "Qty", "Unit", "Unit price", "Amount"]]
    for line in case["lines"]:
        rows.append([line["description"], str(line["quantity"]), line["unit"],
                     money(line["unit_price"]), money(line["line_total"])])
    rows += [["", "", "", label, money(f[key])] for label, key in case["summary"]]
    lines = Table(rows, colWidths=[78 * mm, 14 * mm, 16 * mm, 32 * mm, 30 * mm])
    last, first_summary = len(rows) - 1, len(rows) - len(case["summary"])
    lines.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
        ("LINEABOVE", (3, first_summary), (-1, first_summary), 0.5, colors.grey),
        ("FONTNAME", (3, last), (-1, last), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "LEFT"),
    ]))
    story += [lines, Spacer(1, 10 * mm)] + [Paragraph(text, small) for text in case["footer"]]
    doc.build(story)


def _add_missing_columns(sheet, columns):
    """When the core gains a field, add its column to the key in the core's order. Existing
    cases get the value from CASES where the case defines it; nothing already in the key changes."""
    by_id = {case["id"]: case for case in CASES}
    specs = [c for c in columns["documents"] if c["source"] == "extracted"]
    for index, spec in enumerate(specs):
        header = [c.value for c in sheet[1]]
        if spec["label"] in header:
            continue
        position = header.index(specs[index - 1]["label"]) + 2 if index else 7
        sheet.insert_cols(position)
        sheet.cell(row=1, column=position).value = spec["label"]
        for row in range(2, sheet.max_row + 1):
            case = by_id.get(sheet.cell(row=row, column=1).value)
            if case:
                sheet.cell(row=row, column=position).value = case["fields"].get(spec["key"])
        print(f"added column '{spec['label']}' to the answer key")


def _key_book(path, columns):
    if path.exists():
        book = load_workbook(path)
        documents = book["Documents"]
        if documents.cell(row=1, column=5).value != "Expected bucket":
            # One-off upgrade: every case before buckets existed was a billing document.
            documents.insert_cols(5)
            documents.cell(row=1, column=5).value = "Expected bucket"
            for row in range(2, documents.max_row + 1):
                documents.cell(row=row, column=5).value = "Billing documents"
        _add_missing_columns(documents, columns)
        return book
    book = Workbook()
    documents = book.active
    documents.title = "Documents"
    documents.append(["Case", "File", "Expected type", "Expected direction", "Expected bucket",
                      "Flag expected"]
                     + [c["label"] for c in columns["documents"] if c["source"] == "extracted"])
    lines = book.create_sheet("Line items")
    lines.append(["Case", "Line"] + [c["label"] for c in columns["line_items"] if c["source"] == "extracted"])
    notes = book.create_sheet("Notes")
    notes.append(["A blank cell means the field is not printed on the document."])
    notes.append(["Amounts are numbers; dates are dates; text is copied as printed."])
    return book


def main():
    columns = load_columns()
    key_path = EVAL / "answer-key.xlsx"
    book = _key_book(key_path, columns)
    known = {row[0] for row in book["Documents"].iter_rows(min_row=2, values_only=True)}
    doc_keys = [c["key"] for c in columns["documents"] if c["source"] == "extracted"]
    labels = {c["key"]: c["label"] for c in columns["documents"]}
    line_keys = [c["key"] for c in columns["line_items"] if c["source"] == "extracted"]

    for case in CASES:
        folder = EVAL / "cases" / case["id"]
        folder.mkdir(parents=True, exist_ok=True)
        file_name = f"{case['id']}.pdf"
        draw_invoice(case, folder / file_name)
        axes = case["axes"]
        hard = "[" + ", ".join(f'"{h}"' for h in axes["hard"]) + "]"
        (folder / "case.toml").write_bytes((
            f'file = "{file_name}"\n'
            f'type = "{axes["type"]}"\nmedium = "{axes["medium"]}"\n'
            f'direction = "{axes["direction"]}"\nhard = {hard}\n').encode())
        print(f"wrote eval/cases/{case['id']}/{file_name}")
        if case["id"] in known:
            continue
        values = {"Case": case["id"], "File": file_name, "Expected type": case["expected_type"],
                  "Expected direction": case["expected_direction"],
                  "Expected bucket": case["expected_bucket"], "Flag expected": case["flag_expected"]}
        values.update({labels[k]: case["fields"].get(k) for k in doc_keys})
        header = [c.value for c in book["Documents"][1]]
        book["Documents"].append([values.get(label) for label in header])
        for number, line in enumerate(case["lines"], start=1):
            book["Line items"].append([case["id"], number] + [line.get(k) or None for k in line_keys])
        print(f"added {case['id']} to the answer key")
    book.save(key_path)


if __name__ == "__main__":
    main()
