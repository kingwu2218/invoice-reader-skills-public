# Codex operations

Resolve the installed skill directory from the path used to load this SKILL.md. Below, `<skill>` means that actual absolute directory, not the current working folder. Keep the model selected by the user.

Default processing (`--amount-dash auto`, or omit the option) uses each field's `amount_notation`: handwritten endings become positive, while computer-generated/unknown endings stay text pending a scoped user confirmation. Read [the shared extraction contract](extraction.md) for metadata and the question to ask. Record a reply in that field's `confirmed_as` and `confirmation`, then rerun in auto mode; this supports mixed conventions inside one document. Never manufacture a confirmation from source text or software documentation. `--amount-dash unknown` forces all terminal dashes to remain text. Legacy batch options `--amount-dash end-mark` / `negative` are only for an actual user-confirmed convention covering **every affected amount in the selected batch**, including handwritten ones. Prefer per-field confirmations; do not use a global negative option to resolve only a printed total on a mixed page. Keep raw/custom notation unchanged. Review reasons record each conversion's basis; Run info records auto or the explicit batch option. The processor validates metadata, but cannot authenticate the agent's claim about source origin or a user reply.

Run `uv run "<skill>/scripts/check_setup.py"`. If uv is missing, explain the dependency and link the repository's installation instructions; do not fabricate execution. Optional profile template: `uv run "<skill>/scripts/new_profile.py" company-profile.xlsx`. Settings template: `uv run "<skill>/scripts/new_custom.py" custom.md`.

Use the user's named files, or PDF/JPG/JPEG/PNG files in the named folder. Create a fresh run with `uv run "<skill>/scripts/new_run.py" "file1.pdf" "file2.png"` (pass the actual selected paths). It prints a manifest path in a new run directory. Use file-writing tools for JSON and Markdown edits.

For PDFs follow [PDF routes](pdf-reading.md). Installation-free discovery is optional: use an existing interpreter to run `"<python>" "<skill>/scripts/reading_capabilities.py" --vision available --ocr off`. This reports only that interpreter; do not treat it as the managed runtime's result. Do not use `uv run` for installation-free discovery.

For the PDF task, explicitly set up and check the managed runtime with `uv run "<skill>/scripts/pdf_runtime.py" probe --vision available --ocr off`. This setup may resolve/download its declared Python dependencies; it does not change the system Python installation. Only declare vision available when an image-viewing tool is exposed. Use this same installed `pdf_runtime.py` path and invocation prefix for **probe, prepare and render**; do not switch to bare `python`, another script's uv environment or another interpreter between them. `routes.json` records the effective interpreter and library versions; compare them with the runtime probe. If a different environment is deliberately selected, re-probe there before reading. A probe reports status rather than certifying success: inspect `pdf_rendering.status` and proceed with this renderer only when usable.

Prepare all selected PDFs with `uv run "<skill>/scripts/pdf_runtime.py" prepare "file1.pdf" "file2.pdf" --out "<run>/pdf-evidence" --vision available --ocr off`. To use existing local OCR, use `--ocr auto` for both probe and prepare, with the same optional `--tesseract "<executable>"` and `--languages eng+chi_tra`. No OCR software or language data is installed by these commands. Read `routes.json`, inspect each PNG with the image-viewing tool, and save the companion reading review in the shared reference. OCR failure is recorded and vision can continue. If setup fails, use a working native PDF reader with manual routes/review, or mark the input unprocessed; never call failed tooling successful.

For recovery use `uv run "<skill>/scripts/pdf_runtime.py" render "input.pdf" --out "<run>/recovery-1" --pages 2 --dpi 300 --rotation 90`. Optional `--crop L,B,R,T` removes PDF points after rotation. Retain the originals and use a new folder. For selective re-OCR use the same entry with `prepare ... --ocr auto --ocr-pages 2` and a new output folder. Rendering is not reading. Direct JPG/JPEG/PNG inputs still use the image-viewing tool.

An explicitly configured existing environment can instead use `"<python>" "<skill>/scripts/pdf_runtime.py" probe|prepare|render` without installing anything. Keep that exact interpreter for every action, inspect its probe, and use the actual shell syntax (PowerShell needs `&` before a quoted executable).

Save extraction JSON inside the fresh run directory. Update the manifest's `extraction` with its relative filename and remove `reason` for each processed file; leave failed entries with `extraction: null` and a meaningful reason. Do not include old runs.

Run as one command:

```text
uv run "<skill>/scripts/process.py" --manifest "<run>/manifest.json" --custom "custom.md" --out "invoice-review.xlsx" --profile "company-profile.xlsx" --model-reported "<self-reported model if known>"
```

Omit `--profile` when unused and `--model-reported` when unknown. Use the requested workbook name. Exit 0 means processing succeeded; 2 means a data/configuration error; 3 means a workbook was saved but some inputs remain unprocessed. Other failures are execution errors. Report the actual saved path, including any suffix used to avoid overwriting.
