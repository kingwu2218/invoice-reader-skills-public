# Raw invoice and statement line evaluator regression

Added raw line scoring after the 0.3.4 model run exposed a coverage limitation: its raw checks covered document/custom fields, while quantities, unit prices and line totals were checked only in the workbook. A workbook can contain an equivalent number even when its raw transcription has lost printed notation. The evaluator can now grade both layers for new cases.

This is a **deterministic evaluator test**, with supplied invented JSON and independently specified references. No model or PDF was read in this evaluation; it is not a new model accuracy result. Family prompts, packages, version 0.3.4 and historical reference answers remain unchanged.

| Controlled input | Nonblank field checks | Invoice row slots | Statement row slots | Extraction result |
|---|---:|---:|---:|---|
| Correct supplied transcription | 25 / 25 | 4 / 4 | 2 / 2 | Pass |
| Omit wholly unreadable row | 25 / 25 | 3 / 4 | 2 / 2 | Fail: missing row |
| Rewrite `1,250.00` as `1250` | 24 / 25 | 4 / 4 | 2 / 2 | Fail: changed notation |
| Repair printed `2,490.00` to `2,500.00` | 24 / 25 | 4 / 4 | 2 / 2 | Fail: changed amount |
| Reverse two invoice lines | 15 / 25 | 4 / 4 | 2 / 2 | Fail: wrong row values |
| Fill a value flagged unclear | 25 / 26 | 4 / 4 | 2 / 2 | Fail: invented value |
| Move a debit into credit | 24 / 26 | 4 / 4 | 2 / 2 | Fail: missing debit and invented credit |

All **7 / 7 expected evaluator outcomes** occurred. The six faulty inputs are deliberate negative controls, not model failures. Do not aggregate their field fractions into a model accuracy score. Seven correct blank comparisons are excluded in the baseline; an invented value adds an error opportunity. The existing scorer counts blank-vs-missing cells as correct blanks, so the missing-row check is essential and independently fails the command. Source/ordinal row coverage can remain perfect despite swapped values; it must be read alongside field accuracy.

The reference identity uses file, document pages, document type, document occurrence and line position. Two same-page invoices test document-local numbering; model-generated document IDs and field contents cannot be matching keys. `Pages` is the document range, not a claim of precise line-page grounding. Text comparison retains the existing whitespace collapsing but does not normalize punctuation, amounts, dates or leading zeroes. Unclear flags never suppress supplied strings during grading; the flags themselves are outside this line-field score.

Added **12 regression tests** covering those cases plus duplicated rows, missing units, lost leading zeroes, changed dates, wrong source page, an extra blank row, invalid reference identities, duplicate references, non-text comparisons, reference preflight and CSV/CLI failure behavior. Full suite: **121 / 121 tests passed**. Generated-package checks passed; no package rebuild was needed for evaluator-only changes.

Reproduce with `python -m unittest discover -s tests -p test_raw_lines.py -v`. See the [fixture and contract](../../eval/scorer-cases/raw-lines-v1/README.md), [matrix](2026-10-08-raw-lines-regression.csv) and [detailed results with input/evaluator hashes](2026-10-08-raw-lines-regression.json). Future live scenarios must freeze line-level answers before execution; this change does not retroactively expand the 42 / 42 raw denominator in the earlier model report. No commit or push.
