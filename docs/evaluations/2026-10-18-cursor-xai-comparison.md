# Cursor xAI comparison, 2026-10-17 and 2026-10-18

Scoped comparison of three ways of reading the same public synthetic documents with the same reported model. This is not a general accuracy claim, and it does not replace the earlier Cursor records.

- [2026-10-11 preparation](2026-10-11-cursor-xai-baseline.md) stays prepared only.
- [2026-10-12 execution scores](2026-10-12-cursor-xai-execution.md) stay as artifact scores from those IDE chats.
- The 2026-10-15 handoff is a different batch. Its covered-digit and Cash Memo misses are not added into the counts below.

Row-level results, token counts and timings are in [the CSV](2026-10-18-cursor-xai-comparison.csv) and [the JSON](2026-10-18-cursor-xai-comparison.json). Correct blanks stay out of the accuracy denominator. No price was returned by the CLI, so none is estimated. Workbook review time by an accountant was not measured.

## What changed

xAI family `0.1.2` keeps one prompt for both generated packages. There is no model-version fork and no model or effort pin.

The family prompt now asks the data-policy question once, only in the assistant message, then ends that turn. No, uncertainty, or any other reply continues. A stop request stops the task. The same chat does not ask again. For a number, a nearby mark that does not touch the glyphs is not uncertainty, and a real leading digit stays. If any glyph is covered, overwritten, cropped, or merged with a mark, the field stays blank and unclear. A visible fragment may be quoted as evidence only. It is not stored as the amount, not marked printed, and not replaced by another amount or a calculation.

The Cursor adapter says `AskQuestion` does not wait and is not a reply. The Grok Build adapter does not mention that Cursor tool. Shared `core/` was not edited. The Grok Build package was rebuilt from the shared prompt and was not run.

| Package | Version | Tree hash | This comparison |
|---|---|---|---|
| Cursor, frozen copy | 0.1.1 | `ba89c43560d1cfc8362135ea9465be5f44f4769f338ca6522501df1fa4527657` | Arm B |
| Cursor, current tree | 0.1.2 | `71d0552230f86c0e5c25d3af707d86ed091198bd537ef9a0d559b51db68b04e5` | Arm C |
| Grok Build, rebuilt only | 0.1.2 | `b1e72ffff1740e8093486eb7c4c914592b7dc10a015a5a71beccd58213a6a96b` | Not run |
| OpenAI Codex | 0.3.17 | `e355b2548d97021fd1727b515e7d948d2c7c090f741f87176b6cc08f6bfaa07c` | Unchanged |

`last_eval` stays empty. The sets table still says Not evaluated.

## How the chats were run

Three arms used the same four public files, the same company profile, the same `custom.md`, and the same user wording, including this sentence on every arm: if any digit of an amount is covered or not fully readable, leave that amount blank and mark it unclear, and do not complete it from the visible digits, another amount, or arithmetic. Arm A was also told which workbook columns an accountant needed, and was told not to use an invoice-reader skill. Arms B and C were pointed at the skill copy inside that chat's own document folder.

Each chat had a new document folder outside this repository, so this repository's agent instructions, answer files and old workbooks were not the workspace. Answer files were not copied into those folders. The runner checked that none were present. One scripted reply was sent only after a B or C question turn that had not already read the document or written the workbook. The reply was the public "No, but I will read it…" choice, unless the chat was testing "No", "I'm not sure", silence, or stop. Arm A had no policy question and no second turn. No person typed during the runs. Human workbook-review time is unmeasured.

The reported model string on every recorded turn was `Grok 4.7 256K High Fast`. The selected model was not switched. This string is not the earlier label "Grok 4.7 High", and these counts are not that batch.

The 17 October chats were launched while the installed Cursor CLI reported `2026.10.14-941492e`. The saved transcripts do not repeat the CLI version. On 18 October the same version command reported `2026.10.16-e3cb207`. Continuation, the two extra receipt runs, and frozen digit-boundary trials 4 and 5 are the 18 October rows. They stay in the table and are not pooled with the 17 October timings.

The interpreter was Python 3.14.5 with pypdfium2 5.14.0, Pillow 13.0.0 and openpyxl 3.1.5. All 22 saved route reports recorded pypdfium2 5.14.0, inside the package range `>=5.13,<6`. Pillow 13.0.0 is inside `Pillow>=10.1` and is newer than the 12.3.0 smoke recorded for an earlier OpenAI install.

