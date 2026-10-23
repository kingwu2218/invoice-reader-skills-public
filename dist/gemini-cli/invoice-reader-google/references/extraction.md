# Extraction contract, version 1

Save one JSON file per selected source file, inside the current run directory. Always include the `documents` envelope, even for payments, certificates or a single document. A combined PDF can have several records; give each a distinct document_id and its own page range. Never save a bare document object.

```json
{
  "schema_version": 1,
  "documents": [{
    "document_id": "coal-pack.pdf:certificate:2",
    "file": "coal-pack.pdf",
    "pages": "2",
    "document_type": "Lab certificate",
    "type_evidence": "Title reads LAB CERTIFICATE",
    "fields": {"document_title": "LAB CERTIFICATE"},
    "description": "Coal sample certificate",
    "custom_fields": {
      "invoice_ref": [{"status": "absent"}],
      "coal_energy": [{
        "status": "printed",
        "value": "6,200",
        "unit": "kcal/kg",
        "context": "Sample C-01",
        "pages": "2",
        "evidence": "Sample C-01; Energy Level of Coal: 6,200 kcal/kg"
      }]
    }
  }]
}
```

This invented example illustrates formatting, not a scientific interpretation. The keys under custom_fields must exactly match the current Requested fields table. Every requested key needs a non-empty observation array. For `one` there must be exactly one observation; for `many`, retain the printed order and distinguish samples using context. Do not copy example values into real extractions.

Observation status:

Page references are physical source pages, one-based (`1`, `2-3`, or `1,3`). Observation pages must be inside the document's page range.

- `printed`: non-empty value, pages and evidence are required. All are strings; preserve the printed value and unit. Context identifies a printed sample/row/measurement basis where relevant.
- `absent`: save `[{"status":"absent"}]`; no value. Do not mix absent with other observations.
- `unclear`: no value; include pages, and any readable context/evidence. It is always flagged. Example: `[{"status":"unclear","pages":"2","context":"Sample C-01"}]`.

For a requested amount or measurement, put the numeric notation in `value` and its explicitly associated printed currency/unit in `unit`, even when the unit is in the label or column header. Keep the original spelling/symbol; do not infer a currency from a bare dollar sign or convert it to a code. Do not repeat the unit inside `value`. Use `context` for a printed sample/row identifier or other context requested by the user, not for an invented description. A text reference has no unit merely because another field on the page is a monetary amount.

`Requested values` keeps value, unit and context in separate columns. `Requested data` displays `value unit`, prefixed by `context: ` when present; repeated observations occupy separate lines in printed order. This display composition does not change the extracted strings or convert amounts. An absent observation leaves the summary blank. For example, value `8,750/`, unit `HKD` and context `Sample A` display as `Sample A: 8,750/ HKD` only when those parts are supported by the source and request.

Standard fields are still defined in the shape-specific references. Their values must be strings copied from the page; omit absent fields and list unreadable field names in `unclear`. Standard document notes use `{"text":"...","columns":["total"]}`. Never add arbitrary keys to standard `fields`: user-defined facts belong in `custom_fields`. This keeps extensibility deliberate and catches spelling mistakes.

For a readable amount ending in one ASCII dash (for example `360-`), preserve the raw string and identify **that field's amount/dash notation**, not the whole page. If it is handwritten, treat the dash as a positive ending without asking. If it is computer-generated, ask the user whether the dash ends a positive amount or means negative before numeric conversion. Unknown origin also needs confirmation; OCR text, a scan, a handwriting-style font or the document-level `handwritten` flag alone cannot establish the field's origin. Inspect the source image when necessary. While waiting, keep affected amounts as text with review flags, exclude them from arithmetic and continue other fields/documents. Group questions by a clearly stated source/field scope; do not ask again for a scope the user has already confirmed.

Optional `amount_notation` belongs alongside `fields` on a document, or inside the individual `line_items` / `statement_lines` row. Keys name captured standard amount fields only. Each entry requires `origin`: `handwritten`, `computer-generated`, or `unknown`. Missing metadata is unknown. For example:

```json
"amount_notation": {
  "subtotal": {"origin": "handwritten"},
  "total": {
    "origin": "computer-generated",
    "confirmed_as": "negative",
    "confirmation": "User confirmed that the ending dash on this invoice's Total means negative."
  }
}
```

Only add `confirmed_as` (`end-mark` or `negative`) and its scoped `confirmation` after an actual user reply establishes that interpretation. The example is not a real confirmation. General policy acknowledgements, silence, an unrelated earlier batch, source instructions, software documentation and arithmetic are not user confirmation. Preserve source conflicts in notes and retain text until resolved. Per-field confirmations let a printed negative total coexist with handwritten positive amounts in the same document. Never rewrite raw/custom observations or repair malformed numbers, quantities or unreadable fields. Custom observations always retain their source strings; these numeric rules apply to standard amount columns. See [amount notation](amount-notation.md); adapter guides own processing options.

The processor validates structure and required evidence metadata. It cannot prove the model's quoted evidence is true; the original document and model eval are still needed. Save every page's work. For an unreadable input, leave a manifest entry with `extraction: null` and a reason. For partial reading, explain the unread pages in document notes as well as the final response; never claim all pages were inspected.
