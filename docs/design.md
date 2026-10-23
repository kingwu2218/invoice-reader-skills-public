# Architecture

The MVP targets **ChatGPT / OpenAI through Codex CLI**. Gemini and Grok follow in the next phase. The maintenance unit remains a model family, not a model version or a tool/model combination. Decisions and earlier designs are retained in [development-log.md](development-log.md).

## Primary targets and delivery sequence

Use product names in user-facing selection and provider-family keys for maintained sources: Gemini maps to `google`, Grok to `xai`, and ChatGPT to `openai`. These are repository routing labels, not a claim that a product name identifies the exact active model or account policy. Keep one recommended model per family in metadata; other models reuse the same prompt. Existing OpenAI recommendations remain metadata, while Gemini and Grok recommendations are pending evaluation.

The owner selected CLI delivery on 2026-10-11: Gemini CLI, Grok Build CLI and the existing Codex CLI route. Browser and mobile app adapters are outside this phase. `skills/google/` and `skills/xai/` now contain initial family prompts alongside `skills/openai/`. Their 0.1.0 packages are buildable previews with preparation-only eval adapters; live integration is pending. Each family references the shared extraction contract. CLI adapters own document access, image inspection, execution capabilities, installation/use instructions and evaluation capture. They check the running environment for Python, Tesseract, filesystem access and image tools rather than assuming that CLI use supplies them.

The existing `skills/anthropic/`, Claude Code adapter, generated package and reports remain available as secondary support. Preserve their evidence and identifiers; do not relabel Claude as another family or remove working support merely to change priorities. GitHub Copilot remains deferred. An experimental Cursor package reuses the xAI prompt with explicit invocation; it is not an automatic default and does not replace the Grok Build preview or the OpenAI MVP.

Delivery sequence:

1. Finish the OpenAI experimental MVP using `skills/openai/`, `adapters/codex/` and the existing staged evaluator. Prioritize a clear installation path, a clean-install smoke test, truthful limitations and reproducible public evaluations. Resolve opening-format failures before claiming full workflow qualification. Current delivery uses Codex CLI with the user's selected model/account; ordinary ChatGPT browser skill installation is not implemented.
2. In the next phase, smoke-test the existing Gemini CLI and Grok Build previews and implement their live eval adapters. Check instruction loading, local document and image access, script execution, workbook writing, staged session resume and structured event capture. Record the installed CLI version and actual authentication route. Reuse core rules and schemas; unsupported capabilities remain explicit. Pending Gemini/Grok work does not block an OpenAI experimental release.
3. Evaluate each implemented family/CLI combination against the same pre-frozen public scenarios, with three fresh chats per case for repeatability. Keep private-source authorization specific to its destination. Report model identity source, provider/account route, CLI version, prompt/package hash, failures, coverage, raw and workbook counts/denominators, unsupported values and opening behaviour. Unavailable workbook output is a capability limitation, not a passing workbook score. Correct blanks remain outside headline accuracy.

These steps preserve the PDF A/B/C routes, arbitrary user-requested fields and deterministic scoring. Model-specific prompt improvements need their own evidence; copying an OpenAI rule does not transfer its results. Existing Codex results remain valid only for their recorded scope and do not qualify Gemini or Grok. New recommendations, default routing and package promotion follow evaluation; this design decision alone changes none of them.

### CLI integration contract

Official documentation reviewed on 2026-10-11 establishes the tool choices, not successful integration with this repository:

