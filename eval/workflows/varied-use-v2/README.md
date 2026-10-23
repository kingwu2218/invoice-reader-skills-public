# Varied first-use reference v2: certificate identity erratum

V1 mistakenly used worksheet bucket `Other` as certificate `Document type`.
The pre-existing [document-type rule](../../../core/references/document-types.md)
requires a short plain name for other documents; the
[extraction example](../../../core/references/extraction.md) already uses
`Lab certificate`. Both model trials followed that instruction and routed the
certificate correctly to the Other sheet.

V2 changes only certificate identity values from Other to Lab certificate in
both purposes/layers. All printed values, absent fields, row ordering, identity
columns and grading code remain unchanged. Sources are the v1 PDFs. V1 references,
plans, grades and model outputs are preserved.

This correction was made after observing the two 0.3.16 outputs. Regrading those
outputs is retrospective and must not be called a prospectively frozen pass.
The original `varied_use.py` runner remains frozen to v1 for reproducibility; do
not use it for a new corrected benchmark without a separately versioned plan.
The review tool validates that only the declared identity erratum changed,
verifies archived raw/workbook evidence, and reproduces old grades before issuing
new, separately named JSON/CSV reports. New reviewer-authored references are not
evidence that the model extracted a missing field.

```text
python eval/tools/review_varied_use.py review eval/runs/ORIGINAL_BATCH --out NEW_REFERENCE_REVIEW.json
```

## Prospective confirmation

Use `eval/runner/varied_use_v2.py` for fresh execution. It loads the unchanged v1
execution/scoring engine in an isolated module namespace with the protocol and
reference directory set to v2. The historical v1 module and grader remain intact;
both runner files and their dependencies are frozen in each new plan. Existing
v2 JSON answers are copied byte-for-byte before calls. No output is used to update
an answer. Plans of the wrong version are rejected before an attempt is reserved.

This reuses the known synthetic PDFs and the same payment/quality prompts. Two
fresh sessions (one per purpose), one opening and one reply attempt each, receive
only the installed package and PDFs. No earlier examples, settings or answers
are supplied. The scripted read-later response is labelled public test input.
Opening v9 and raw/workbook scorers are unchanged. Every error is retained; no
retry replaces an output. Correct blanks stay outside accuracy denominators.

```text
python eval/runner/varied_use_v2.py plan eval/runs/NEW_V2_BATCH --workspace-root NEW_EXTERNAL_DIRECTORY --model YOUR_SELECTED_MODEL_ID --provider "ACTUAL_ACCOUNT_ROUTE"
python eval/runner/varied_use_v2.py start eval/runs/NEW_V2_BATCH --trial 1
python eval/runner/varied_use_v2.py reply eval/runs/NEW_V2_BATCH --trial 1
python eval/runner/varied_use_v2.py start eval/runs/NEW_V2_BATCH --trial 2
python eval/runner/varied_use_v2.py reply eval/runs/NEW_V2_BATCH --trial 2
python eval/runner/varied_use_v2.py report eval/runs/NEW_V2_BATCH --out NEW_REPORT.json
```

These are fresh executions of known content, not new independent documents or
evidence of general handwriting accuracy. Compare them with the retrospective
v2 results separately; never replace the original v1 scores.
