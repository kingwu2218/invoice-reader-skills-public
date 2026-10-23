# Varied first-use protocol v1

Two public synthetic PDFs, three physical pages and four documents. These layouts
and values were authored after the OpenAI 0.3.16 package freeze. They were not used
in this repository's earlier prompt development. This does not assert that the
model has never seen similar content. No real company data is included.

The author reviewed all three rendered pages before model execution. The source
generator is `eval/tools/build_varied_use.py`; regeneration refuses existing files.
References are authored from the printed facts, never from model responses.

| Source / location | Document | Printed values |
|---|---|---|
| batch-invoices.pdf / page 1 top | INVOICE RT-2048 | Subtotal 230.00; tax 18.40; total 248.40; due 12 Nov 2026; Filter cartridges, quantity 2, unit price 115.00, line total 230.00 |
| batch-invoices.pdf / page 1 bottom | CASH MEMO CM-083 | Subtotal 70.00; tax 0.00; total 70.00; due date absent; Packing sleeves, quantity 2, unit price 35.00, line total 70.00 |
| batch-support.pdf / page 1 (raster only) | INVOICE SR-0912 | Subtotal 120.00; tax 5.00; printed total 125.75; due date absent; Sample analysis, quantity 3, unit price 40.00, line total 120.00 |
| batch-support.pdf / page 2 (native text) | LAB CERTIFICATE | Sample Q-17: Energy Level of Coal 5,870 kcal/kg, Sulphur 0.42 %; Sample Q-18: Energy Level of Coal 24.8 MJ/kg, Sulphur 0.35 %; Ash content absent |

Cash Memo is Invoice, retaining its printed title. Same-page document occurrences
follow source order top to bottom. The source identity contains file, page, type
and occurrence, not an expected invoice number or amount. The certificate's
invoice reference SR-0912 is not its own invoice number.

The payment chat requests optional Invoice number and Payment due date columns.
The quality chat requests optional Energy Level of Coal, Sulphur and Ash content,
including all samples and printed units. Both retain standard document sheets.
Only PDFs and the installed skill enter the fresh workspaces; the model creates
custom.md and extraction. No pre-run public example is supplied. Each gets one
start and one reply attempt. The negative policy reply is explicitly scripted
public test input, not a human acknowledgement or consent.

Both raw transcription and workbook output are scored. Correct blanks are
excluded from accuracy; absent/printed status and expected review fields are
nonblank scored cells. Document, observation and line coverage are reported
separately. Printed total 125.75 must survive, with arithmetic Failed. Units must
not be converted. Expected missing values must remain blank. Tests deliberately
remove documents, swap same-page order, change totals, invent dates, convert units
and substitute the wrong purpose to check that these failures are detected.

The runner freezes fixture/reference, evaluator, transitive harness and package
hashes before execution, and rejects drift. v9 opening and existing extraction
graders are unchanged. One run per purpose broadens coverage; it is not a
stability claim, real-document holdout or production accuracy estimate.