The user allowlist permitted only `Shell(ls)`, which blocked the skill's Python. Scored chats passed the CLI force flag for that process only. Global sandbox settings were already disabled and were not edited. One earlier improved-skill opening without that flag asked once, waited, and then stopped because Python was rejected. It produced no workbook. That is an environment block, not a prompt result.

## Documents

Four public synthetic files, not four supplier families repeated as if they were new documents:

| File | What it holds | Role |
|---|---|---|
| `digit-boundary-v1` | Three raster invoices: a nearby rule, a real leading digit, and a covered leading digit | Known regression, three runs |
| `cash-memo-classification-v1` | Cash Memo sale, payment receipt, tax invoice/receipt | Known regression, three runs |
| `harbour-meter-v1` | One native-text invoice, a kWh line, and a meter reading | New holdout, one run per arm, plus a second batch |
| `northwharf-receipt-v1` | One raster receipt whose total is partly covered; a clear storage fee and bay remain | New holdout; three improved-skill runs |

The receipt holdout was generated before any model output from it was read. The prompt was not edited after those outputs.

## Opening and stop behaviour

A compliant first invocation asks the exact question once, with both choices, only in the assistant message, calls no question tool, and does not start document work on that turn. A later turn does not ask again. Silence leaves no workbook. Stop leaves no workbook. "No" and "I'm not sure" continue.

Improved skill, 17 October plus the two 18 October receipt repeats: 14 of 14 first invocations met that opening. Silence left no workbook. Stop's second turn did not ask again and left no workbook (14.6 seconds). "No" and "I'm not sure" each produced a harbour workbook of 12 / 12, raw 11 / 11, with no second question. The 18 October second batch in the already-answered harbour chat did not ask again and scored 12 / 12 in 758.9 seconds.

Frozen 0.1.1 did not behave one way. Three completed chats waited with one channel and no question tool: Cash Memo trial 2, the receipt holdout, and digit-boundary trial 5 on 18 October. Other frozen chats called the question tool. Digit-boundary trial 2 called it and finished the workbook in that same turn (15 / 15, blanks 3). Cash Memo trial 1, digit-boundary trials 1 and 3, and the plain "No" chat did not receive the scripted reply, because the runner treated the question tool or a tool listing as document work. Those four have no workbook and are harness gaps, not extraction scores. They were kept. Later frozen runs used a runner that still sends the reply after a question tool or a tool listing. The frozen plain "No" chat was not repeated after that correction.

## Extraction

Official workbook and raw scores use the existing scorer. Arm A did not use the skill sheets, so the automatic flexible matcher is not the result. Its flexible row counts remain in the CSV as a rejected scorer output. The Arm A column review below is the one used here. A layout difference is not counted as a wrong amount.

### Improved skill

| Chat | Day | Workbook | Raw | Opening | Turn 1 + turn 2 seconds |
|---|---|---|---|---|---|
| digit-boundary, three runs | 17 Oct | 15 / 15, blanks 3, each run | 13 / 13, blanks 2, each run | compliant, no repeat | 32.2+501.8, 25.6+493.6, 31.5+552.7 |
| Cash Memo, three runs | 17 Oct | 17 / 17, each run | 9 / 9, each run | compliant, no repeat | 61.3+417.9, 26.4+561.5, 36.2+433.7 |
| harbour meter | 17 Oct | 12 / 12 | 11 / 11 | compliant, no repeat | 26.4+457.4 |
| receipt holdout trial 1 | 17 Oct | 10 / 10, blank 1 | 8 / 8, blank 1 | compliant, no repeat | 33.0+527.9 |
| receipt holdout trial 2 | 18 Oct | 10 / 10, blank 1 | 8 / 8, blank 1 | compliant, no repeat | 160.0+900.2 |
| receipt holdout trial 3 | 18 Oct | 8 / 10, blank 1, silent text 2 | 7 / 8, blank 1, silent text 1 | compliant, no repeat | 160.9+920.3 |

Unprocessed inputs were 0 on every improved workbook above. The covered digit stayed blank and unclear, and the clear 684 and 1684 stayed printed. Cash Memo totals 58 and 93 were present, with Invoice / Receipt / Invoice. Harbour kept invoice HM-7781, total 180.00, the kWh line, and meter reading 45012 kWh. The receipt total stayed blank. Storage fee 80.00 and bay B12 stayed printed on trials 1 and 2.

