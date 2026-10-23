# Cursor operations

This experimental adapter loads the shared xAI-family prompt in Cursor. It does not select a model, an effort level, or an account. Keep the user's current selection. A self-reported model name is not verified identity. Grok Build installation and its policy route do not apply here; record the actual Cursor account route separately, or leave it unknown.

Reviewed on 2026-10-11 from Cursor's Agent Skills and Rules docs. Install by copying this whole package to `.cursor/skills/invoice-reader-xai-cursor/` in the document workspace. The folder name must match the `name` field. Leave `disable-model-invocation: true` in place, and do not add `model`, effort, `paths`, or `alwaysApply`. Do not also copy the package into `.agents/skills/`, `.claude/skills/`, or `.codex/skills/`: Cursor loads those locations too, and a second copy can compete. Do not install an always-apply rule for this workflow. A project rule with `alwaysApply: true` is included in every chat; this package stays explicit.

Invoke `/invoice-reader-xai-cursor`. The docs say that slash invocation attaches to one message. For a chat that must wait for a policy reply and then continue, start the skill as a Custom Mode: select it in the `/` menu and press Alt+Enter on Windows or Option+Enter on macOS. A one-message slash attach is not session-long loading.

Resolve `<skill>` from the SKILL.md path actually loaded. All script paths below are inside that package. The family prompt asks the policy question; do not add another confirmation. Begin document work only after the chat's policy reply.

Ask that question only as the assistant message, then stop. Do not call AskQuestion or any other question tool. In Cursor that call does not wait for the user and is not a reply. The question turn contains no other tool call. After a later user message, continue without asking again. No or an uncertain reply continues the task. A stop request ends it.

Cursor's agent can run a shell and write files. PowerShell needs `&` before a quoted executable. Use an existing Python interpreter (`<python>`) when one is supplied. Check that environment with:

```text
<python> "<skill>/scripts/pdf_runtime.py" probe --vision unknown --ocr off
```

Declare vision available only after an exposed tool returns the picture itself. Reading a PNG path, a renderer exit code, OCR text, or a probe flag supplied by the caller is not that evidence. If no image content comes back, rerun the probe with `--vision unavailable` and follow the partial-input rules in [PDF reading](pdf-reading.md). Do not install software or change Cursor model settings during discovery. If Python is unavailable, say so. A native reader may still capture partial information, but it cannot establish workbook creation.

`uv` is optional explicit setup for the scripts' declared dependencies. Discovery does not install them. An existing interpreter may report a PDFium version outside that declared range; record the probe and do not relabel it as the managed runtime. Use `new_custom.py` or `new_profile.py` only when templates are needed. Reuse the user's settings outside the installed package.

Create a fresh run with the selected files:

```text
<python> "<skill>/scripts/new_run.py" "input.pdf"
<python> "<skill>/scripts/pdf_runtime.py" prepare "input.pdf" --out "<run>/pdf-evidence" --vision available --ocr off
```

Pass every selected PDF. Use the same interpreter and the same `pdf_runtime.py` entry for probe, prepare, and render. Optional `--tesseract` and `--languages` select an existing OCR engine; `--ocr auto` on both probe and prepare enables it. `--ocr off` disables it. Inspect the pages, preserve physical page references, and save `reading-review.json` separately from `routes.json`. Keep failed inputs visible. Recovery uses a new output directory:

```text
<python> "<skill>/scripts/pdf_runtime.py" render "input.pdf" --out "<run>/recovery-1" --pages 2 --dpi 300 --rotation 90
```

Optional `--crop L,B,R,T` removes PDF points after rotation. Inspect the result; rendering is not reading. Direct image inputs also require visual inspection.

Read [extraction contract](extraction.md) before saving JSON. Set each processed manifest entry's extraction to its relative JSON filename and remove its reason; failures retain `extraction: null` and a reason. Use [amount notation](amount-notation.md) per field: handwritten terminal dashes are end marks; computer or unknown origins need a scoped user reply before numeric conversion. Never infer a reply or apply a global convention to mixed origins.

```text
<python> "<skill>/scripts/process.py" --manifest "<run>/manifest.json" --custom "custom.md" --out "invoice-review.xlsx"
```

Add `--profile` only when a profile is used. Add `--model-reported` only for a self-reported name, and label it self-reported. Exit 0 means processing succeeded, 2 is invalid input or configuration, and 3 means a workbook with unprocessed inputs. Other errors are execution failures. Return the actual saved path and limitations. Never fabricate execution or hide review flags. Keep the shared scripts unchanged.
