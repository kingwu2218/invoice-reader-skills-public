# Cursor xAI baseline, 2026-10-11

Experimental explicit Cursor package for the existing xAI prompt. This is a preparation and capability record. It is not a model-accuracy result.

## Result

No fresh extraction chat was run. Workbook and raw accuracy are **not run**. Correct blanks were not scored. Prepared workspaces, failed attempts, and this report are kept; nothing was selected as a best run.

`digit-boundary-v1` and `cash-memo-classification-v1` have locked raw references. `coal-ocr-payment` and `coal-ocr-energy` do not, so their raw accuracy is **not configured**. Those references were hashed before any extraction and were not edited after the capability smoke.

| Case | Raw reference | Raw accuracy | Workbook accuracy | Correct blanks |
|---|---|---|---|---|
| digit-boundary-v1 | configured | not run | not run | not run |
| cash-memo-classification-v1 | configured | not run | not run | not run |
| coal-ocr-payment | not configured | not configured | not run | not run |
| coal-ocr-energy | not configured | not configured | not run | not run |

Not run, and therefore not counted: missing documents, wrong classification, guessed values, missed values, silent amount changes, and omitted units, pages, or samples.

## Why extraction was not claimed

Cursor's CLI docs, reviewed on 2026-10-11, describe a fresh chat with `agent create-chat` and exact continuation with `--resume [chatId]`. The local PATH has no `agent` executable, and the user-level `.cursor/bin` directory is absent. The documented Windows install command was not run. This IDE chat had already been used to prepare and score, so it cannot be counted as a blind extraction.

Paste prompts and isolated workspaces are ready. Each model-visible folder contains the package, one public PDF, `custom.md`, and a synthetic company profile. `expected.json` and the scripted reply stay in the sibling `run-1` folder.

## What was checked

| Check | Evidence | Status |
|---|---|---|
| Shell write | PowerShell and Python each wrote a file under `eval/runs/cursor-capability-smoke/` and the Python file read back `py-write-ok` | passed in this IDE chat |
| PDF render | `core/scripts/render_pages.py` rendered page 1 of public `eval/fixtures/digit-boundary-v1.pdf` at 72 DPI and reported 3 pages | passed |
| Image tool | This IDE chat's file reader returned that PNG as an image. A page image was visible | passed in this IDE chat only |
| Fresh skill chat | `agent` CLI absent; `create-chat` / `--resume` not executed | not run |
| Policy opening | No new skill chat | not observed |

The PDF probe used Python 3.14.5, Pillow 12.3.0, and pypdfium2 4.30.0. The scripts declare `pypdfium2>=5.13,<6` for a managed `uv` run. `uv` was not on PATH, so that managed runtime was not used. The installed 4.30.0 library still rendered a page. `reading_capabilities.py --vision available --ocr off` reported PDF rendering usable on a blank page. Its vision field is caller-supplied; it does not detect an image tool. Tesseract was not probed.

Rendering and the probe do not mean a model read the page. The image-tool observation is limited to this maintainer chat. The visible values were not copied into the case workspaces or this report, and they are not an extraction score.

## Identity and route

| Item | Record |
|---|---|
| Requested tool / model / effort | Cursor, Grok 4.7, Effort High. Source: the user message in this chat on 2026-10-11 |
| Model ID reported by a tool | Unknown. No CLI init event supplied a model ID |
| Effort reported by a tool | Unknown |
| Self-report | The assistant is identified in this conversation as Grok 4.7. That is not a verified model ID |
| Provider / account route | Unknown. `agent status` and `agent about` were not run |
| Cursor editor | 3.23.12, commit `2d29876d567da1607532b23bbf2cd5ddbca496f0`, x64, from `cursor --version` |
| Cursor Agent CLI | Not found on PATH |

The adapter does not pass `--model` or an effort flag. The package has no `model` field.

## Docs used for the adapter

Reviewed 2026-10-11, not guessed:

- [Agent Skills](https://cursor.com/docs/skills): `.cursor/skills/<name>/SKILL.md`; `disable-model-invocation: true` loads the skill only for explicit `/skill-name`. A slash invocation attaches to one message. Custom Mode keeps it for the session: Alt+Enter on Windows, Option+Enter on macOS.
- [Rules](https://cursor.com/docs/rules): `alwaysApply: true` is included in every chat. `alwaysApply: false` with no description and no globs is manual `@` mention. This package is a skill, not an always-apply rule.
- [CLI parameters](https://cursor.com/docs/cli/reference/parameters): `agent create-chat`, `--resume [chatId]`, `-p`, `--output-format`, `--trust`, and `--model`. `--model` exists and is intentionally unused.
- [Output format](https://cursor.com/docs/cli/reference/output-format): stream JSON `system/init` may include a model display name and `apiKeySource`; a terminal `result` with `subtype: success` is completion telemetry only.
- [CLI installation](https://cursor.com/docs/cli/installation): Windows install is `irm 'https://cursor.com/install?win32=true' | iex`, then `agent --version`. Not run.

Cursor also loads `.agents/skills/`, `.claude/skills/`, and `.codex/skills/`. The install note says to copy this package only to `.cursor/skills/invoice-reader-xai-cursor/`.

## Frozen artifacts

| Artifact | Hash |
|---|---|
| `dist/cursor/invoice-reader-xai-cursor` | `ba89c43560d1cfc8362135ea9465be5f44f4769f338ca6522501df1fa4527657` |
| `skills/xai` | `46dc6e841526797800aaec99b806514055965619ed5598de1615744ef66cb175` |
| `adapters/cursor` | `d965459316b20034521c2ff0e572d7a874106f936fac81dfbea25ec8f64bb588` |
| `dist/codex/invoice-reader-openai` | `2f03d23ca01d755c4cf6ed94c752d809ef03df201a94a26d8b8c49dc11bd7743` |
| `eval/runner/opening_v9.py` | `4e4e083323835f3a8579b818a5b64b7af49e03e482aecd420b57a2dbd59a6c16` |

The OpenAI 0.3.16 package hash and the v9 hash match the previously published difficult-regression record. Rendering the Cursor package did not change the OpenAI, Grok Build, Gemini, or Claude package trees, or `skills/xai`. Codex opening v9 was not used and was not edited. Cursor openings need their own observation record.

Family version remains 0.1.1 because the xAI prompt was not edited. `invoice-reader-xai-cursor` is manual only. `dist/grok-build/invoice-reader-xai` remains the Grok Build preview.

Dataset hashes, source plus custom settings plus the locked reference:

| Case | Dataset hash |
|---|---|
| digit-boundary-v1 | `4f1e780a2a78956b2d4162eaa0dd43ef0b6432ee61e81df9eec57ac99cd240a9` |
| cash-memo-classification-v1 | `f7f7dbf181e13e653b37623b679c5deef54d22374aa097cc48d877cba4674fca` |
| coal-ocr-payment | `23b53e701fb5fc5e322a35e5d2d3496ab5d122e94c751cf44931725192460ca1` |
| coal-ocr-energy | `89fb8d67d5a7d506dbc0100edd1f9be4b37093e5da160d6b2b925aa53f883c1a` |

## Cursor opening checklist

These items are separate from Codex v9. None were observed, because no new skill chat ran.

| Check | Result |
|---|---|
| Exact question once: "Have you read the Readme about the data policy for your model?" | not observed |
| Choice "Yes, I have read it." | not observed |
| Choice "No, but I will read it before I upload any confidential data" | not observed |
| Pause before document work | not observed |
| Extra confirmation | not observed |
| Yes-only gate | not observed |

The skill text already contains the question and both choices. That is instruction text, not an observed opening. A scripted public reply is stored beside each workspace and labelled `SCRIPTED PUBLIC FIXTURE, NOT A HUMAN CONFIRMATION`. It was not sent. Sending it later would test reply handling, not human confirmation.

## Tests

`tests.test_cursor_adapter` and `tests.test_build` passed after the final paste-text edit (11 tests). The earlier run that also included `tests.test_cli_readiness` passed (13 tests). `python tools/check.py` passed after the package build. These tests check packaging, explicit invocation, answer-file isolation, and stream parsing. They are not model accuracy.

## Limits and next step

Install and authenticate Cursor Agent CLI only if a headless fresh chat is wanted, then use `agent create-chat` and `--resume` with that same ID. Do not pass `--model`. Until that exists, open each case workspace below as its own Cursor folder, start a new Agent chat, keep the current model and effort, and invoke `/invoice-reader-xai-cursor` as a Custom Mode with Alt+Enter. Paste the matching `PASTE-OPENING.txt`. Reply to the policy question in that chat. For a public fixture, the reply can be the scripted read-later line, and the score must label it scripted.

Score a finished `output.xlsx` with `eval/runner/score.py` only after copying the workbook into that case's `run-1` folder and recording a raw extraction hash when raw scoring is configured. Do not overwrite this baseline, do not drop failed attempts, and do not change the xAI prompt to chase a score.