Trial 3 wrote the storage fee as `80 . 00` on the requested display, the requested value, and the raw observation. The total stayed blank. The spaced fee was not marked unclear, so the scorer counts it as a silent text mismatch. The digits are 80 and 00. This was not used to edit the prompt.

Each receipt workbook also has `unexpected_rows: 1`. On trial 1 that row is a line item with the document number and no line amount. Trials 2 and 3 fire the same check; their extra-row text was not opened separately. The frozen receipt workbook has the same check.

### Frozen skill, completed extractions only

| Chat | Day | Workbook | Raw | Opening |
|---|---|---|---|---|
| digit-boundary trial 2 | 17 Oct | 15 / 15, blanks 3 | 13 / 13, blanks 2 | Question tool, workbook finished in that same turn |
| digit-boundary trial 4 | 18 Oct | 13 / 15, blanks 3, silent text 2 | 13 / 13, blanks 2 | Question and question tool, then a later turn |
| digit-boundary trial 5 | 18 Oct | 15 / 15, blanks 3 | 13 / 13, blanks 2 | Compliant one-channel wait |
| Cash Memo trials 2 and 3 | 17 Oct | 17 / 17 each | 9 / 9 each | Trial 2 waited in one channel. Trial 3 used the question tool, then a later turn. Trial 2's CLI timed out after the workbook existed; duration was not retained |
| harbour, and "I'm not sure" | 17 Oct | 12 / 12 each | 11 / 11 each | Question tool, then a later turn |
| receipt holdout | 17 Oct | 10 / 10, blank 1 | 8 / 8, blank 1 | Compliant one-channel wait |

Digit-boundary trial 4's two silent cells are the requested display `TOTAL: 684` and `TOTAL: 1684`. The billing totals and requested values are the bare numbers, and the covered total is blank and unclear. That is a display-label difference, not a filled covered digit. The raw score does not include those display cells.

### No skill, column review

| Chat | Amounts and types read from the workbook | Seconds |
|---|---|---|
| digit-boundary, three runs | 684 printed, 1684 printed, covered total blank and unclear, each run | 679.6, 665.1, 555.6 |
| Cash Memo trial 1 | Invoice 58, Receipt 58, Invoice 93, line amounts 58 and 93 | 465.7 |
| Cash Memo trial 2 | Same amounts. The sale documents are titled Cash memo and Tax invoice / receipt on the Other sheet, not the skill's Invoice label | 743.5 |
| Cash Memo trial 3 | CLI stopped at 900 seconds after a workbook existed. Columns show Invoice 58, Receipt 58, Invoice 93 and the same line amounts. No summary file was written, so this run is not a CSV row | not a clean exit |
| harbour | HM-7781, total 180, meter 45012 kWh, line 120 kWh at 1.50 totalling 180 | 669.4 |
| receipt | Receipt NW-204, total blank and unclear, storage fee 80 printed, bay B12 | 705.9 |

The no-skill workbooks use different sheet layouts. They do not provide the skill's input-coverage sheet or one stable requested-values layout. Where a column was read, the amounts above were present. Cash Memo trial 2 follows the printed titles rather than the skill rule that a Cash Memo for a sale is an Invoice.

## What this shows an accountant

On these four files, the improved skill waited once, accepted No or uncertainty, stopped when asked to stop, and did not ask again for a second workbook in the same chat. Its finished workbooks use the skill sheets, record printed versus unclear, and keep a source page on requested values. Covered amounts stayed blank. Clear amounts, the Cash Memo totals, the kWh line and the meter reading were present. One of three receipt runs spaced the storage-fee decimal and did not flag it.

The frozen package often produced the same amounts once extraction actually ran. It did not reliably wait in one channel. The no-skill chats also kept the covered amounts blank and the clear amounts, under the same explicit instruction, with less stable sheets and one Cash Memo run that did not use the skill's Invoice label.

The shared covered-digit sentence was given to every arm. Abstaining on the covered digit therefore cannot be credited to the prompt change alone. The 2026-10-15 misses remain a separate batch under a different reported model label and an older CLI.

No arm is a measured saving of accountant review time. No currency cost was returned.

## Checks

The `tests/` suite passed 346 tests, including the Cursor adapter, the new holdout fixtures, package build and the publication scan. `tools/check.py` passed. Grok Build was not executed. Nothing was committed, pushed, released, or made public by this comparison.
