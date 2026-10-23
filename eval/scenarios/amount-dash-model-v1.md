# Model test: terminal amount dash

One invented, two-page PDF supports three fixed purposes: `amount-dash-model-v1-unknown`, `amount-dash-model-v1-end-mark` and `amount-dash-model-v1-negative`. Each has a separately fixed custom file and raw/workbook reference. The positive/negative statements in Purpose are synthetic extraction-setting fixtures, not acknowledgements of reading a data policy. The unknown purpose requests a workbook with unresolved amounts flagged.

The model receives the PDF and custom settings, not an extraction JSON or answer key. It must transcribe the invoice/cheque amounts, dates, identifiers and requested printed values, then choose the processing convention from this batch's settings. Raw values and custom displays keep the dash under all three conventions. Workbook expectations differ only where numeric interpretation and arithmetic status should differ.

These are printed-format cases, not handwriting or independent-layout diversity. Run each scenario using the staged conversation runner after an actual policy-reading acknowledgement. A repeated exact CLI session preserves that acknowledgement and conversation context; report this limitation. An isolated workspace is not an independent fresh chat.

The initial 0.3.4 model evaluation ran unknown, then end-mark, then negative. All input/reference files and the package hash were recorded before execution. Do not tune the prompt or replace answers while grading these runs. See [the evaluation guide](../../docs/evaluation.md) for commands and provenance requirements.