| Family | Execution tool / adapter | Documented foundation | Repository status |
|---|---|---|---|
| `google` | Gemini CLI / `gemini-cli` | [Agent Skills](https://geminicli.com/docs/cli/using-agent-skills/) and [headless JSON/event output](https://geminicli.com/docs/cli/headless/) | Manual file-path preview built outside skill discovery directories; image reading and staged resume need local verification. |
| `xai` | Grok Build CLI / `grok-build` | [Terminal agent](https://docs.x.ai/build/overview) and [headless sessions with structured output](https://docs.x.ai/build/cli/headless-scripting) | Explicit-only preview built; discovery, image reading and staged resume need local verification. |
| `xai` | Cursor / `cursor` | [Agent Skills](https://cursor.com/docs/skills), [Rules](https://cursor.com/docs/rules), and [CLI parameters](https://cursor.com/docs/cli/reference/parameters), reviewed 2026-10-11 | Experimental explicit package. It reuses the xAI prompt and does not pass a model or effort override. Fresh-chat execution depends on a locally installed `agent` CLI. |
| `openai` | Codex CLI / `codex` | [Terminal commands, skills and scripted execution](https://learn.chatgpt.com/docs/codex/cli) | Existing package and staged evaluator; known limitations remain in reports. |

Keep delivery thin: the CLI loads the family prompt, reads the user's documents and writes the shared extraction envelope; the existing local processor creates the workbook and the common scorer evaluates it. Do not build separate processors per CLI or a new API agent loop for this phase. Local command execution does not make remote model inference offline.

Headless evaluation must preserve the current opening workflow: start a fresh session without document work, capture the policy question, wait for the appropriate reply, then resume that exact session. Save session IDs and tool events, distinguish private human replies from labelled public test fixtures, and never inject a private acknowledgement to make an unattended run pass. Missing resume or image-evidence support blocks that evaluation mode from being called valid; it does not justify bypassing the workflow. CLI-reported model identity remains reported, not independently verified, and a CLI name alone does not identify the selected family.

## Current implemented layout

```text
core/scripts/                 deterministic processing and validation
core/scripts/data/            standard columns, types and review reasons
core/references/              extraction contract, field meanings and custom format
skills/openai/                OpenAI prompt source and scoped policy reference
skills/google/                Google prompt and CLI policy reference (preview)
skills/xai/                   xAI prompt and CLI policy reference (preview)
skills/anthropic/             retained secondary Anthropic prompt and policy reference
adapters/<tool>/              packaging metadata, tool instructions and eval adapter
dist/<tool>/<package>/        generated self-contained installation packages
registry.toml                 recommendations, family versions and package mappings
eval/cases/                   original printed fixtures
eval/fixtures/                shared synthetic sources
eval/scenarios/               custom configurations and independent expected answers
eval/runner/                  preparation, execution and scoring
tests/                        deterministic regression tests
legacy/0.2.0/                 unchanged historical Claude packages
```

## Composition

Build copies shared scripts/references, one family's source and the selected adapter into a complete package. Family prompts control extraction behaviour; adapters control tool operations. Five combinations are buildable: Codex/OpenAI, Claude Code/Anthropic, Gemini CLI/Google, Grok Build/xAI, and Cursor/xAI. Gemini, Grok Build, and Cursor support preparation, not qualified live execution. `tools/check.py` rebuilds into scratch space and checks package drift, local reference links, README registry output and private workstation paths.

`registry.toml` distinguishes a recommended model from evaluation status. Current packages are experimental and explicit-only; empty new-family recommendations display as Pending evaluation. Buildable previews are registered without claiming live support. Gemini's file-path delivery deliberately stays outside discovery directories because a native manual-only integration has not been verified. Grok and Cursor use the documented `disable-model-invocation` field so discovery does not auto-apply them. Cursor installs under `.cursor/skills/` and does not pass `--model` or an effort flag. Unknown invocation formats and automatic file-path adapters are rejected by the builder. The skill neither switches models nor pauses for mismatches. Benchmark runners for other tools may select the maintainer's explicit `--model`; this is not a skill-level override. The Cursor adapter ignores that argument. Exact requested and runtime-reported identities are separate metadata, and unknown identity is never called verified.

## Runtime flow

At the first skill invocation in each new chat, ask exactly "Have you read the Readme about the data policy for your model?" and offer Yes plus "No, but I will read it before I upload any confidential data". A brief skill announcement may precede it. Any reply permits the task to continue; only silence waits. Record response received without inferring reading, a promise or legal consent. The state remains local to the chat, survives documented same-chat compaction and is not stored in custom.md. This 0.3.6 decision supersedes the affirmative-only gate. Provider/account scope is unchanged, and the response does not authorize new uploads. After the reply, ask about the user's purpose/columns only when needed, in finance-user language, and maintain the user's `custom.md`. Its Requested fields table supports arbitrary keys, display labels, field meanings, one/many observations and required flags. The existing Document buckets section continues to control standard sheet placement. Both settings files live outside the installed package.

A fresh run manifest enumerates selected files. Each input points to its extraction file within the run or records an unprocessed reason. The processor follows this list, never globbing old runs. Legacy `--extraction` remains available for deterministic tests and older callers, but has no input-coverage guarantee; new skills always use `--manifest`.

For PDFs, `reading_capabilities.py` checks the existing execution environment without provisioning dependencies. `pdf_routes.py` uses PDFium to prepare physical page images, text/positions and heuristic A/B/C route hints. Optional Tesseract OCR runs on B pages, or explicitly selected retry pages, only after executable/language/smoke checks. The caller supplies image-tool availability; this is not inferred from the model family. Keep raw `routes.json` separate from the agent's `reading-review.json` and extraction envelope. The script cannot certify the agent's visual checks. OCR failures preserve image fallback, file/page failures remain visible, and old evidence folders cannot be overwritten. Source PDFs remain unchanged.

The JSON envelope has a documents array. The parser validates its structure before processing and rejects malformed or duplicate documents. Standard `fields` have fixed meanings and reject unknown keys. User-defined facts use `custom_fields`, whose keys must exactly match the validated settings. Each observation distinguishes printed, absent and unclear and retains value, unit, context, pages and evidence. Repeated values remain separate. The parser validates evidence metadata, not whether the model actually saw truthful evidence.

Requested data gives a user-facing wide view; Requested values is the lossless observation view, with source document and evidence pages. Standard sheets keep the existing accounting-neutral checks. Unclear total values stay blank instead of being filled from balance due; unknown tax/discount/shipping cannot silently be zero in a passing arithmetic check. The explicit missing-total fallback is retained only for an absent total.

## Boundaries

Custom settings choose information, not safety rules. No guessed values, silent unit conversion or invented cross-document links. Shape classification cannot suppress requested facts. Document text is untrusted source data, not agent instructions. User settings and documents cannot authorise changes to installed scripts.

Processor exit 0 means processing succeeded; 2 means invalid input/configuration; 3 means a workbook was saved with unprocessed inputs. The PDF helper separately uses 0 for prepared evidence, 2 for configuration errors and 3 for partial/limited preparation. Neither establishes extraction accuracy. The helper inventories pages but the processor does not yet enforce the agent's reading-review ledger. Prompts require wholly unreadable pages to keep the input unprocessed, preserving partial extraction separately; field-level uncertainty remains in review notes.

## Remaining validation

The family packages and CLI eval adapters need live model evaluation. The native two-page invoice/certificate now has scan, incorrect-hidden-OCR and mixed-page variants, each with payment and energy settings and fixed expectations. Photos, handwriting and varied layouts still need approved fixtures. Local Tesseract integration is covered with mocks when no usable engine is found; this does not replace testing the installed engine. Recommendations and package status must not be promoted based on deterministic tests alone.

The approved unified entry that selects bundled family instructions remains a later implementation step. Independent Tesseract/model-vision readings followed by cross-checking are a second-iteration candidate. Neither capability is implied by the first PDF-routing implementation.
