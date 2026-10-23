# Image-only PDF with raw line references

The existing public `coal-scan.pdf` supports two purposes, payment details and coal energy measurements. The new `coal-scan-*-lines-v2` scenarios add raw document, custom-observation and invoice-line checks to the existing workbook expectations. They expect route B for both physical pages. Rendered pages were reviewed before the new executions; the PDF contains no usable native text. It remains known public content, also illustrated in shared references, not a holdout or evidence of unseen-document recognition.

Run with the staged conversation evaluator after an actual policy acknowledgement. Freeze source/configuration/answer/package hashes before execution. Do not infer successful image inspection from correct answers or a model-authored review ledger. The autonomous tool choice remains part of the trace: no page attachments or OCR output are injected by these scenarios.

## Reference correction

The initial `v1` references incorrectly used `Other` as the certificate's raw document type. The extraction contract permits short plain names for nonstandard documents, such as `Lab certificate`; `Other` is their worksheet destination. This reference defect was identified from the documented contract while the v1 runs were in progress, before inspecting their extracted answers. The v1 inputs, answers and scores are retained.

Version 2 removes document type from raw document/custom matching for this fixture, which has exactly one document per page. It retains source filename, document pages and occurrence, plus custom key/occurrence where relevant. Invoice line identity remains the full source/type/document/line contract. Values and workbook expectations are unchanged. This fixture-specific key choice must not be copied to ambiguous multi-document pages without independently identifying each record.

`python eval/tools/make_scan_line_cases.py --version 2` generates the versioned settings and refuses to overwrite them. The generator defaults to v2; `--version 1` exists only to reproduce the frozen historical reference defect. Regression tests verify both versions, arbitrary certificate type names, both user purposes and detection of a changed line amount.
