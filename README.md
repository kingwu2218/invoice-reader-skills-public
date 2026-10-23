# invoice-reader-skills

This public repository begins with an independently reviewed source snapshot and a new Git history. Historical evaluation reports retain their original scope and artifact hashes; they are not fresh measurements of this snapshot. Private documents and run transcripts are not included.

Extract the information you need from invoices and supporting documents into an Excel workbook for review. Standard finance columns are available, but you can also ask for other printed facts, such as Energy Level of Coal on a lab certificate. Tell the agent what you need in ordinary language; it maintains `custom.md` for you.

## MVP: ChatGPT / OpenAI through Codex CLI

**An experimental invoice-extraction skill for Codex CLI, including use with ChatGPT sign-in.** The MVP focuses on this route. Ordinary ChatGPT browser/mobile skill installation is not implemented. Gemini and Grok are the next phase; their existing previews are not live-validated and are not required to use the MVP. Claude/Anthropic remains available as secondary support.

Start with **`invoice-reader-openai` 0.3.17**. Read the [data-policy guidance](#data-policy), follow [Install](#install), then describe the information you need. Your selected OpenAI model stays selected; the recommendation is metadata, not a model override.

Download the OpenAI package and checksum from the [0.3.17 experimental release](https://github.com/kingwu2218/invoice-reader-skills-public/releases/tag/v0.3.17). See the [release notes](docs/releases/0.3.17.md) for tested behaviour and known limitations.

The package includes custom extraction fields, PDF reading routes, source evidence, input coverage and Excel output. Version 0.3.17 maintains the prompt in [three authoring parts](docs/prompt-maintenance.md) and generates one complete installed entry. It retains the 0.3.16 shared PDF runtime. It remains experimental; fresh results are separate from historical 0.3.16 evidence. The v9 opening grader and extraction references remain locked. See [evaluation evidence](#existing-evaluation-evidence) for tested environments, model results and their limits.

Maintainers keep one prompt per provider family, shared processing in `core/`, tool operations in `adapters/`, and generated installation packages in `dist/`. See the [architecture and delivery sequence](docs/design.md#primary-targets-and-delivery-sequence) and the [next-phase CLI handoff](docs/cli-smoke-tests.md).

For agents working in a clone, [AGENTS.md](AGENTS.md) provides public workspace
guidance. Installed skills follow their own package instructions. Maintainer-only
workflow files stay local and ignored; see [publication review](docs/publication-review.md)
for contribution checks and optional local Git guards.

## Choose a package

**MVP: choose OpenAI / Codex below.** Gemini and Grok are next-phase previews; Anthropic is retained secondary support. “Not evaluated” in Last eval means no full qualifying evaluation; scoped results are linked below.

One prompt source is maintained per model family. Other models reuse it without a model switch or an additional model-mismatch confirmation. The policy-reading question applies to every model. Tool adapters provide installation and execution details. The packages below are currently explicit-only previews; invoke them by name.

<!-- sets:start -->
| Family | Tool | Package | Recommended model | Version | Status | Last eval |
|---|---|---|---|---|---|---|
| openai | Codex | `invoice-reader-openai` | `gpt-6.1-sol` | 0.3.17 | experimental | Not evaluated |
| anthropic | Claude Code | `invoice-reader-anthropic` | `claude-sonnet-5-5` | 0.3.14 | experimental | Not evaluated |
| google | Gemini CLI (manual file preview) | `invoice-reader-google` | Pending evaluation | 0.1.1 | experimental | Not evaluated |
| xai | Grok Build (unvalidated preview) | `invoice-reader-xai` | Pending evaluation | 0.1.2 | experimental | Not evaluated |
| xai | Cursor (experimental explicit skill) | `invoice-reader-xai-cursor` | Pending evaluation | 0.1.2 | experimental | Not evaluated |
<!-- sets:end -->

The OpenAI recommendation changed to [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) (`gpt-6.1-sol`) on 2026-10-08 after the owner reported weaker-than-expected Luna handwriting recognition in separate testing. This is a recommendation decision, not a measured Sol-over-Luna accuracy claim. A subsequent private rerun completed all four fixed scenarios with all 14 scenario document records present and 2 / 2 custom project values correct. It exposed both an omitted identifier and numeric/date normalization limitations, and does not establish better handwriting recognition. Broader evaluation remains pending; see the development log. The existing OpenAI prompt is shared with Luna and other OpenAI models; the skill never switches the user's model.

Gemini and Grok have buildable prompt/adapter previews with local preparation tests; live integration, staged evaluators and model recommendations remain pending. The OpenAI route reuses Codex; no separate ChatGPT browser adapter is planned for this phase. An experimental Cursor package reuses the same xAI prompt and stays explicit-only. A scoped 17–18 October 2026 comparison is in the evaluation guide; it is not a general accuracy claim. GitHub Copilot remains deferred. Do not assume a family package works in every application or tool.

## Install

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once. It runs the bundled Python scripts and their declared dependencies.

- **Codex:** copy `dist/codex/invoice-reader-openai/` into your personal `.agents/skills/` folder, or your project's `.agents/skills/`. Ask: "Use $invoice-reader-openai to read these documents."

<details>
<summary>Secondary and next-phase preview installation</summary>

- **Claude Code:** copy `dist/claude-code/invoice-reader-anthropic/` into your personal `.claude/skills/` folder. Start with `/invoice-reader-anthropic`.
- **Gemini CLI preview:** copy `dist/gemini-cli/invoice-reader-google/` to `.invoice-reader/packages/invoice-reader-google/` in your working folder. Explicitly ask Gemini to read `.invoice-reader/packages/invoice-reader-google/SKILL.md` and process your named documents. Keep it outside automatic skill-discovery directories; native explicit-only discovery is not validated.
- **Grok Build preview:** copy `dist/grok-build/invoice-reader-xai/` into `.grok/skills/` in your working folder and invoke `/invoice-reader-xai`. The generated skill disables model invocation. This documented installation route still needs a local smoke test before any accuracy claim.
- **Cursor experimental package:** copy `dist/cursor/invoice-reader-xai-cursor/` to `.cursor/skills/invoice-reader-xai-cursor/` in the document workspace. Invoke `/invoice-reader-xai-cursor`. For a multi-turn chat, start it as a Custom Mode with Alt+Enter on Windows or Option+Enter on macOS; a plain slash invocation attaches to one message. The package does not change the selected model or effort. It is explicit-only. The [17–18 October comparison](docs/evaluations/2026-10-18-cursor-xai-comparison.md) is a scoped result, not a general accuracy claim. Do not also install it under `.agents/skills/`, `.claude/skills/`, or `.codex/skills/`.

</details>

Copy the whole package, including scripts and references. `skills/` contains maintainer source and is not an installable package. Earlier Claude packages are preserved under `legacy/0.2.0/` for comparison.

For local PDF rendering, if an existing Python environment does not already have PDFium and Pillow, set them up explicitly in a new document working folder:

```text
uv venv .venv
uv pip install --python .venv "pypdfium2>=5.13,<6" "Pillow>=10.1"
```

Tell the agent to use `.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on macOS/Linux for PDF helpers. The workbook scripts run through `uv run` and declare their own dependencies. Setup can download packages; capability discovery itself does not install anything. Tesseract is optional. This is runtime setup; users do not need the repository's development dependencies.

The [0.3.17 verification](docs/evaluations/2026-10-13-openai-0.3.17-prompt-parts.md) passes **24 / 24** clean-install/processing checks with a fresh dependency cache and **326 / 326** local regression tests. PDF probing and preparation use the same runtime; the release ZIP preserves the evaluated package bytes. These deterministic checks are separate from the fresh model results below. The earlier [0.3.16 verification](docs/evaluations/2026-10-13-openai-0.3.16-release-readiness.md) remains unchanged. Version 0.3.17 is an experimental pre-release; it does not claim production accuracy.

## Use

For example: "Extract invoice numbers and payment due dates," or "Find the Energy Level of Coal for each sample in the attached certificates, keeping its unit."

The agent may briefly announce the skill, then asks **Have you read the Readme about the data policy for your model?** with two choices: **Yes, I have read it.** and **No, but I will read it before I upload any confidential data**. Codex may add one necessary line explaining the wait with a source link. Any reply allows work to continue; you do not have to answer Yes or confirm twice. Read [Data policy](#data-policy) before uploading confidential data. The question is asked once per chat, including with an existing `custom.md`; another batch does not repeat it. A new chat asks again.

After your reply, if requirements are missing or ambiguous the agent asks what you need in finance-user language. It creates or reuses `custom.md` in your working folder. You do not need to write field keys or JSON. A company profile is optional when company direction is not needed.

With custom fields the workbook starts with **Requested data**. **Requested values** preserves each repeated observation's printed value, unit, context, source page and evidence. The usual billing, reference, payment and other sheets remain available. Missing information stays blank; unclear information is flagged. The skill does not silently convert units or fix printed totals.

Every run has a new `invoice-reader-work/<run-id>/` folder and manifest. **Input coverage** lists processed and unprocessed files; partial output is identified explicitly. Review reasons tell you which entries need comparison with the original. This is extraction for review, not accounting, tax or audit advice.

## Existing evaluation evidence

The [23 October diverse-data benchmark](docs/evaluations/2026-10-23-openai-diverse.md)
adds three fresh Luna/high chats: a utility invoice, a partly obscured receipt,
and a new credit-note/proforma diagnostic. Configured fields score **31 / 31 raw**
and **36 / 36 workbook**, excluding one correct blank in each layer, with no
missing or extra scored rows. All three openings pass unchanged v9. The prompt
remains 0.3.17. These are single synthetic trials, not customer-document or
handwriting-stability evidence; the report records the next dataset priorities.

The [0.3.17 three-part prompt regression](docs/evaluations/2026-10-13-openai-0.3.17-prompt-parts.md) runs four fresh sessions with unchanged v9 and locked answers. Payment and certificate purposes score **104 / 104 raw**, **122 / 122 workbook** together; public digit boundaries score **13 / 13**, **15 / 15**. The known Fox page scores **5 / 5**, **7 / 7**, with owner-confirmed subsets **2 / 2**, **4 / 4**; both totals and Invoice classifications match. Correct blanks are excluded and private provisional fields remain separate. All four policy questions/options/pause checks pass; **3 / 4** openings pass automatic v9 format grading, with one payment explanation still requiring review. These are single executions of known sources, not a handwriting-stability or general accuracy claim.

The [0.3.16 difficult-document regression](docs/evaluations/2026-10-11-openai-0.3.16-difficult-regression.md) freezes references before three fresh chats, with package and v9 unchanged. The known Fox page retains the target amount and Cash Memo classification but misses the neighbouring total: **4 / 5 raw**, **6 / 7 workbook** (owner-confirmed subsets **1 / 2**, **3 / 4**). Public digit-boundary controls score **13 / 13 raw**, **15 / 15 workbook**; the conflicting-OCR certificate scores **25 / 25 workbook**, with raw scoring not configured. Correct blanks are excluded. All three exact policy questions/options/pause checks pass, but **0 / 3** openings pass automatic v9 format grading: explanation wording remains `requires_review`. This is one execution per known source, not an all-pass or handwriting-stability claim.

The [prospectively frozen v2 confirmation](docs/evaluations/2026-10-11-openai-0.3.16-varied-v2-confirmation.md) reruns the known public PDFs in two fresh 0.3.16 chats with corrected answers locked before calls. Payment scores **45 / 45 raw**, **55 / 55 workbook**; certificate quality scores **59 / 59 raw**, **67 / 67 workbook**. Totals are **104 / 104** and **122 / 122**, excluding **78 / 78** blanks. Unchanged v9 openings and workflows pass **2 / 2**; both runtime pairs match. **17 focused tests** pass. The prior failure and retrospective regrading remain intact; one new chat per purpose confirms these cases, not general accuracy or handwriting stability.

The [0.3.16 varied-use evaluation](docs/evaluations/2026-10-11-openai-0.3.16-varied-use.md) adds two fresh chats over new public PDFs: multiple files, two same-page invoices, mixed native/scanned pages and custom certificate measurements. Both workflows and unchanged v9 openings pass **2 / 2**. It exposed a reference error confusing the Other worksheet with `Lab certificate` document type. Original frozen scores remain **79 / 129 raw**, **93 / 151 workbook**; separately labelled retrospective corrected-reference scores are **104 / 104** and **122 / 122**, excluding **78 / 78** blanks. The full suite passed **307 tests**, followed by **11 / 11** focused tests after the erratum. These are two purpose trials, not stability evidence; the separately frozen confirmation above followed this erratum.

The [0.3.16 PDF runtime evaluation](docs/evaluations/2026-10-11-openai-0.3.16-pdf-runtime.md) reproduces the old 4.30 rendering failure and verifies the repair. All **298 local tests** pass, with **27 / 27** runtime checks across existing PDFium 4.30.0, 5.14.0 and managed uv environments. Installation-free discovery remains separate from explicit dependency setup; the same runtime entry handles probe, prepare and recovery. The unchanged v9 grader passes **3 / 3** new openings; initial extractions plus the scan follow-up score raw **65 / 65** and workbook **88 / 88**, excluding **68 / 57** correct blanks. All **4 / 4** phases use matching probe/preparation environments without alternate-renderer recovery. The v9 grader and extraction references are unchanged. These are known synthetic regression cases; other rebuilt family packages remain experimental without new provider-model evidence.

The [unchanged-v9 repeat](docs/evaluations/2026-10-11-openai-0.3.15-v9-repeat.md) adds three fresh 0.3.15 chats using identical grader/package/reference/harness hashes. Openings again pass **3 / 3**, giving **6 / 6** across the two frozen-v9 batches. Including the scan follow-up, the new batch again scores raw **65 / 65** and workbook **88 / 88**, excluding **68 / 57** correct blanks. All compared scored values agree across four initial payment chats, two energy chats and two scan follow-ups; settings and earlier outputs are preserved. Runtime probes encounter a local renderer incompatibility and the models recover without evaluator edits; the report retains this limitation. No prompt or grader change was made, and earlier evidence remains unchanged.

The [0.3.15 frozen v9 evaluation](docs/evaluations/2026-10-11-openai-0.3.15-v9-confirmation.md) accepts bounded `one reply` / `one response` wording while retaining source-path safety, extra-confirmation and Yes-only rejection. All **294 tests** and **738 authored grading cases** pass. Fresh openings pass **3 / 3** under both v9 and v8; none uses the new determiner variant. The previous known v8 batch scores **3 / 3** retrospectively, versus its original **2 / 3**, including the repaired `one reply` example. Initial extraction totals are raw **50 / 50** and workbook **67 / 67**, excluding **51 / 43** correct blanks. Including the same-session scan follow-up, totals are **65 / 65** and **88 / 88**, excluding **68 / 57** correct blanks; settings and earlier outputs are preserved. The prompt package remains 0.3.15, and earlier results are preserved.

The [0.3.15 frozen v8 evaluation](docs/evaluations/2026-10-11-openai-0.3.15-v8-confirmation.md) recognises `require this question and a reply` and `before I can begin/start`, retaining v7 source validation and extra-confirmation/Yes-only rejection. All **289 tests** pass. Both relative and slash-drive links pass **34 / 34** valid, **55 / 55** rejected and **204 / 204** appended-condition cases; new wording also passes **16 / 16** valid and **28 / 28** rejected path cases. Fresh openings pass **2 / 3**, equal to v7 on the same outputs; `one reply` remains reviewable. The previous known v7 batch scores **3 / 3** retrospectively, covering both requested variants. Neither variant occurs in the fresh outputs; full stability is not claimed. All initial extractions and the same-session scan follow-up complete: raw **65 / 65**, workbook **88 / 88**, excluding **68 / 57** correct blanks; settings and earlier outputs are preserved. The 0.3.15 prompt and earlier results remain unchanged.

The [0.3.15 frozen v7 evaluation](docs/evaluations/2026-10-11-openai-0.3.15-v7-confirmation.md) supports `/C:/...` Windows source links while preserving exact installed-source checks, extra-confirmation rejection and Yes-only rejection. All **269 tests** pass; native Windows path cases accept **16 / 16** valid spellings and reject **28 / 28** unsafe/unsupported paths. The 28 accepted, 43 rejected and 168 appended-requirement language cases pass with both relative and slash-drive links. Fresh opening acceptance is **1 / 3**, equal to v6 on the same outputs; all fresh links are recognised, while two new prose variants require review. The previous known v6 batch scores **3 / 3** retrospectively, exercising the alias fix. No fresh output uses the alias, and no stable full acceptance is claimed. All initial extractions and the same-session scan follow-up complete: raw **65 / 65**, workbook **88 / 88**, excluding **68 / 57** correct blanks; settings and earlier outputs are preserved. The 0.3.15 prompt and historical results remain unchanged.

The [0.3.15 frozen v6 evaluation](docs/evaluations/2026-10-11-openai-0.3.15-v6-confirmation.md) supports a complete explanation followed by its quoted waiting rule, retaining extra-confirmation and Yes-only rejection. All **252 local tests** pass; authored fixtures accept **28 / 28** valid forms and reject **43 / 43** invalid forms plus **168 / 168** appended-requirement variants. Fresh openings pass **2 / 3**, equal to v5 on the same outputs; the remaining referral concerns `/C:/...` source-link spelling. Rescoring the previous known v5 batch gives **3 / 3** retrospectively, which is development evidence rather than fresh confirmation. All initial extractions and the same-session scan follow-up complete: raw **65 / 65**, workbook **88 / 88**, excluding **68 / 57** correct blanks; settings and prior outputs are preserved. The 0.3.15 prompt and historical grades remain unchanged.

The [0.3.15 frozen v5 evaluation](docs/evaluations/2026-10-11-openai-0.3.15-v5-confirmation.md) recognises a quoted waiting rule followed by one application clause while retaining extra-confirmation and Yes-only rejection. Before execution, grading fixtures pass **20 / 20** acceptable forms, **31 / 31** rejected forms and **120 / 120** appended-requirement variants. The full suite passes **238 tests**, with **21 affected tests** rerun after the final grammar simplification. Fresh opening acceptance is **2 / 3**, equal to v4 on the same outputs; the remaining explanation reverses the clause order. V5 accepts **3 / 3** on the previous known batch when rescored retrospectively, which is development evidence rather than fresh confirmation. All three initial extractions and the same-session scan follow-up complete: raw **65 / 65**, workbook **88 / 88**, excluding **68 / 57** correct blanks; settings and prior outputs are preserved. The 0.3.15 prompt and original results remain unchanged.

The [0.3.15 frozen v4 evaluation](docs/evaluations/2026-10-11-openai-0.3.15-v4-confirmation.md) improves recognition of necessary waiting paraphrases while keeping extra-confirmation and Yes-only restrictions. Before the three fresh chats, grading fixtures pass **12 / 12** acceptable forms, **18 / 18** rejected forms and **48 / 48** appended-requirement variants; all **227 local tests** pass. Live opening acceptance is **1 / 3**, versus unchanged v3's **0 / 3** on the same outputs. Two new explanation structures still need review. Initial extraction is raw **50 / 50**, workbook **67 / 67**, excluding **51 / 43** correct blanks. Including the same-session scan follow-up, totals are raw **65 / 65** and workbook **88 / 88**, excluding **68 / 57** correct blanks; existing settings and outputs are preserved. V4 and its dependencies were frozen before execution; the package prompt and previous results were not changed.

The [0.3.15 prospective v3 confirmation](docs/evaluations/2026-10-11-openai-0.3.15-v3-confirmation.md) uses the unchanged package and the already approved grader, frozen before three fresh CLI chats. Initial extraction scores raw **50 / 50** and workbook **67 / 67**, excluding **51 / 43** correct blanks. Both payment trials have identical scored values. All three openings preserve the exact question/options and observed wait, but their source-linked explanations vary in wording: v3 reports **0 / 3 automatic passes, 3 / 3 requires_review**. This does not confirm the previous retrospective 3 / 3 result. Original grades remain visible, and the prompt/grader were not changed to fit this batch.

Its same-chat second scan batch also completes, preserving custom.md and the earlier workbook without another policy question. Across four batches, raw is **65 / 65** and workbook **88 / 88**, excluding **68 / 57** correct blanks. These repeated synthetic sources establish neither broad document diversity nor general handwriting accuracy.

The [0.3.15 first-use evaluation](docs/evaluations/2026-10-11-openai-0.3.15-first-use.md) repeats three fresh CLI chats and one same-chat second batch with a fixed short opening announcement. All complete, scoring raw **65 / 65** and workbook **88 / 88**, excluding **68 / 57** correct blanks. The remaining one-line explanations follow a requirement observed in the host's captured instructions. The owner then approved that format: supplementary `codex-opening-v3` checks pass **3 / 3**, while v2 remains **3 / 3 requires_review**. This is an explicitly retrospective format judgment, not an improved extraction score or a prospectively frozen confirmation test. Future plans freeze v3 before execution. Shared extraction/runtime and other families are unchanged.

The [0.3.14 first-use evaluation](docs/evaluations/2026-10-11-openai-0.3.14-first-use.md) tests three new document workspaces outside the repository, with no prefilled custom.md, profile or extraction. All three fresh CLI chats create their own settings, handle PDF setup and generate Excel; a second batch in chat 1 preserves its settings and earlier workbook. Four batches score raw **65 / 65** and workbook **88 / 88**, excluding **68 / 57** correct blanks respectively. Exact policy question/options and observed waiting pass **3 / 3**; additional opening text remains `requires_review` in all three. The versioned evaluator separates those outcomes and binds image evidence to actual tool returns. The prompt/package is unchanged. This is known synthetic content with two initial payment trials and one energy trial, not a general handwriting or full qualification result.

**Experimental: OpenAI 0.3.15, Anthropic 0.3.13, Google 0.1.0 and xAI 0.1.0 have not passed a full qualifying evaluation.** Recommendations are evaluation targets, not accuracy claims. Earlier results do not establish accuracy or onboarding behaviour for changed packages.

OpenAI **0.3.14** makes the opening question and both replies explicit in the entry, uses one response channel and waits before workspace access. Extraction guidance is unchanged from 0.3.13. The public repeated-chat evaluation is reported separately from the historical Fox results below; no private Fox rerun is implied.

The [0.3.14 public CLI evaluation](docs/evaluations/2026-10-11-openai-0.3.14-cli-public.md) completed **11 / 12** planned trials; one startup permission failure is retained without replacement. Valid results score workbook **219 / 219**, excluding **93** correct blanks. Raw checks on classification and digit-boundary cases score **53 / 53**, excluding **4** correct blanks; coal cases do not configure raw scores. The same OCR-layer PDF passes payment and energy purposes in three fresh chats each. All 11 started chats ask once and do not repeat after the reply, but strict opening format remains **10 invalid / 1 requires_review**. These known synthetic fixtures and 199 passing local tests do not establish general handwriting accuracy or a full workflow pass.

<details>
<summary>Earlier versions and evaluation history</summary>

OpenAI **0.3.13** adds a local visual check before accepting handwritten amounts or requested numeric measurements, even when the first reading seems clear. The view retains the label, complete token and nearby lines; the agent checks which strokes belong to digits and records the evidence. Genuine leading digits must be retained; unresolved tokens stay unclear and blank. This OpenAI-only prompt change includes no supplier, page-specific coordinates or expected values.

The [0.3.13 three direct fresh-chat Fox repeats](docs/evaluations/2026-10-11-openai-0.3.13-direct-fox-repeats.md), with no public examples first, read the owner-confirmed target Total correctly **3 / 3** in raw and Excel, and classified Cash Memo correctly **3 / 3**. All used local amount views and recorded boundary evidence. However, run 3 left the neighbouring Cash Memo Total unclear and blank. Strict scores are **raw 14 / 15**, **workbook 20 / 21**, excluding nine correct blanks per layer. Target reading improves within this small sample, but overall workbook accuracy is unchanged from the preceding repeats. The first chat repeated its opening policy question. All 190 current local tests pass; the package remains experimental and this is not general handwriting accuracy.

OpenAI **0.3.12** requires reading the shared document-type mapping before classifying each batch, including familiar titles. Payment status alone does not determine document type: a Cash Memo recording a sale remains an Invoice. The shared mapping and processor were unchanged in that release.

The earlier [0.3.12 three direct fresh-chat Fox repeats](docs/evaluations/2026-10-11-openai-0.3.12-direct-fox-repeats.md), with **no public examples first**, classified Cash Memo correctly **3 / 3**, but read the owner-confirmed target Total correctly only **2 / 3** in both raw and Excel. One run repeated the extra-leading-digit error and wrote it into the workbook. Strict scores total **raw 13 / 15**, **workbook 20 / 21**, excluding nine correct blanks per layer. All six document records remained present and all three covered requested values stayed blank. Those repeats used unchanged 0.3.12 and showed an unstable target reading. The 189 passing local tests did not override that model failure.

The [0.3.12 OpenAI evaluation](docs/evaluations/2026-10-11-openai-0.3.12-cash-memo.md) passed public classifications **3 / 3**, raw **9 / 9** and workbook **17 / 17**. On the reused Fox page, both documents are now Invoice and the owner-confirmed target Total remains correct in raw and Excel. Strict private scores are **raw 4 / 5**, **workbook 7 / 7**, excluding three correct blanks per layer. The sole raw difference is a source-supported currency prefix omitted by the frozen reference; the original score is retained. The obscured requested value stays blank. This is one execution per case, with the public controls preceding the private batch in one new chat, not general handwriting accuracy. That chat asked the policy question once and waited, but its automatic opening-format audit remains invalid. All **186 local tests** pass; both packages stay experimental.

Anthropic **0.3.13** tightens the opening in the Anthropic family prompt. Until you reply, the agent may only read the skill's own instructions: no folder listing, no shell commands and no workspace files. The two reply choices must be offered word for word. The [0.3.13 evaluation](docs/evaluations/2026-10-11-anthropic-0.3.13.md) found:

- **Public cases:** Sonnet 27 / 27 and Opus 26 / 27 valid (one dropped connection), all configured checks correct. No tools before the reply and verbatim choices in every chat, where Sonnet previously used tools in 14 / 27 chats.
- **Fox pages:** Sonnet raw 74 / 75 and workbook 81 / 81; Opus 73 / 75 and 80 / 81. Both had 15 / 15 documents and 6 / 6 unclear values kept blank, and both followed the Payer rule on every cheque run.

An account usage limit interrupted 98 executions, which are kept as failures and rerun in new chats. These are known fixtures and four reused pages, not general accuracy.

Version **0.3.11** makes two changes:

- **Waiting for the policy reply:** until you answer the policy question, the agent does not list folders or open any file, including custom.md, because file names can be confidential.
- **Payer on cheques:** when a cheque prints the drawer's name twice, Payer uses the account-holder line exactly as printed, and the other form is quoted in a note.

The [Anthropic 0.3.11 evaluation](docs/evaluations/2026-10-10-anthropic-0.3.11.md) ran Sonnet 5.5 and Opus 5.5 in three new chats per case:

- **Public cases:** 27 / 27 valid per model, all configured checks correct.
- **Fox pages (four owner-authorized, known):** Sonnet scored raw 74 / 75 and workbook 80 / 81; Opus scored 73 / 77 and 78 / 82, from one Cash memo misclassification. Both had 6 / 6 unclear values kept blank, no guessed values, and every cheque used the account-holder line.
- **Folder listing:** Sonnet still listed the folder before the reply in 19 / 39 chats; Opus did so in 0 / 39. This needs another prompt iteration.

The intermediate OpenAI 0.3.11 package was rebuilt but unevaluated; 0.3.12 inherits its shared-core changes.

Version **0.3.10** adds a bounded visual check for strokes beside amounts: inspect nearby rules and surrounding space before deciding whether a mark is a digit; keep unresolved values unclear. A public three-page raster fixture tests a nearby rule, a genuine leading digit and an obscured prefix. The [supplied-transcription matrix](docs/evaluations/2026-10-10-core-0.3.10-digit-boundary.md) detects 4 / 4 injected errors; 169 local tests pass. These validate scoring and processing, not model recognition. Earlier 0.3.9 results do not qualify this changed prompt.

The [0.3.10 OpenAI live evaluation](docs/evaluations/2026-10-10-openai-0.3.10-digit-boundary.md) passed **raw 13 / 13** and **workbook 15 / 15** configured nonblank checks on that three-page public fixture. All 3 / 3 invoice records were present; the obscured complete amount stayed unclear and blank. The automatic opening audit remains invalid because of extra explanation/combined instruction reads; a separate maintainer review accepted the observed wait before the scripted public reply. Requested model: `gpt-6.1-sol`; reported identity: Unknown. This single synthetic printed-image run does not establish general handwriting accuracy or a fix for the earlier private amount error. Both packages remain experimental.

The subsequent [0.3.10 private case-004 rerun](docs/evaluations/2026-10-10-openai-0.3.10-private-case-004.md) read the owner-confirmed target Total correctly in **both raw extraction and the workbook**. However, it classified the neighbouring Cash Memo as Receipt instead of Invoice. Strict scores are **raw 3 / 7** and **workbook 4 / 8**, excluding three correct blanks in each layer; classification creates missing/extra matches and increases the denominators. The single private attempt took about **28 minutes**. The new session also repeated its opening policy question three times. This is a narrow corrected reading with a classification regression, not an overall pass or evidence of reliable handwriting accuracy. The report preserves the separate legacy public-bootstrap reference defect and all original outputs.

The [first Anthropic 0.3.10 live evaluation](docs/evaluations/2026-10-10-anthropic-0.3.10-claude-code.md) ran the unchanged package on nine public cases in fresh Claude Code chats. Requested and reported model was `claude-opus-5-5` (the owner's selection, not the recommended Sonnet), as reported by the CLI rather than verified. With corrected evaluation permissions, **9 / 9 executions** were valid: raw **13 / 13**, workbook **199 / 199**, documents **19 / 19** and requested observations **39 / 39**, excluding correct blanks. That covers native, image-only, wrong-hidden-OCR and mixed coal PDFs for payment and energy, plus the digit-boundary fixture. There were no extra records or guessed blanks. The baseline batch scored 174 / 174 on 8 / 9 runs; one execution failed when harness permission rules denied its shell commands, and is kept as unscorable. Every chat asked the policy question once before document work; the reply was a labelled scripted fixture. Each case ran once per harness on known synthetic content, so this is not a general accuracy claim. The package stays experimental.

A [follow-up](docs/evaluations/2026-10-10-anthropic-0.3.10-repeats-and-fox.md) ran the recommended `claude-sonnet-5-5` and `claude-opus-5-5` in three new chats per case. Package and prompt were unchanged; the evaluation harness gained a recorded environment note about single-script commands. Public: 27 / 27 valid per model, with digit-boundary raw 39 / 39 and workbook 45 / 45 and identical values across repeats. Coal cases are now reported only as custom-field demonstrations; all 24 / 24 per model reproduced their requested fields. On the four owner-authorized Fox pages, a known-source regression with frozen owner-confirmed references:

- Opus scored raw 71 / 75 and workbook 77 / 81.
- Sonnet scored raw 68 / 75 and workbook 74 / 81.
- Both had 15 / 15 documents and 6 / 6 predeclared unclear values kept blank, with no guessed values.

Most differences are the account holder's name copied in the source's alternate casing. The owner then accepted that printed alternate. Rescoring the unchanged predictions against separately frozen v2 references gives Opus raw 74 / 75 and workbook 80 / 81, and Sonnet 75 / 75 and 81 / 81; the original strict scores remain the record. Earlier Sonnet attempts failed on harness permission bugs and are kept as failures. These are four reused pages, not a general handwriting accuracy claim.

Version 0.3.9 handles an ending `-` by the **individual amount's source**. Handwritten `360-` becomes positive `360` without asking. For a computer-generated amount, the skill asks whether it means positive or negative before conversion. If the origin is uncertain, it also keeps the text pending confirmation. Other work continues; unresolved amounts are flagged and excluded from arithmetic. Mixed printed/handwritten pages use per-field metadata and scoped replies. Raw/custom values stay unchanged. [Amount notation](core/references/amount-notation.md) explains the rule and why software-format examples cannot replace the user's reply.

The [completed private handwritten regression](docs/evaluations/2026-10-10-openai-0.3.9-handwritten-completion.md) covers **4 / 4 pages** and **5 / 5 expected document records**. Frozen-reference checks score **raw 23 / 25** and **workbook 25 / 27**, excluding correct blanks. The differences are a source-supported Payer capitalization alternate and an amount error now confirmed by the owner. The [scoped owner review](docs/evaluations/2026-10-10-openai-0.3.9-owner-adjudication.md) preserves the original scores and reports the updated review scope separately. The handwritten terminal-dash check passed **1 / 1**, and both predeclared unclear observations stayed blank (**2 / 2**, one owner-confirmed and one provisional). All 14 execution attempts and the [earlier partial report](docs/evaluations/2026-10-10-openai-0.3.9-handwritten-regression.md) remain visible. These are reused sources and selected fields, not overall handwriting accuracy. All **165 local tests passed**; the package remains experimental.

The [0.3.9 staged live eval](docs/evaluations/2026-10-09-openai-0.3.9-dash-clarification.md) passed raw 42 / 42 and workbook 72 / 72 after a documented scorer fix and separately frozen reference correction. It checks two computer-generated pages across three confirmation stages, including a handwriting-style font; it does not establish human-handwriting accuracy. All 152 regression tests passed. The 0.3.8 live results below remain historical. The [0.3.9 processor matrix](docs/evaluations/2026-10-09-core-0.3.9-amount-origins.md) passed 119 / 119 nonblank checks and 21 / 21 expected review flags; 42 correct blanks are excluded. These are supplied-transcription tests, not handwriting recognition.

The [0.3.8 live evaluation](docs/evaluations/2026-10-09-openai-0.3.8-default-dash.md) records both preliminary and final artifacts. Final-package public checks passed raw 25 / 25 and workbook 34 / 34, including Payee/Payer; a preliminary 11 / 12 party result remains visible because its legacy reference omitted a printed unit. The [processor matrix](docs/evaluations/2026-10-09-core-0.3.8-amount-dash.md) passed 68 / 68; all 139 regression tests passed. These known printed fixtures do not establish general handwriting accuracy or a verified model identity.

Version 0.3.7 explicitly reads both **Payee** (recipient) and **Payer** (drawer/account holder) on every cheque, even when your custom request focuses on another field. Missing names remain blank with a note; unreadable names are flagged. The bank, company profile or another invoice cannot supply a missing party. A **Cash Memo** recording a sale is classified as **Invoice**, with its printed title retained. **Billing documents** is the worksheet for invoices, credit notes and debit notes by default; the Document type column distinguishes them. Versioned payment-party scenarios now score these names explicitly; the v1 reference failure and corrected v2 run are reported separately.

Version 0.3.6 accepts any reply to the once-per-chat policy question. Offer **Yes, I have read it.** and **No, but I will read it before I upload any confidential data**. Either option, No, uncertainty or another answer lets the task continue without another confirmation. No response still means waiting. A brief skill announcement may come first. This records a response, not proof of reading or consent; historical evaluation scores retain their original criteria. That policy workflow is retained in 0.3.7.

The [0.3.5 opening and resume test](docs/evaluations/2026-10-08-openai-0.3.5-onboarding.md) passed manual opening review under A; the automatic checker referred the explanatory preface for inspection. After the owner supplied a real affirmative reply, two public image-only extraction purposes completed without repeating the question: raw 39 / 39 and workbook 46 / 46 configured checks, excluding correct blanks. All 128 regression tests passed. These two known public pages do not establish general recognition accuracy; actual model identity remains Unknown.

Historical version 0.3.4 handled readable amounts with an ambiguous ending dash: its default kept the original text and requested review. If you confirm whether that dash means a negative amount or simply ends a positive amount for the selected documents, the adapter can apply that convention to the batch. Converted standard amounts retain the original notation in review reasons; raw extraction and custom values stay unchanged. Mixed document conventions require separate batches. [Deterministic processor cases](eval/processor-cases/amount-dash-v1/README.md) test this contract without calling a model; they do not replace a new model evaluation.

The [0.3.4 processor evaluation](docs/evaluations/2026-10-08-core-0.3.4-amount-dash.md) passed 51 / 51 configured workbook checks across those three conventions; 108 unit/regression tests passed. This is conversion evidence from supplied synthetic strings, not a new handwriting accuracy result.

A targeted [0.3.4 live model evaluation](docs/evaluations/2026-10-08-openai-0.3.4-model.md) then completed three public PDF executions: raw 42 / 42, workbook 63 / 63, document records 6 / 6 and correct batch conventions 3 / 3. The same printed PDF was reused with unknown, positive and negative settings in one acknowledged conversation. These are limited format/workflow results, not handwriting accuracy or full qualification; the registry status remains experimental.

The evaluator now also supports raw invoice line items and statement transactions, with separate row coverage and exact-text checks. [Deterministic regression tests](docs/evaluations/2026-10-08-raw-lines-regression.md) verify detection of missing/duplicated rows, changed printed numbers and misplaced debit/credit values; 121 tests passed. This extends what future evaluations can measure. It is not a new model run, and earlier scores retain their original field coverage.

A subsequent [image-only workflow evaluation](docs/evaluations/2026-10-08-openai-0.3.4-scan-lines.md) added raw invoice-line checks: two runs with corrected, pre-frozen references scored raw 39 / 39, workbook 46 / 46 and documents 4 / 4. Two earlier runs exposed a reference mistake equating the Other sheet with the certificate's document type; those failing scores are retained. The source is known public content in a continued chat, and image attention is unverified, so this is not a scan-recognition accuracy claim. The complete test suite now passes 124 tests.

Historical version 0.3.3 asked once at the first skill invocation in every new chat: **Have you read the Readme about the data policy for your model?** It required an affirmative answer before document work; 0.3.6 supersedes that requirement.

A partial OpenAI 0.3.1 public evaluation completed on 2026-10-08: six executions, 12 / 12 expected document records, 36 / 36 configured raw checks and 91 / 92 workbook checks. One difference concerns currency display; first-response reminder timing and visual-inspection evidence remain unresolved. These are small synthetic cases, not handwriting accuracy. See the [results and limitations](docs/evaluations/2026-10-08-openai-0.3.1.md). The registry's Last eval denotes a completed qualifying evaluation; it remains unset for these experimental packages.

Version 0.3.2 clarifies that custom amount/measurement values keep their printed unit separately, with requested context kept separately too. The summary displays `context: value unit` when those parts exist. Two new `format-*-units-v1` scenarios explicitly score the parts and summary without changing the old answers. Codex eval can optionally attach every rendered page with hash-checked input records; this establishes CLI image inputs, not model attention or autonomous page-reading success.

An initial [0.3.2 image-assisted evaluation](docs/evaluations/2026-10-08-openai-0.3.2.md) completed three public runs: raw checks 20 / 20, workbook checks 50 / 50 and supplied pages 6 / 6. Each scenario ran once; reminder timing, autonomous visual inspection and handwriting remain unqualified.

A limited [0.3.3 conversation and handwriting evaluation](docs/evaluations/2026-10-08-openai-0.3.3-onboarding.md) completed after a real policy-reading reply: public raw 20 / 20 and workbook 25 / 25; four private handwritten pages raw 19 / 19, workbook 18 / 19, documents 5 / 5. Both predeclared unreadable values stayed unclear and blank (2 / 2). One amount-format conversion was flagged; the exact question was preceded by a skill announcement in both new-chat trials (0 / 2 literal-first-message passes). References are provisional and each case ran once in one shared chat. See the [accuracy matrix](docs/evaluations/2026-10-08-openai-0.3.3-onboarding.csv); these results do not qualify a default or change the frozen registry status.

</details>

## PDF routes and the planned unified entry point

**PDF routing helpers are implemented; full route evaluation is pending.** The unified entry and multi-family delivery below are future work, not OpenAI MVP requirements. A partial OpenAI 0.3.1 run produced matching values for an incorrect-hidden-text fixture, but visual inspection was not independently verifiable from its saved event stream. Generated packages include capability checks, per-page evidence preparation and shared reading instructions. The unified family-selecting entry remains planned; keep using the existing family package names and installation commands above.

### PDF reading: three routes, selected per page

| Route | Page content | Reading approach |
|---|---|---|
| A: native text | Usable text generated directly into the PDF | Extract text and positions; check the page image for layout and label/value associations. |
| B: image only | Scanned or photographed content without usable text | Render and read visually; rotate, zoom or crop as needed. OCR may assist. Leave unreadable values unclear. |
| C: image with OCR text | Scanned content with a recognition-generated text layer | Use OCR to locate candidates, then check requested values against the image. Selectable text is not proof of correctness. |

Route each page, and relevant regions when a page mixes text and images. A mixed PDF combines these routes rather than requiring a fourth extraction algorithm. If the page type or text layer is uncertain, add visual inspection. Shared recovery handles poor image quality, rotation and handwriting; cross-page tables and repeated samples retain their context. Identify separate documents and associate attachments only with printed evidence. Record encrypted, corrupt or unreadable inputs and continue with readable material.

Shared [PDF guidance](core/references/pdf-reading.md) defines route selection and evidence rules; adapters supply commands and native-reader fallbacks. Users describe their information needs in `custom.md`, without choosing a technical PDF route. Evaluate native, image-only, OCR (including incorrect hidden text) and mixed fixtures separately, reporting counts and denominators for extraction, coverage, unsupported values, unit/sample associations and source-page correctness. Alternate renderings of the same content test robustness, not independent document diversity.

`pdf_routes.py` writes a fresh evidence folder with `routes.json`, text/position candidates and page PNGs. Classification is heuristic: image-plus-text pages may be OCR or mixed content, and image regions on otherwise native pages still need reading. The agent inspects each page and records a separate reading review. Preparation never marks a page visually verified. Failed files/pages and OCR failures remain in the report; unreadable input is reflected in the extraction manifest. Optional recovery supports rotation, cropping and selected-page re-OCR without replacing source files or earlier evidence.

### Reading capabilities and second-iteration cross-checking

Select the execution method from **PDF type × available capabilities**. `reading_capabilities.py` reports the running Python, library imports and a PDF-render smoke test, then checks Tesseract's executable, version, required language data and synthetic OCR result. The adapter identifies an existing interpreter and declares whether it has image-viewing capability; Python cannot detect model vision. Python or a Python OCR wrapper alone does not establish that the OCR engine works. Reports distinguish usable, unavailable, failed and unknown/not accessible; a missing PATH entry does not prove the software is not installed. A configured executable path is supported. A cloud sandbox's capabilities do not describe the user's computer without a local connection.

For the first iteration, use native text when suitable; use local OCR as an optional aid for image pages and visual checks where available. Re-OCR only relevant problematic regions of an existing OCR layer. If an optional reader fails, continue with another available method and record any verification limitation. Capability discovery itself must not silently install software or download runtimes/language packs.

With an existing Python interpreter (replace `python` as needed):

```text
python core/scripts/reading_capabilities.py --vision unknown
python core/scripts/pdf_routes.py input.pdf --out invoice-reader-work/RUN/pdf-evidence --vision available
```

In installed packages the adapter resolves the corresponding `scripts/` paths. Use `--vision available` only when the agent has an image-viewing tool; `--tesseract PATH` and `--languages eng+chi_tra` select an existing OCR installation and required languages. `--ocr off` disables Tesseract calls. The preparation helper needs PDFium and Pillow; dependency setup is a separate explicit step. Do not run capability discovery through `uv run`, which can provision packages/runtimes. Native PDF reading remains a fallback if those Python dependencies are unavailable. OCR outputs assist reading and never establish field accuracy.

**Second-iteration candidate:** independent local OCR and model-vision readings, such as Tesseract plus GPT, followed by field-level cross-checking. Keep the first visual reading separate from OCR output to reduce anchoring; saving two readings in sequence is sufficient and does not require parallel agents. Match document, page, field and sample before comparing values and units. Agreement is not proof of correctness. For disagreements, revisit the source region and preserve both readings; leave unresolved conflicts flagged rather than averaging, silently picking a value or adjusting arithmetic. Do not switch the user's model to obtain GPT.

Compare direct vision, OCR-assisted vision and independent dual reading against pre-established answers. Report accuracy, missed/extra observations, disagreement detection, unresolved conflicts, time and model usage, including cases where both readers make the same mistake. This extension remains a proposal for the second iteration, not a shipped capability or a claim of improved accuracy.

### One entry point, with model-family selection

The intended installed entry is `invoice-reader`. It will read the selected family instructions on demand, with one registered skill entry per tool. Maintainers still keep one prompt source per family; the build will bundle the supported family resources, tool adapter and shared core into a self-contained package.

| Available information | Selection rule |
|---|---|
| Current-session model ID supplied by the tool | Map a recognised ID to its family. |
| User-specified family, without reliable session metadata | Use the user's selection. |
| Only a model's self-reported identity | Use a recognised family as a fallback; label the identity self-reported, never verified. |
| Unknown, conflicting or unsupported identity | Use the package's declared fallback family, briefly state the limitation and continue. |

Adapters must establish whether they can expose current-session model information; automatic detection is not guaranteed across tools. A configuration default, tool name or provider endpoint alone does not establish the active model's family. Record the selected family and selection source, keeping an unknown actual model unknown. Selecting instructions never switches or pins the model, and a different or unknown model never creates a confirmation gate.

Family selection determines prompt instructions; the tool adapter determines PDF access and script execution. Neither determines the user's actual data policy: README guidance retains its stated model/provider/account scope. The per-chat question applies regardless of family. The proposed package shape is:

```text
invoice-reader/
  SKILL.md                 # entry and family selection
  families/                # bundled supported family instructions
    google.md              # planned: Gemini
    xai.md                 # planned: Grok
    openai.md              # ChatGPT / OpenAI family
  references/
    tool.md                # this tool's adapter instructions
    pdf-reading.md         # shared PDF routes and recovery
  scripts/                 # shared processing helpers
```

This target shape is planned, not the current generated package layout. Only implemented combinations will be shipped; existing Anthropic packages remain available separately. Evaluation is still required before promoting an automatically invoked default. See the [development log](docs/development-log.md) for these decisions and their implementation status.

## Data policy

Each CLI package's guidance identifies its product/provider scope and review date, including the actual sign-in or API route. A CLI name does not establish the account's data handling, and API guidance cannot automatically be applied to subscription sign-in. Adding a package does not authorize uploading private fixtures to another service.

Checked 2026-10-11: [Gemini CLI terms and privacy](https://geminicli.com/docs/resources/tos-privacy/) distinguishes Google-account Code Assist, Gemini Developer API paid/unpaid services and Vertex AI routes. For Grok Build, consult the CLI section of the [official security FAQ](https://docs.x.ai/developers/faq/security) and [enterprise data lifecycle](https://docs.x.ai/build/enterprise). Retention and privacy controls depend on the account/settings. These links do not verify your configuration or promise ZDR. Google/xAI model recommendations remain pending.

The OpenAI package links the [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data), checked 2026-10-08: API data is not used for training by default unless you opt in, and storage depends on the feature/account. This does not establish a ChatGPT subscription's or a third-party tool's settings. The Anthropic package links the [Claude Code data usage policy](https://code.claude.com/docs/en/data-usage); training and retention depend on the provider/account. Users of a different model look up their own applicable policy. Do not assume a model name alone determines your account's data handling.

At the start of each new skill chat, the agent asks exactly: **Have you read the Readme about the data policy for your model?** One offered reply is **No, but I will read it before I upload any confidential data**. Any reply completes this reminder step and lets the original task continue, subject to your instructions. The agent does not require proof of reading, reinterpret No as Yes, or claim legal consent or verified account settings. It waits only if no reply has arrived. Response state stays in the current chat; `Confirmed by user: yes` in `custom.md` concerns requested fields only. The reminder does not authorize additional uploads or a different service.

Working extractions and generated workbooks remain in the user's workspace. Never commit real client documents to this repository.

## Development and evaluation

Use Python 3.11 or later. Install development dependencies in your chosen virtual environment:

```text
uv pip install -r requirements-dev.txt
python tools/build.py
python tools/check.py
python -m unittest discover -s tests
```

Prepare synthetic evaluation workspaces without calling a model:

```text
python eval/runner/run.py --package invoice-reader-openai --prepare-only --runs 1
```

Prepare all six new PDF-format/purpose scenarios without a model call:

```text
python eval/runner/run.py --package invoice-reader-openai --prepare-only --runs 1 --cases coal-scan-payment coal-scan-energy coal-ocr-payment coal-ocr-energy coal-mixed-payment coal-mixed-energy
```

These supplement the native `coal-payment` and `coal-energy` scenarios. The OCR fixture deliberately has wrong hidden numbers while the page image retains the expected values. Format variants share one content group and do not constitute independent business documents. Local Tesseract execution and live model extraction still need environment-specific evaluation; mocked OCR tests are not accuracy evidence.

A private real-document check subsequently opened/rendered 34 PDFs / 536 pages and exercised an existing Tesseract installation on selected pages. It exposed and fixed trailing-empty-column handling in OCR TSV. Four live scenarios on three PDFs then completed through Codex with `gpt-6-luna` requested; the CLI did not report an independently confirmed actual model ID. All 14 scenario document records were present and the two requested project values were correct. Standard-field mistakes included a missed/misread cheque identifier and an amount assigned to Total without the required label. One provisional reference value was disputed during review; original scores remain preserved separately from scores excluding that field. This small, agent-reviewed baseline does not qualify a default or establish general accuracy. Private documents, answers and detailed results remain excluded from the public corpus. See the development log for scope and limitations.

**Conversation evaluation:** Codex has a staged runner that saves the exact session ID and continues after a reply. The 0.3.6 contract accepts any answer; older recorded sessions retain their affirmative-only gate. Public negative-response fixtures are labelled as scripted, never as human consent. The original one-turn runner still rejects live launches. Claude Code has a staged session runner that executes `--prepare-only` workspaces in fresh persisted chats (see below). Other tools can use `--prepare-only` and an interactive session. No evaluator-written acknowledgement or pre-answer page attachment is added.

```text
python eval/runner/run.py --package invoice-reader-anthropic --prepare-only --runs 1 --python PYTHON --cases digit-boundary-v1 coal-payment
python eval/runner/claude_session.py run eval/runs/PREPARED_BATCH --cases digit-boundary-v1 coal-payment --model YOUR_SELECTED_MODEL_ID --provider "ACTUAL_ACCOUNT_ROUTE"
python eval/runner/claude_session.py report eval/runs/EXECUTION_BATCH
```

The Claude runner answers the policy question with a labelled public test fixture (`No, but I will read it before I upload any confidential data`), never a Yes, and never for private cases. It writes execution records to a separate batch, so prepared workspaces remain `prepared_only`.

```text
python eval/runner/conversation.py start --case format-payment-units-v1 --model MODEL_ID --provider "ACTUAL_PROVIDER_AND_ACCOUNT_ROUTE"
python eval/runner/conversation.py reply CONVERSATION_FOLDER --reply-file ACTUAL_HUMAN_REPLY.txt --origin "Where the user supplied this reply"
python eval/runner/conversation.py continue CONVERSATION_FOLDER --case format-project-units-v1
python eval/runner/conversation.py reset CONVERSATION_FOLDER
python eval/runner/conversation.py report CONVERSATION_FOLDER
```

The reply file contains the user's actual answer, not a generated test Yes. Negative/uncertain test replies, onboarding results and extraction metrics are separate. See [conversation and holdout evaluation](docs/evaluation.md). The commands below document the earlier one-turn extraction mode; use the staged runner for current live Codex evaluation:

```text
python eval/runner/run.py --package invoice-reader-openai --model MODEL_ID --provider "ACTUAL_PROVIDER_AND_ACCOUNT_ROUTE" --runs 3
python eval/runner/score.py eval/runs/BATCH_FOLDER
```

If a suitable Python installation already exists, append `--python "PATH_TO_PYTHON"`; the runner supplies that path to the model and records this setup assistance. Codex evaluation uses its supported automatic approval review mode with the workspace sandbox; logs stream to each run folder while execution is in progress.

For a small PDF case (up to 20 pages), append `--attach-page-images` to run an explicitly image-assisted Codex evaluation. The runner renders all pages, attaches them in order and saves source/page hashes plus the exact invocation. The matrix reports supplied-page counts separately from reading accuracy. Prepared-only runs never count as supplied; absent or changed required evidence fails the image-input audit. This mode is currently unsupported by the Claude Code eval adapter.

```text
python eval/runner/run.py --package invoice-reader-openai --model MODEL_ID --provider "ACTUAL_PROVIDER_AND_ACCOUNT_ROUTE" --runs 1 --cases format-payment-units-v1 format-project-units-v1 --attach-page-images
```

The scorer writes `score.json` and `accuracy-matrix.csv`: counts, denominators, field precision/recall, missing/extra rows and review outcomes. Correct blanks are counted separately and excluded from headline accuracy. Prepared-only workspaces are not valid model runs. See [evaluation design](docs/evaluation.md) and [architecture](docs/design.md).

The reusable prompt and evaluation are the deliverables; private client files are evidence for finding gaps, not templates to imitate. The `format-payment` and `format-project` scenarios use one invented PDF with two user purposes and separate **raw transcription** and **workbook** expectations. They test leading zeroes, cheque amount notation, spaced dates and an invoice amount without a Total label. They are printed-format fixtures, not handwriting benchmarks.

```text
python eval/runner/run.py --package invoice-reader-openai --prepare-only --runs 1 --cases format-payment format-project
```

For scenarios with `raw_tables`, the runner captures the single run manifest's extraction as `raw-extraction.json`, with its hash. The matrix adds `raw_*` counts and rates without replacing workbook scores. Missing, ambiguous or changed raw evidence is reported as unavailable, not zero accuracy. Older scenarios without raw expectations are `not_configured`. Source strings stay intact; deterministic normalisation happens only in workbook processing. The [partial 0.3.1 evaluation](docs/evaluations/2026-10-08-openai-0.3.1.md) exercised both layers; broader evaluation remains necessary.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
