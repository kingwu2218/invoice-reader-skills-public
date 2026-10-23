# Invoice reader settings

Tell the agent what you want to find and how you will use it. It maintains this file for you.
Requested fields can describe any printed information, including certificate measurements.
They cannot change the rules against guessing values or correcting the original.

Confirmed by user: yes

## Purpose

Extract the printed amounts for finance review.

## Requested fields

| Key | Column | Find | Values | Required |
|---|---|---|---|---|
| printed_amount | Printed amount | The labelled invoice total or cheque amount in figures, preserving its written notation and explicitly labelled currency separately | one | no |

An empty table uses the standard document columns. Values is one or many; Required is yes or no.
Keep printed units and evidence. Use semicolons instead of vertical bars inside table cells.

## Document buckets

| Document type | Bucket |
|---|---|
| Invoice | Billing documents |
| Credit note | Billing documents |
| Debit note | Billing documents |
| Receipt | Reference documents |
| Proforma invoice | Reference documents |
| Quotation | Reference documents |
| Purchase order | Reference documents |
| Delivery note | Reference documents |
| Statement of account | Reference documents |
| Cheque | Payments |
| Bank deposit slip | Payments |

Buckets: Billing documents, Reference documents, Payments, Other.
Any document type not listed here, and any document the reader is unsure about, goes on Other.
