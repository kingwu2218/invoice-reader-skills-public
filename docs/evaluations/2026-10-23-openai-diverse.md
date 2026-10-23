# OpenAI 0.3.17: diverse synthetic documents

Three fresh Codex chats completed all configured fields correctly: **31 / 31 raw**
and **36 / 36 workbook**. One correct blank in each layer is excluded. There were
no missing or extra scored rows or unprocessed inputs. This is one execution per
synthetic case, not an accuracy estimate for customer invoices.

| Case | Purpose | Raw fields | Workbook fields |
|---|---|---:|---:|
| harbour-meter-v1 | Utility invoice, units and required meter reading | 11 / 11 | 12 / 12 |
| northwharf-receipt-v1 | Raster receipt, readable custom fields and partly hidden total | 8 / 8 | 10 / 10 |
| diverse-terms-v1 | Same-page credit note and proforma, separate amounts and printed zero | 12 / 12 | 14 / 14 |

The first two sources were already known synthetic regressions. The third is a
new maintainer-authored diagnostic: its PDF, settings and answers were frozen
before calls. It includes a positive printed credit amount, a different original
invoice reference, a printed zero balance, and separate proforma total, deposit
and payable balance. No private Fox document was uploaded or added to this snapshot.
The new diagnostic is straightforward printed text and is not independent gold
data or a handwriting holdout.

## Execution and controls

- Package: `invoice-reader-openai` 0.3.17, tree hash
  `e355b2548d97021fd1727b515e7d948d2c7c090f741f87176b6cc08f6bfaa07c`.
- Requested model: `gpt-6-luna`, effort `high`, preserving the current selected
  configuration. Model identity reported by the CLI: `Unknown` in all three cases.
- Provider: OpenAI through existing ChatGPT sign-in; Codex CLI
  `0.163.0-alpha.11.2`, explicit HTTPS transport, Python 3.14.5 on Windows.
- Three fresh workspaces and exact-session continuations, one attempt each.
  Expectations were kept outside model workspaces. No retries or grader changes.
- Each opening asked the exact policy question and both choices and visibly
  paused before document work. All **3 / 3** pass unchanged `codex-opening-v9`.
  The reply was the labelled scripted public-fixture read-later response;
  it does not represent human policy reading or consent.
- Exact-session traces show at least one image-tool response containing pixels
  in every trial. This is separate from the generic scorer's `not_captured`
  CLI-attachment audit; no page was attached by the harness. Returned pixels do
  not prove attention, page coverage or recognition quality.
- Package and datasets remained unchanged. Original local traces, raw extraction
  and workbooks stay outside the publication set. Public
  [JSON](2026-10-23-openai-diverse.json) and [CSV](2026-10-23-openai-diverse.csv)
  retain scores, artifact hashes and source/grader fingerprints.

## Prompt decision and next data

Keep 0.3.17 unchanged. Its existing rules already distinguish absent, unreadable
and printed zero, preserve printed signs, and require a summary field's own label.
These trials provide no new scored failure that warrants another instruction.
The receipt retained its unreadable total as blank; the credit and proforma
retained their own numbers, totals and requested balances without invented items.

Next, extend the private Fox dataset by source/template group rather than random
pages. Keep near-duplicates and pages from one transaction in the same split.
Use a development set to diagnose failures and a separate untouched confirmation
set for candidate prompts. Independently review ambiguous handwritten values;
unresolved values need an explicit unclear reference, not an assumed answer.

Prioritize crowded handwriting, adjacent subtotal/total figures, similar digits,
poor scans, repeated document numbers, continuation pages and instructions printed
inside documents. Track field mistakes, unjustified corrections, omitted records,
false review flags, elapsed time and token use separately. The current field
references do not fully score review-flag precision, party extraction or every
standard column.

For each reproducible failure, propose one bounded family-prompt change, rerun
existing regressions, then confirm against fresh reserved sources with the same
model and effort. Preserve the original failure and frozen answer versions.
Publish synthetic or carefully reviewed redacted equivalents; keep original
customer documents, full gold answers and raw runs in the private dataset.
