# Field rules: payments and other documents

Read this before the first cheque, bank deposit slip, other document or `Unsure` document in a session. The record format, and the rules on blanks, `unclear`, `handwritten` and `notes`, are the same as in `field-rules.md`. These documents have no `line_items`.

## Cheques and bank deposit slips (Payments)

```json
{"file": "chq-0042.jpg", "pages": "1", "document_type": "Cheque",
 "type_evidence": "Pay ... or order; cheque number line; bank name",
 "handwritten": true,
 "fields": {"payment_date": "3 Oct 2026", "bank_name": "Example Bank",
            "cheque_number": "000123", "payee": "ABC Trading Ltd",
            "amount": "250.00", "amount_in_words": "Two hundred and fifty pounds only"},
 "unclear": [], "notes": []}
```

| Field | Take it from | Leave it blank when |
|---|---|---|
| `document_title` | A printed title, such as `DEPOSIT SLIP` | Most cheques have none; the scripts flag that, which is expected |
| `payment_date` | The date on the cheque or slip | |
| `bank_name` | The bank printed on the document | |
| `cheque_number` | The cheque's serial number | It is a deposit slip with no cheque number |
| `account_number` | The account number printed or written | |
| `payee` | On a cheque, the name after "Pay"; on a deposit slip, the account holder being paid in to | |
| `payer` | On a cheque, the account holder or signatory's printed company name; on a deposit slip, the depositor | Only a signature is shown: don't read a name from a signature |
| `currency` | A printed currency code or name | Only a symbol is printed |
| `amount` | The amount in figures | |
| `amount_in_words` | The amount written in words, copied exactly | |

If the amount in words and in figures disagree, copy both as written and add a note naming `amount` and `amount_in_words`.

## Other documents and Unsure

Use for any type the user placed on Other, and for documents you can't classify (`document_type`: a short plain name such as `Tenancy agreement`, or `Unsure`).

```json
{"file": "misc/lease.pdf", "pages": "1-3", "document_type": "Tenancy agreement",
 "type_evidence": "Title reads TENANCY AGREEMENT",
 "description": "Lease of an office unit for 12 months",
 "fields": {"document_title": "TENANCY AGREEMENT", "document_date": "1 Sep 2026",
            "parties": "ABC Trading Ltd; Exampleton Properties Ltd"},
 "unclear": [], "notes": []}
```

| Field | Take it from |
|---|---|
| `document_title` | The title as printed |
| `document_date` | The document's own date, if one is labelled |
| `parties` | The organisations or people named as parties, separated by `; ` |
| `total` | Only an amount labelled as a total |
| `description` (outside `fields`) | One plain sentence saying what the document is. This is your summary, not printed text |

Every document on Other is flagged for the accountant to check by hand.
