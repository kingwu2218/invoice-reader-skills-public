# Gemini CLI operations

This is an experimental adapter preview; local model/tool integration has not been evaluated. Keep this preview outside .gemini/skills and .agents/skills. Explicitly ask Gemini to read the package's SKILL.md by path. Native discovery may activate skills automatically, so this preview uses manual file-path invocation until an explicit-only native integration is tested. Keep the user's selected model and account unchanged.

Resolve <skill> from the SKILL.md path actually loaded. All script paths below are inside that complete generated package. Begin these operations only after the chat's policy reply.

Use an existing Python interpreter (<python>); PowerShell uses & before a quoted executable. Check the current environment with:

```text
<python> "<skill>/scripts/reading_capabilities.py" --vision unknown
```

Declare vision available only if an exposed tool actually returns image content. Use the CLI's available image/file reader to inspect rendered PNGs; shell text output or an OCR transcript is not visual evidence. If images cannot be viewed, record that limitation and apply the partial-input rules in [PDF reading](pdf-reading.md). Do not install dependencies or alter CLI permissions during discovery. If Python is unavailable, explain the missing capability; a working native reader may still capture partial information, but cannot establish workbook creation.

With a working interpreter, run check_setup.py. An explicitly approved dependency setup may use uv; discovery never uses uv. Use new_custom.py or new_profile.py only when templates are needed. Reuse the user's settings outside the installed package.

Create a fresh run using the actual selected paths:

```text
<python> "<skill>/scripts/new_run.py" "input.pdf"
<python> "<skill>/scripts/pdf_routes.py" "input.pdf" --out "<run>/pdf-evidence" --vision available
```

For multiple PDFs pass every selected path. Optional --tesseract and --languages select existing OCR; --ocr off disables it. Inspect the pages, preserve physical page references and save reading-review.json separately from routes.json. Keep failed inputs visible. Recovery may use render_pages.py with --pages, --dpi, --rotation or --crop in a new output directory; inspect the result rather than treating rendering as reading. Direct image inputs also require visual inspection.

Read [extraction contract](extraction.md) before saving JSON. Set each processed manifest entry's extraction to its relative JSON filename and remove its reason; failures retain extraction: null and a reason. Use [amount notation](amount-notation.md) per field: handwritten terminal dashes are end marks; computer/unknown origins need a scoped user reply before numeric conversion. Never infer a reply or apply a global convention to mixed origins.

```text
<python> "<skill>/scripts/process.py" --manifest "<run>/manifest.json" --custom "custom.md" --out "invoice-review.xlsx"
```

Add --profile only when used; add --model-reported only when known and label it self-reported. Exit 0 means processing succeeded, 2 is invalid input/configuration and 3 means a workbook with unprocessed inputs. Other errors are execution failures. Return the actual saved path and limitations; never fabricate execution or hide review flags. Keep the shared scripts unchanged.
