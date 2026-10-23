# Terminal amount dash: deterministic processor cases

These are invented transcription strings, not a source PDF or model extraction. The source filename inside JSON is a synthetic identity only. No user/company documents are used.

The same input is processed with three independently fixed meanings: unknown (keep text and exclude it from arithmetic), end-mark (positive), and negative. Expectations cover invoice totals, cheque amounts, line items, statement amounts and unchanged custom observations. Every dash interpretation remains flagged. No expected values come from processor output.

Run `python eval/runner/processor.py`. Results are processor checks, not handwriting or LLM accuracy. The runner records input/reference/script hashes, selected mode and raw-input preservation, and uses the shared workbook scorer. Do not revise historical model-eval references based on this fixture.
