# Field rules: payments and other documents

Read this before the first cheque, bank deposit slip, other document or `Unsure` document in a session. The examples below are document records: always wrap them in the `documents` array described in [extraction.md](extraction.md). These documents have no `line_items`. Requested fields from custom.md can be extracted on every shape, including certificates.

## Cheques and bank deposit slips (Payments)

```json
{"file": "chq-0042.jpg", "pages": "1", "document_type": "Cheque",
 "type_evidence": "Pay ... or order; cheque number line; bank name",
 "handwritten": true,
 "fields": {"payment_date": "3 Oct 2026", "bank_name": "Example Bank",
            "cheque_number": "000123", "payee": "ABC Trading Ltd", "payer": "Example Buyer Ltd",
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

For every cheque, read both `payee` (who receives the money) and `payer` (the drawer/account holder who pays), even when custom.md only requests amounts or references. Look at the Pay line and the printed account-holder name or company stamp near the signature. Keep the names as printed; the bank's name belongs in `bank_name`, not `payer`. If the drawer's name is printed more than once in different forms, such as an uppercase account-holder line and a title-case name under "For and on behalf of", use the account-holder line exactly as printed, without changing its case, and quote the other form in a `payer` note. Do not fill either party from the company profile, an adjacent invoice, the filename or an undeciphered signature. If absent, leave it blank and explain which party is not shown in a field-specific note; if unreadable, also put that field in `unclear`. A visible bank name or a readable amount does not make both parties complete.

If the amount in words and in figures disagree, copy both as written and add a note naming `amount` and `amount_in_words`.

Keep identifiers as text, including every leading zero; distinguish the serial number from adjacent bank/account groups. If a group is hard to read, use the bounded visual recovery in [pdf-reading.md](pdf-reading.md) before marking it unclear. Do not borrow a number from a different document.

Copy the visible amount and date notation into the extraction, including an amount's terminal stroke or spaces between date boxes. Do not rewrite these strings merely to satisfy the processor. The processor may normalise an unambiguous spaced date and a terminal `/` in a cheque's amount field; it keeps the extraction unchanged. Ambiguous dates and unrecognised notation remain flagged rather than guessed.

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
