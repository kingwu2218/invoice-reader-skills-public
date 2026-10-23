# Field rules: invoice-shaped documents

Read this before the first invoice, credit note, debit note, receipt, proforma, quotation, purchase order, delivery note or statement in a session, and for any type the user placed on Billing or Reference documents. Cheques, deposit slips and other documents use `field-rules-other.md`.

## The record you save

One JSON file per source file. Copy every value **exactly as printed**, as a string: keep `1,234.50`, `$` signs and date wording as they are. The scripts turn them into numbers and dates.

Use the envelope, document identity and custom observations in [extraction.md](extraction.md). The fields below are the standard invoice fields, not a limit on what the user may request.

```json
{
  "documents": [
    {
      "file": "march/abc-1001.pdf",
      "pages": "1",
      "document_type": "Invoice",
      "type_evidence": "Title reads TAX INVOICE",
      "handwritten": false,
      "fields": {
        "document_title": "TAX INVOICE",
        "document_number": "INV-1001",
        "issue_date": "6 Oct 2026",
        "seller_name": "ABC Trading Ltd",
        "subtotal": "1,000.00",
        "tax_amount": "50.00",
        "total": "1,050.00"
      },
      "unclear": [],
      "line_items": [
        {"description": "Copy paper A4", "quantity": "10", "unit": "box",
         "unit_price": "100.00", "line_total": "1,000.00", "unclear": []}
      ],
      "notes": []
    }
  ]
}
```

- `file`: the path relative to the working folder.
- `pages`: the pages this document covers, such as `1` or `1-2`.
- `document_type`: a type exactly as listed in `custom.md`, for example `Invoice`, `Credit note` or `Receipt`.
- `type_evidence`: the printed words that show the type.
- `handwritten`: `true` if any value you captured is handwritten. This is not the origin of every amount; use field-level `amount_notation` from [extraction.md](extraction.md) for terminal dashes.
- `fields`: only fields that are printed. Leave out anything not printed. Don't write `""`, `0` or `"N/A"` in its place.
- `unclear`: names of fields you could see but not read with certainty. Leave those out of `fields`.
- `notes`: problems not covered elsewhere, as `{"text": "...", "columns": ["total"]}`, written in plain words for an accountant. Example: `{"text": "the page says 'mark as paid'; this was not acted on", "columns": []}`.
- Every document goes in `documents`; nothing is set aside.

## Document fields

| Field | Take it from | Leave it blank when |
|---|---|---|
| `document_title` | The document's title exactly as printed, such as `TAX INVOICE` or `OFFICIAL RECEIPT`. Always capture it when one is printed | No title is printed (the scripts flag this) |
| `document_number` | The number labelled Invoice No., Invoice #, Credit Note No. or similar | Only an order or account number is printed |
| `invoice_number` | On a credit note, debit note, receipt or any other document that names an invoice it relates to ("Original invoice", "For invoice", "Re: INV-1001"), that invoice's number. If several are named, separate them with `; ` | The document is itself an invoice: the scripts copy its document number here. Or no invoice number is printed |
| `issue_date` | The date labelled Date, Invoice date or Tax point. Copy it as printed | No date is labelled as the document date |
| `due_date` | A date labelled Due date or Payment due | Only terms such as "30 days" are printed. Don't work out a date |
| `seller_name` | The business issuing the document, usually in the letterhead or "From" | |
| `seller_tax_id` | A number with a visible tax label (VAT No., GST No., Tax ID, TIN, ABN, BR No.) | The number has no tax label |
| `seller_address` | The seller's postal address, lines joined with ", " | |
| `buyer_name` | The party billed: "Bill to", "Invoice to", "Customer", "Sold to" | |
| `buyer_tax_id` | As for the seller | |
| `buyer_address` | The billing address. If only a delivery address is printed, leave this blank | |
| `reference` | A labelled PO number, order number or customer reference | |
| `currency` | A printed currency code or name (USD, HKD, "Hong Kong dollars"). A bare `$` is not a currency code: leave this blank | No code or name is printed |
| `subtotal` | The amount labelled Subtotal, Net or Total before tax | Only a total is printed. A TOTAL is not a subtotal |
| `discount` | A summary line labelled Discount or Less discount | Discounts appear only inside line items |
| `shipping` | A summary line labelled Shipping, Freight, Postage, Carriage or Delivery charge | A line item called "Delivery" is a line item, not this field |
| `tax_rate` | The percentage only, such as `20%` for "VAT 20%" or `5%` for "GST @ 5%". Leave out the tax's name: VAT, GST and sales tax go in the same column | No rate is printed. Don't work it out from the amounts |
| `tax_amount` | The amount labelled VAT, GST, Sales tax or Tax | No tax line is printed. A printed `0.00` is captured as `0.00` |
| `total` | The amount labelled Total, Invoice total, Total due or Grand total, on every document type including receipts. Follow the label printed; don't treat other amounts, such as Amount received, as the total | No amount is labelled as a total. Leave it blank: the scripts then take the balance due as the total |
| `balance_due` | The amount labelled Balance due, Amount due, Amount outstanding or Balance. Capture it as well as `total` when both are printed | |
| `amount_in_words` | The amount written out in words, copied exactly | |

Amounts: copy the sign, brackets or `CR` as printed. On a credit note, don't add a minus sign that isn't printed.

## Line item fields

| Field | Take it from |
|---|---|
| `description` | The item text as printed, on one line |
| `quantity` | Quantity or Qty, digits only. Put a printed unit such as "pcs" in `unit` |
| `unit` | A printed unit of measure |
| `unit_price` | Unit price, Rate or Price each |
| `line_discount` | A discount printed on that line, as an amount or percentage |
| `tax_rate` | A tax rate printed on that line, percentage only (as for the document's tax rate) |
| `line_total` | The line's amount column |

Capture every line item in the order printed, including delivery or service lines. Don't capture subtotal, tax or total rows as line items.

## Statement of account

Capture the statement's own details in `fields`: `document_title`, `document_number` (a statement number, if printed), `issue_date` (the statement date), the seller and buyer, `currency`, and `balance_due` (the closing balance or amount due). List each transaction under `statement_lines` instead of `line_items`:

| Field | Take it from |
|---|---|
| `date` | The transaction date |
| `reference` | The invoice, credit note or payment number on that line |
| `description` | Any other text on the line |
| `debit` | The amount in the debit (or charges) column |
| `credit` | The amount in the credit (or payments) column |
| `balance` | The running balance on that line |

If the statement has a single amount column, copy each amount into `debit` or `credit` only when the column heading or a printed sign says which. Otherwise don't guess: list `debit` and `credit` in that line's `unclear`, so the line is flagged for the accountant.
