# Document types

Decide from what is printed. Record the evidence in the words on the page. Every type is extracted; the type decides which fields are read, and `custom.md` decides which sheet it goes on. The sheet shown here is the default.

| Type | Default sheet | Usual evidence |
|---|---|---|
| Invoice | Billing documents | Title Invoice or Tax invoice; an amount due; seller and buyer |
| Credit note | Billing documents | Title Credit note or Credit memo; often refers to an earlier invoice |
| Debit note | Billing documents | Title Debit note or Debit memo |
| Receipt | Reference documents | Title Receipt or Official receipt; "Received with thanks"; shows a payment made |
| Proforma invoice | Reference documents | Title Proforma or Pro forma: a request before supply, not a tax invoice |
| Quotation | Reference documents | Title Quotation, Quote or Estimate; a validity period |
| Purchase order | Reference documents | Title Purchase order or PO, issued by the buyer |
| Delivery note | Reference documents | Title Delivery note, Delivery order or Packing list; quantities, usually without prices |
| Statement of account | Reference documents | Title Statement; a list of invoices and payments with a running balance |
| Cheque | Payments | "Pay ... or order"; bank name; cheque number line |
| Bank deposit slip | Payments | Bank name; "Deposit" or "Paying-in"; account number; cash or cheque totals |
| Anything else | Other | Use a short plain name, such as Tenancy agreement |
| Unsure | Other | The evidence conflicts or is missing |

- The title decides when it is clear. "Invoice" in small print on a receipt does not make it an invoice.
- A title containing "Tax invoice", including "Tax invoice / Receipt", makes the document an **Invoice**. The full title is still captured in `document_title`.
- When in doubt, choose **Unsure** and say why. A document on the Other sheet is easy for the accountant to spot and re-file; a document on the wrong sheet with confident-looking figures is not.
