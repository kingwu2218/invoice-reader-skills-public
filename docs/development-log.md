# Development log

Why the project is built the way it is: each decision, the options weighed, and the reason. Newest entries at the bottom. Facts about the platforms were checked against the official docs on the date given; see [research/platform-facts.md](research/platform-facts.md) for the sources.

---

## 2026-10-06

### Starting point

The project owner set the brief: open-source Agent Skills that let accountants read invoices with the AI coding agent they already use. One skill set per model version, a shared core written once, English invoices first, the host model reads the documents (no OCR engine, no API key), output is a spreadsheet, and every uncertain value is flagged rather than guessed. No confidence scores and no accuracy percentages.

### Can a skill know which model it runs on? Not with certainty

- **Question:** can a skill set detect, with 100% certainty, that it is running on the model it was tested on?
- **Finding:** no. Claude Code has no `$CLAUDE_MODEL` variable. Only the `SessionStart` hook may receive the model, and the docs say it is not always included. The practical source is the model ID in Claude Code's system prompt, which the agent reports itself. A company gateway or proxy can route a model name to a different model, and nothing inside the session can see that.
- **In the eval, certainty is possible:** a headless run (`claude -p --model <id>`) reports which model did the work, so the harness can reject runs on the wrong model.

### Never force a model on the user

- **Option considered:** SKILL.md can set `model:` to switch the model while the skill runs.
- **Rejected by the project owner.** Users choose their model for cost and access reasons. A skill set may check which model it is on and ask; it never switches. The switch would also have been unreliable: it lasts one turn only, and it is silently ignored when an organisation's allowlist excludes the model.
- Recorded in AGENTS.md.

### The README is how users choose; detection is only a fallback

- Users read the README and install the set that matches their model.
- **One default per harness, named `invoice-reader`,** starts automatically. It targets one model tier: Sonnet (Claude Code), Luna (Codex CLI), Flash (Gemini CLI).
- **The default checks the tier only, never the version number,** because the agent can misreport a version. A version difference within the tier does not stop the run; it is recorded in the workbook.
- **A default is a pointer** to a specific model-version set. It moves to a newer version only after that version passes the full eval. A tier model that fails the eval means no default for that harness.
- **Specific sets** (for example `invoice-reader-claude-opus-5-5`) set `disable-model-invocation: true`, so they run only when named. This also stops two installed sets competing for the same request.
- **An alias is not one model.** The docs show `sonnet` meaning Sonnet 5.5 on the Anthropic API but Sonnet 4.5 on Bedrock, Google Cloud and Foundry. Every set states the exact model ID and provider it was evaluated on.

### Licence: Apache-2.0, so pypdfium2 rather than PyMuPDF

PyMuPDF is AGPL-3.0 (or commercial), which would bind everyone who runs the scripts. pypdfium2 is Apache-2.0 or BSD-3-Clause and fits. openpyxl (MIT) writes the workbook.

### Users install one thing: uv

Windows has no Python, and the scripts need two packages. Asking accountants to install Python and then `pip install` packages is several error-prone steps. uv is one install; each script declares its own packages, and uv fetches Python and the packages on first run.

### Output is xlsx only, no CSV

Formula-injection protection in a CSV means prefixing values that start with `=`, `+`, `-` or `@`. That turns a credit note's `-125.00` into text Excel can't add up. In xlsx, amounts are real number cells, and only text cells need protection, using Excel's own leading-apostrophe marker.

### The company profile is an .xlsx file, not YAML

Accountants know Excel. Drop-down lists prevent typing mistakes, and dragging rows sets the column order. YAML's one advantage is readable diffs in git, but the profile lives on the user's machine and is never committed.

### Holdout documents stay outside the repo

Documents kept back for release testing must stay unseen while a set is tuned. Inside the repo, even when git-ignored, the tuning agent could read them; once public, they could end up in future models' training data. The runner finds them through an environment variable.

### Names: `invoice-reader-skills` and `invoice-reader-<harness>-<model>`

The early name prefix `ocr-skill-` was dropped: no OCR engine is involved, because the model reads the page. The Agent Skills spec requires a skill's name to match its folder, so the build renames both together when it ships a set as the default.

### Support window

The latest two versions of each model line are supported. After a core safety fix, supported sets get the full eval (three runs per document); frozen sets get one run per document. The question for a frozen set is only whether silent errors and invented values got worse, not whether it is consistent.

### Eval uses the developer's subscription for now

`--bare` gives the cleanest isolation, but it needs an API key and hides the skill list from the model, so it can't test automatic triggering. The eval therefore runs without `--bare` on a subscription login, and the harness refuses to start if a personal skill could shadow the set under test.

### The eval is started from the desktop app, but not run in it

The desktop app is fine as the control room: start the eval script, read the results, review. The test runs themselves must be separate headless `claude -p` processes, one fresh session per document:

1. **Exact model.** A subagent started from the desktop app accepts only an alias (`sonnet`), not `claude-sonnet-5-5`. When a new Sonnet ships, the same eval would quietly test a different model, and the comparison between frozen sets would be meaningless.
2. **Proof of the model.** A headless run reports which model produced every answer, so a run on the wrong model can be rejected. A desktop session or subagent leaves no such record, and a subagent falls back to another model when the requested one isn't available.
3. **Clean conditions.** A desktop session carries the developer's own setup: memory, installed skills, connectors, instruction files. Run inside the repo, it could even open the answer key. Each eval run gets an empty temporary folder holding only the skill, the document and a test profile.
4. **Same path as a real user.** An accountant triggers the skill in a main session. A subagent has a different system prompt and loads skills differently, so it would measure something else.
5. **Anyone can reperform it.** The results are published, so another contributor must get comparable numbers from the same command. A script does that; "ask Claude in my desktop app to start some subagents" doesn't. It is the same principle as an audit test another auditor can reperform.
6. **Scale.** About 120 sessions per set can't be driven by hand.

### Build plus drift check; frozen sets are snapshots

`tools/build.py` assembles each supported set from the core and its tuning. `tools/check.py` fails when a shipped set differs from what the build would produce, when the README table differs from the registry, when a set breaks the naming rules, or when a specific set can start by itself. Frozen sets aren't rebuilt, so non-safety core changes can't reach them by accident; changing one requires a recorded safety fix.

### Scripts enforce the safety rules instead of trusting the model

- A value the reading step marks as unclear is blanked by the script, even if the model also wrote a value.
- An unknown field name in the extraction file is refused, so a typo can't silently drop data.
- An arithmetic check missing an input says "Not checkable"; it never passes by default.
- Every review reason names the columns it covers, so the scorer can tell "wrong but flagged" from "wrong and silent".

### Small choices

- Data files use TOML, which Python reads without extra packages.
- The skill renders PDF pages itself: Claude Code's own reader needs poppler, which Windows users won't have, for PDFs over 10 pages, and it downscales large images.
- Test documents are generated from invented data (the town "Exampleton", `.example` e-mail addresses) with reproducible PDF output.

---

## 2026-10-07

### What Claude Code can do on a computer

- It runs as the user's Windows account, not as Administrator, and can do what that account can: read and write files, run commands, reach the network.
- What limits it is the permission mode. The working-folder boundary is a prompt, not a wall: an approved command can write anywhere the account can. Native Windows has no sandbox; that needs WSL 2.
- What it reads is sent to the model provider. On a personal Pro or Max plan, retention is 5 years if the "improve the model" setting is on and 30 days if it is off. Conversations, including document text, are also saved in plain text on the computer.
- **Consequences:**
  - The README now has a privacy and client-confidentiality section.
  - The eval only runs `claude -p` in folders it created: `-p` shows no "trust this folder" prompt, so a downloaded folder's hooks would run unasked.
  - The eval's tool allowlist names the exact skill scripts, not `uv run` in general, because that would let the agent run any Python it wrote.
  - Each run records the Claude Code version, because auto-updates could change it between runs.

### User needs come before compliance work

The project owner set the order: before compliance work, find out as much as possible about what users need. Recorded in AGENTS.md. Raised by the question of whether an accountant who can't use a command line can run the eval. The published eval is the maintainers' job; whether accountants want to test a set on their own invoices is an open question about their needs.

### Who runs the eval

The maintainers run the eval with the CLI and publish the results matrix. Users only download and use a skill set. A user who wants to check the matrix can install the CLI and rerun the same eval on the public test documents. Holdout documents can't be rerun, because they aren't published.

### No commits during a discussion

The project owner's rule, recorded in AGENTS.md: work done during a discussion is left uncommitted until the discussion ends and the owner approves the commit.

### Document title, balance due and receipts

Decisions by the project owner:
- **Document title** is always captured as printed (for example `TAX INVOICE / RECEIPT`), and its column can't be hidden. A document without a printed title is flagged.
- **Total and Balance due are both captured,** in separate columns. A balance due can include earlier balances or payments, so the arithmetic check uses Total. Only when no total is printed is the balance due checked instead, and a mismatch there is flagged, never corrected.
- **A "Tax invoice" title makes the document an Invoice.**
- **Receipts are extracted too,** not set aside.
- **Each company has its own policy** on how each kind of document is handled. How the company profile should express that is still open.

### Follow the printed label; a balance due stands in for a missing total

- On every document, receipts included, `total` is only an amount labelled as a total. Other amounts, such as "Amount received", are never treated as the total. The reading step follows what is printed and doesn't guess.
- When no total is printed, the balance due (or amount due) stands for the total. This is the project owner's rule, and the script applies it, not the model, so the reading step still copies only labelled values. The arithmetic check then compares the balance due with subtotal plus tax, and a mismatch is flagged, because a balance can include earlier balances or payments.

### Every document is extracted, sorted into buckets

This replaces the brief's "extract the invoice family, set the rest aside". The project owner's rule: every document is extracted, and the skill sorts it by type into a bucket, one sheet per bucket:

- **Billing documents:** invoice, debit note, credit note.
- **Reference documents:** receipt, proforma, quotation, purchase order, delivery note, statement of account.
- **Payments:** cheque, bank deposit slip.
- **Other:** everything else, and anything the skill is unsure about.

Each company handles document types differently, so the user can change the mapping:
- On the first run the skill shows the default mapping and asks whether it fits. If not, the user says what to change, and the agent updates `custom.md` and shows the result for confirmation.
- `custom.md` sits next to the company profile, one per company, never inside the skill folder: updating a skill replaces its whole folder, which would delete it.
- It can only move document types between buckets or add a type. It can't override the safety rules: a request such as "fill missing amounts with 0" is refused, with the reason given.
- The eval can't answer a question, so its test profile comes with the mapping already confirmed.
- The project owner chose `custom.md` over a sheet in the company profile. The trade-off: the script needs a fixed table layout in it that it can read reliably.

Built in slice 2, after slice 1 (one printed invoice) has completed its first eval.

### First eval smoke run: simple commands only

The first headless run read the invoice correctly but produced no workbook. The agent combined "create folder, write the JSON, run the script" into one shell command, which the eval's tool allowlist refused. The agent stopped and explained rather than working around the refusal, which is the behaviour we want. The skill now says to save files with the file-writing tool and to run each script as a single command on its own. This also helps real users: a short, single command is easier to read and approve.

The runner also strips the parent session's `CLAUDE*` and `ANTHROPIC*` environment variables. Without that, a run started from the desktop app would go through the app's own connection instead of being an independent session.

### First eval: one printed invoice, three runs

Set `invoice-reader-claude-sonnet-5-5` v0.1.0 on `claude-sonnet-5-5` (Anthropic API), Claude Code 2.1.286. Test document `printed-001`, three fresh headless sessions. These are results on this one test document, not an accuracy claim.

- **First batch:** 120 cells correct, 3 silent errors, 0 invented, 0 misses. Type, direction and the flag decision were right in all three runs, and no cell differed between runs.
- **All three silent errors were the same cell:** Tax rate. The invoice prints `VAT 20%`; the answer key said `20%`; the agent copied `VAT 20%`. The agent had followed our own field rule, whose example was `VAT 20%`, so the rule contradicted the key.
- **Not fixed by editing the answer key to match the output.** Changing the key to suit the result would hide exactly what the eval exists to find. The project owner decided the column's meaning instead: Tax rate holds the percentage only. VAT, GST and sales tax are treated in broadly the same way in the accounts, so they share one column and the tax's name is left out.
- **After the field rule was corrected:** 123 cells correct, 0 silent errors, 0 invented, 0 misses, 0 cells differing between runs.
- **Lesson:** a silent error can come from an inconsistent rule, not from the model. Every silent error is traced to its cause before anything changes.
- **Known limit of this eval environment:** the developer's 23 personal skills load in every run. They are unrelated to invoices, but a dedicated Claude Code configuration folder for the eval would make the environment cleaner.

### Slice 1 widened: no subtotal, amount due only, credit note

Three more invented printed documents: `printed-002` (no subtotal), `printed-003` (no total, only "Amount due") and `printed-004` (a credit note whose amounts are printed without a minus sign). Set v0.1.0 on `claude-sonnet-5-5`, Claude Code 2.1.286, three runs each: 285 cells correct, 0 misses, 0 silent errors, 0 invented. Type, direction and the flag decision were right in all nine runs, and no cell differed between runs. These are results on these three test documents only.

### Slice 2 built: buckets and custom.md

Core 0.2.0 and set v0.2.0 add the buckets, `custom.md`, the Payments and Other sheets, statement lines, and a fifth case: `printed-005`, a receipt expected on Reference documents. The answer key gained an "Expected bucket" column, and the scorer checks it.

### The eval shares the subscription's usage limit

The first full run of slice 2 (five cases, three runs each) produced no valid runs. The account's session limit had been reached, and every run got Claude Code's own message ("You've hit your session limit") instead of a model answer. The runner rightly marked them invalid, because the answers didn't come from the pinned model. Two lessons:
- The eval and the developer's own Claude sessions draw on the same subscription limit. A full eval can stop the developer's work, and the developer's work can stop an eval.
- The runner now stops the batch at the first run that hits the limit, instead of spending the remaining runs on the same message.

### Invoice No. on every invoice-shaped sheet

Credit notes and receipts usually name the invoice they relate to, and accountants match them on that number. The project owner chose the column name **Invoice No.**, not "Related document number": a receipt row with an Invoice No. is self-explanatory to an accountant, and "related document" isn't.
- On a credit note, debit note, receipt or similar, Invoice No. holds the invoice number the document names.
- On an invoice, the script copies the invoice's own document number into Invoice No. (the owner's choice), so every sheet can be matched or looked up on one column.
- The answer key gained the column; existing rows got their values from the case definitions, and nothing already in the key changed.

### The repository starts private

The GitHub repository `invoice-reader-skills` is created private. It becomes public once the Claude Code version is finished.

### Slice 2 eval: five documents, three runs each

Set `invoice-reader-claude-sonnet-5-5` v0.2.0 (core 0.2.0) on `claude-sonnet-5-5` (Anthropic API), Claude Code 2.1.286. Cases `printed-001` to `printed-005`, three fresh sessions each, all 15 valid. 525 cells correct, 0 misses, 0 wrong but flagged, 0 silent errors, 0 invented. Document type, direction, bucket and the flag decision were right in all 15 runs, and no cell differed between runs. These are results on these five printed test documents only; scans, photos, handwriting, multi-document files, AR documents and payments are still to be tested. The registry's last eval date is set from this run.

### Open

- Install the CLI for the eval with WinGet (no auto-update, stable for comparisons) or the native installer (auto-updates).
- How the company profile sets each company's policy per document type.

---

## 2026-10-08

### Architecture direction: one prompt set per model family, with tool adapters

The project owner chose to maintain one main prompt set per model family, with one recommended model for each family. A separate maintained set for every tool and model version would create more maintenance than the project needs.

"OpenAI" means OpenAI models generally, not only the ChatGPT product. Use consistent model-family directory names: `openai`, `anthropic` (Claude), and `google` (Gemini). Keep the model family separate from the tool running it, such as Codex, Claude Code, Cursor or GitHub Copilot.

Decisions:

- **One maintained prompt set per family.** Each family can have its own prompt structure, workflow wording and reference layout. Do not force every family through one shared prompt template with only a small tuning section.
- **One recommended model per family.** Tune and run the main evaluation against that model. The owner's example is an OpenAI set recommended for Luna 6 that can also be tried with Sol 6.1. These examples do not establish evaluated compatibility or a final model recommendation.
- **Other models reuse the same prompt set.** A different model or a new model version does not automatically get its own maintained directory. Avoid accumulating model-specific branches inside the prompt. Keep earlier skill versions in Git tags/releases rather than maintaining a permanent prompt fork for every model version.
- **Recommendation is not a model override.** Users choose their model. The skill must not switch or pin it, and a self-reported model identity must not be described as verified.
- **Separate recommendation from evidence.** The README should distinguish the recommended model, other models tested with the same prompt, and untested models. Record exact evaluated model IDs and providers; do not imply equal results across models.
- **Share deterministic behaviour.** Data contracts, field meanings, parsing, arithmetic checks, review-reason definitions and workbook output belong in the common core. Family-specific prompts must produce data that conforms to the same contract.
- **Adapt to tools without duplicating the whole prompt.** Adapters handle installation format, resource paths, tool-specific operations and evaluation launch. Add small tool-specific instructions only when testing shows they are needed. Supported family/tool combinations must be established by tests, not assumed.
- **Keep installation self-contained.** Build outputs include the selected family prompt, the relevant tool adaptation and the required core resources. Users should not have to install the core separately.

### Intended repository layout (planned, not yet migrated)

```text
core/                         # shared contracts, rules, scripts and data
skills/                       # maintained prompt source, organised by family
  openai/
    SKILL.md
    references/
  anthropic/
    SKILL.md
    references/
  google/
    SKILL.md
    references/
adapters/<tool>/              # packaging, tool operations and eval launch
dist/<tool>/                  # generated, self-contained installation packages
eval/
  cases/
  answer-key.xlsx
  runner/
  scorer/
  results/<family>/           # results identify the actual model, provider and tool
tests/                        # core, build and eval tests
tools/                        # build and consistency checks
docs/
registry.toml                 # family versions, recommendations and eval references
```

For example, Cursor with an OpenAI model uses the OpenAI prompt plus the Cursor adapter; Cursor with a Claude model uses the Anthropic prompt plus the same tool adapter. This is a composition rule, not a claim that either combination is already supported. Create family and adapter directories when support is implemented, not as empty placeholders.

In the intended layout, `skills/` becomes maintained source and generated installable content moves to `dist/`. Today, `skills/` is generated output; that remains true until the migration is implemented. The registry remains the central home for version and recommendation metadata rather than duplicating it in each source folder.

This direction supersedes the earlier plan to maintain a set per specific model version. Implementation must reconcile `AGENTS.md`, `docs/design.md`, the registry, build/check tools, evaluation tooling and installation instructions with it. The exact package naming/default selection for tools that can run several model families, and whether a non-recommended model should prompt for confirmation, remain to be settled. This entry records the architecture decision only; it does not migrate the repository or change runtime model checks.

### OpenAI prompt: policy reminder, user-defined extraction and evaluation

The project owner subsequently settled the model-confirmation question: **continue with the user's model without pausing for confirmation**. Do not switch models. Record a model identity only when available, identify self-reported information as such, and leave unknown information unknown. This replaces the earlier planned confirmation gate; the existing runtime instructions still need updating during implementation.

The agreed user flow is:

1. **Give a brief data-policy reminder in the initial response.** Cover the project's recommended model and identify the account/provider context to which the cited policy applies. If the user uses a different model, tell them to look up its applicable policy themselves. Do not describe the recommended model's policy as applying to their actual setup. Include an official source and the policy reference date; do not invent policy details. The reminder is informational: no consent question, acknowledgement requirement or task pause, and no mandatory policy-search step for the skill.
2. **Understand what the user needs from the documents.** Use language familiar to finance users: ask what they want to do with the information, which details they need, or whether there is an existing spreadsheet layout to follow. Do not require JSON, schema terminology or programming knowledge. Reuse requirements already given instead of asking again.
3. **Create or reuse `custom.md` to express those needs.** Its role expands beyond document-to-sheet buckets to the requested fields and their meanings. Existing settings should be reusable; changed needs can update them. The field list must be flexible rather than limited to the standard invoice columns.
4. **Extract, check and deliver for those requirements.** Apply the common rules on evidence, missing and unclear values, arithmetic and review reasons. Keep source-file and page references and identify unprocessed inputs. Correct extraction mistakes from the source; never change printed values merely to make a check pass.

The owner supplied a real example: a user wanted the **Energy Level of Coal from a lab certificate within the invoice material**. This must be possible without adding a hard-coded coal field to every installation. Invoice number, dates and totals are useful defaults, not an exhaustive list of allowable information. Document classification must not prevent extraction of requested information from an in-scope certificate or section.

Custom field definitions need enough meaning to identify the requested information, including relevant printed labels and units. If the request could refer to several values, resolve that ambiguity in plain language rather than guessing a technical meaning. Preserve the evidence and distinguish missing information from unreadable information. Flexibility in the requested fields does not permit invented values, unsupported associations between documents, or silently calculated replacements for printed values.

Implementation must extend the current fixed-field processor and workbook output to accept validated user-defined fields. A prompt or `custom.md` change alone cannot provide this capability: the current processor rejects unknown field names. The exact representation of custom fields and repeated values remains a design task.

### Agreed test and accuracy-matrix direction

The first OpenAI baseline should test missing documents, guessed values and whether the agent changes data to make checks pass, alongside compliance with user-defined extraction requirements. Combine deterministic script tests with model-driven evaluations; passing script tests alone does not establish extraction accuracy.

- Evaluate document coverage, missing/extra/duplicate documents, field correctness, recall of printed requested values, unsupported filled values, silent errors, review-flag behaviour and adherence to `custom.md`.
- Publish counts and denominators. Do not let large numbers of correctly empty cells inflate the headline accuracy; distinguish those from successful extraction of printed values.
- Identify the model, provider, tool, skill version, case category and custom configuration behind each result. Results on the evaluated cases do not establish accuracy on arbitrary user documents.
- Test the same invoice with different user purposes, different custom configurations and separately defined expected answers. Establish the answers before evaluating the output; do not change them to fit the result.
- Include the coal-certificate use case as an evaluation scenario for fields outside the normal invoice schema, using invented or otherwise approved test material. No real user documents were supplied in this discussion.
- Start with a clear baseline and add targeted examples in response to observed failures, rather than accumulating speculative prompt rules.

These are agreed requirements for the new prompt and supporting implementation. No new prompt package, schema migration or evaluation results are delivered by this log entry.

### First implementation of the family architecture and custom extraction

Implemented after the owner authorised proceeding:

- Moved shared scripts and references out of `core/skill/`. Added independently maintained `skills/openai/` and `skills/anthropic/` prompts, Codex and Claude Code adapters, and generated self-contained packages under `dist/`.
- Updated AGENTS.md, registry, README, build/check tools and design documentation. The OpenAI recommendation is `gpt-6-luna` as the initial evaluation target. Both 0.3.0 packages are explicitly invoked experimental previews; neither claims a completed model evaluation.
- Added the non-blocking policy reminder and finance-language requirements workflow. OpenAI API policy wording links the official data-controls page checked on 2026-10-08 and explicitly limits its scope; it does not assert subscription or third-party account settings.
- Extended `custom.md` with requested field meanings, one/many cardinality and required flags. Added Requested data and Requested values sheets, preserving arbitrary printed facts, units, contexts, evidence and page references. The standard document sheets remain available.
- Added extraction-envelope validation, duplicate checks, evidence-page containment and fresh run manifests. Partial inputs remain visible in Input coverage and produce exit code 3. Fixed unclear totals being filled from balance due and unknown arithmetic components being treated as zero in a passing check.
- Added a synthetic invoice/certificate PDF and payment/coal-energy scenarios with independent expectations. Rendered and visually inspected both PDF pages. The fixture includes repeated samples, an absent measurement, an arithmetic mismatch and instruction-like document text.
- Reworked eval preparation/execution around tool adapters. Each run copies its expectations outside the model workspace and records artifact/dataset hashes. The scorer emits counts and denominators in an accuracy matrix, separates correct blanks, checks missing/extra rows and preserves invalid runs.
- Preserved the original Claude 0.2.0 installation packages unchanged under `legacy/0.2.0/`; they are not rebuilt. The initial deletion approach was rejected by automatic approval review, so the packages were moved intact instead.

Validation: 56 local unit/regression tests passed, generated-package drift/link checks passed, both family prompt sources and the Codex package passed skill-creator's quick validator, and the PDF-render helper was exercised. The Codex validator rejects Claude's native `disable-model-invocation` field; the Claude package's invocation metadata is checked by repository build tests instead. Prepared seven isolated eval workspaces (the five original printed cases plus both custom scenarios) without calling a model. **No new LLM extraction accuracy has been measured.** Live model eval, additional scan/photo/handwriting fixtures and stronger isolation from personal CLI configuration remain necessary before promoting a supported default.

### Decision: three PDF reading routes with page-level dispatch

The owner approved distinguishing PDF reading approaches inside the skill. **This is an accepted design; this entry and the README update do not implement the dispatcher or new evaluation fixtures.** Existing rendering support is a foundation, not completed route detection.

- **Route A — native text:** extract usable text and positions, with visual checks for reading order, table structure and label/value associations. Text availability alone does not establish correct extraction.
- **Route B — image only:** render and read scanned or photographed pages visually. Rotate, zoom or crop when useful; OCR is optional assistance. Preserve unclear values when the image cannot support a reading.
- **Route C — image with OCR text:** use the text layer to locate candidate information and verify requested values against the page image. A readable image takes precedence over incorrect OCR; an unreadable image does not justify guessing from an unverified text layer.
- **Dispatch per page, or per relevant region.** One PDF can contain all three kinds; one page can combine native text and embedded images. Mixed documents use the existing routes, not a fourth independent algorithm. Type detection can be uncertain, in which case inspect visually rather than claim certainty.
- **Share recovery and document assembly.** Blur, rotation, handwriting, complex/cross-page tables and repeated samples are shared handling concerns. Keep document boundaries and sample identities, and require printed evidence to link a certificate to an invoice. Record encrypted, corrupt or unreadable files/pages and continue with the readable inputs.
- **Separate user needs from reading mechanics.** Shared skill references define routing and evidence rules. Tool adapters own available readers, rendering/OCR commands and capability limitations. `custom.md` describes requested information; finance users do not choose the technical route.
- **Evaluate by route.** Add native-text, image-only, OCR and mixed fixtures, including OCR text that contradicts a clear image. Report counts and denominators for field accuracy, omissions, unsupported values, unit/sample associations and source-page correctness. Preserve the two-purpose custom-field scenarios. Rendering the same content in several formats tests robustness but must not be counted as independent document diversity.

The coal-certificate example remains an example of arbitrary requested information, not a hard-coded feature: preserve each printed sample's own value, unit, context and physical PDF page reference without averaging, converting or merging observations.

### Decision: one skill entry that selects model-family instructions

The owner approved a thin `invoice-reader` entry that reads model-family instructions on demand. **Pending implementation and adapter verification.** The current `invoice-reader-openai` and `invoice-reader-anthropic` preview installation commands remain valid until the new package is built and released.

Selection rules, in order:

1. Use current-session model information explicitly supplied by the tool and map recognised model IDs to families.
2. When reliable session information is unavailable, use a family the user has already specified.
3. Otherwise, a recognised model self-report may serve as a fallback, explicitly labelled self-reported rather than verified.
4. If information is unavailable, conflicting or unsupported, use the package's declared fallback family, briefly disclose the limitation and continue. Do not pause for model confirmation or invent an actual model identity.

Each adapter must establish whether current-session information is accessible. Reading a configuration default alone is insufficient because runtime settings may override it. A tool name or provider endpoint is not a model-family identity. Keep selected family, selection source and reported model identity separate in run records; leave unknown actual identities unknown. Do not treat invoice content as routing instructions.

The intended generated package has one registered `SKILL.md` entry, bundled `families/openai.md` and `families/anthropic.md` where supported, shared references including `pdf-reading.md`, the tool's `references/tool.md`, and processing scripts. Family files are resources read on demand, not competing automatically triggered skills. Maintain the existing independent sources under `skills/<family>/`; build the installation package without introducing maintained per-model copies. Bundle the resources required for supported combinations so installation remains self-contained.

This refines the earlier selected-family package design: users will choose a tool package and its entry can select a bundled family. Family selection controls prompt instructions; adapter selection controls tools and execution. Neither switches or pins the user's model. Unknown/non-recommended models continue without a gate, and model detection does not establish account-specific data policy. The brief recommendation-policy reminder keeps its stated provider/account scope.

Verify routing with known IDs, explicit user choices, self-reports, unknown/conflicting metadata and unavailable family resources, alongside adapter-specific evidence of runtime model access. Supported combinations and an automatically invoked default still require evaluation. This documentation update adds no runtime detection, new PDF routes or model accuracy results.

### Refinement: available OCR capabilities and a second-iteration dual-reading candidate

The owner accepted selecting the reading method by **PDF type × available capabilities**, and asked to consider independent Tesseract plus GPT reading and cross-checking for the second iteration. Keep the three PDF categories; local OCR is an execution capability, not another document category. This entry records the design only.

The planned adapter capability check discovers Python and relevant libraries, PDF rendering, OCR executables and required language data, and whether the current model/tool can inspect page images. Discover executable paths (including explicitly configured paths), check versions and run a bounded synthetic smoke test. A Python installation or wrapper import alone does not establish usable OCR. Record usable, unavailable, failed and unknown/not accessible separately. Not finding Tesseract on PATH does not prove absence from the machine; sandbox results only describe the execution environment. Do not silently install software or download runtimes/language data while claiming merely to detect capabilities.

First-iteration OCR is optional assistance: retain native text where suitable, use local OCR for image content when available, and selectively re-read problematic existing OCR regions. Fall back to other available readers on an optional tool failure, retain unresolved values as unclear, and disclose when visual verification is unavailable. The current `check_setup.py` checks Python and openpyxl only; broader capability detection remains to be implemented.

For the second-iteration candidate, obtain one local OCR reading and one model-vision reading of the same material. Capture the initial visual reading without showing the OCR result, then cross-check document/page/field/sample identity, values and units. These are separate readings, not a requirement for parallel agents; independence is procedural, not a guarantee of independent errors. GPT is an example when the chosen model supports it, not a forced model switch.

Retain both readings and source evidence. Agreement does not establish ground truth. Reinspect disagreement regions and flag unresolved conflicts without averaging, silently choosing a candidate or changing printed numbers to pass checks. Compare direct vision, OCR-assisted vision and independent dual reading using fixed expected answers, including shared-error and disagreement cases. Report counts/denominators, conflict outcomes, elapsed time and model usage before claiming an accuracy or cost benefit. No dual-reading workflow or new evaluation results are implemented by this documentation update.

### First PDF-routing implementation

Implemented after the owner requested starting the PDF routes and keeping the decisions in README and this log:

- Added `reading_capabilities.py`, runnable with an existing Python interpreter without provisioning packages. It records the current interpreter/library state, tests synthetic PDF rendering, resolves a configured Tesseract path or PATH command, checks version/language data and runs a bounded synthetic OCR smoke test. Model vision is caller-declared, not guessed by Python. Missing commands do not prove absence elsewhere on the computer; cloud execution remains distinct from a user's local machine.
- Added `pdf_routes.py` with per-page A/B/C heuristic classification, text and position candidates, image-region hints, page PNGs, source hashes and a persistent `routes.json`. Mixed pages retain region-reading requirements. Hidden text or large images suggest C without claiming certainty about PDF provenance. Scripts prepare evidence; visual verification remains pending until the agent actually inspects it.
- Added optional Tesseract TSV reading on B pages, preserving word positions and confidence without treating confidence as accuracy. Selected pages can be explicitly re-OCRed; C pages do not automatically undergo redundant OCR. `--ocr off` makes no Tesseract calls. Missing/failed OCR falls back to available vision; lack of image-reading capability is explicit. File/page failures preserve later-input processing and partial status.
- Added shared `pdf-reading.md` and linked it from both family prompts and both tool adapters. It separates raw preparation from the agent's companion reading review, requires per-page/region attention and retains existing evidence/non-guessing rules. A wholly unreadable page keeps that input unprocessed in the extraction manifest; readable partial extraction is saved separately for recovery. The processor does not yet enforce the companion review ledger automatically.
- Extended rendering recovery with bounded DPI, rotation and crop options. Source PDFs and earlier evidence files remain unchanged. Native PDF readers remain an adapter fallback if the current Python environment lacks PDF dependencies. Dependency installation is an explicit setup activity, not hidden in discovery.
- Added three synthetic format fixtures: scan, incorrect hidden OCR and mixed native/scan pages. Each has payment and energy scenarios, adding six fixed-answer cases. The hidden OCR layer deliberately changes `105.00` to `100.00` and `6,200` to `8,200`; visible images and expected values retain the originals. Format variants share one content group and do not count as independent document diversity. Rendered the fixtures and visually inspected the distinct page images; identical rendered pages were also checked by file hash.
- Updated README, architecture, evaluation guidance and changelog, rebuilt both generated packages, and recorded the eval content group alongside format category. Existing model recommendations remain experimental. The unified family-selecting entry remains planned; independent dual-reader cross-checking remains a second-iteration candidate.

Validation: **73 unit/regression tests passed**, including 17 new PDF/capability tests. Coverage includes route/page inventory, missing language data, OCR smoke failure/timeout, absent/failed OCR fallback, wrong hidden text, locked/corrupt files, per-page rendering failure, missing vision, selected-page re-OCR, rotation/crop and preservation of earlier evidence. Generated-package drift/link checks and `git diff --check` passed. Both family prompt sources and the Codex package passed skill-creator validation; Claude invocation metadata remains checked by repository tests. Prepared six new isolated OpenAI eval workspaces without invoking a model.

**Limits:** Tesseract was not found through the current PATH lookup; its real recognition was not exercised. OCR subprocess paths were tested with controlled mocks. No live model extraction accuracy has been measured for these changes. Route classification is heuristic, the reading-review ledger is agent-authored, and photos/handwriting/varied layouts still need fixtures and evaluation. No commit or push was made.

### Private real-document testing: local routes and Tesseract

The owner supplied company PDFs for testing. Kept all source copies, extracted text, rendered pages, private references and run configurations in Git-ignored evaluation storage; no private document or identifying source path was added to the public corpus.

- Inventoried 34 PDFs / 536 pages. All opened and rendered successfully; candidate routes were A 13, B 515 and C 8. This measures preparation coverage, not extraction accuracy or confirmed PDF provenance. Source hashes remained unchanged for all 34 files.
- Found an existing Tesseract installation outside PATH via its standard installation location. Version 5.5.0.20241111, English and Traditional Chinese data, and the synthetic smoke test worked. This corrects the earlier limitation: PATH lookup had not found the engine; it had not proved the engine absent.
- Exercised actual local OCR on representative pages, including explicit-path OCR-assisted preparation of 3 PDFs / 8 pages and rotation recovery. All 8 pages prepared; the 3 B pages completed OCR, while 5 A/C pages retained their existing text candidates. Also tested three standalone OCR reads. These are execution results, not a word/field accuracy score.
- Real Tesseract TSV exposed a command-output bug: `strip()` removed the final empty text column's trailing tab, causing a parser failure. Preserve trailing spaces/tabs by removing only newline characters, validate required TSV columns and retain explicit image fallback on malformed data. Added two generic regression tests without private content, rebuilt both packages, and passed all 75 tests plus drift/link checks.
- Prepared four private model scenarios from three source PDFs: mixed payment, the same document with custom project fields, OCR-like content, and rotated scans. Clear-field references were established before any tested-model output and kept outside model workspaces. References are agent-reviewed and provisional, not owner-verified gold; ambiguous values are excluded from exact-value scoring.

Live model evaluation did not complete. The first CLI launch failed on sandbox access to its normal local state database. Automatic approval review rejected the subsequent execution request because sending company PDFs to OpenAI through the current Codex ChatGPT login requires explicit destination/account approval. No alternative upload or service was used. Model accuracy remains undefined, with the four prepared scenarios awaiting that approval. No commit or push was made.

### Approved private baseline: four live scenarios completed

The owner subsequently explicitly approved the specified three PDFs / eight unique pages for four evaluations through OpenAI using the current Codex ChatGPT login. All four scenarios completed and produced workbooks. Requested model: `gpt-6-luna`; actual model remains Unknown because the CLI events did not identify it. Tool: Codex CLI 0.162.0-alpha.2. Frozen package hash: `54ce15065aa33adab92cad7a1eec3886c467d6092d7108e4cb7aac54a777032f`. No prompt changes were made between these runs.

- Resolved the non-interactive CLI execution failure using its supported automatic approval review mode with workspace-write sandbox and existing execution rules retained. Earlier failed attempts remain recorded; they are not extraction scores. No bypass flags were used.
- Document coverage was 14 / 14 scenario records, with no extras (10 unique documents; one four-document PDF was evaluated for two purposes). Custom project information was correct for 2 / 2 printed values, with source-page/evidence metadata present; 2 / 2 absent observations were correctly blank and excluded from accuracy.
- Provisional standard-field scores against the original frozen references were mixed-payment 8 / 11, mixed-project 8 / 10, OCR-payment 7 / 7 and scan-payment 8 / 8. Correct blanks are excluded; unexpected filled values count against the denominator. These cover only enumerated clear fields, not entire workbooks.
- Reinspection found a disputed digit in one pre-run reference identifier. Original expected files and scores were preserved. Excluding that same disputed field in both affected scenarios gives 8 / 10 and 8 / 9 respectively; the other two scores are unchanged. This post-run reference issue needs independent adjudication, not silent answer-key editing. All references remain agent-reviewed and provisional, not owner-approved gold.
- Observed failures include a missed cheque identifier, an extra leading zero in another run, and a line amount assigned to Total despite the predeclared independent-label rule. The same PDF's standard-field behavior differed by requested purpose. Prioritise synthetic regression cases for label association, identifier preservation and targeted re-reading before revising prompts.
- Ambiguous crossed-out/handwritten amounts were excluded from exact-value scoring. Consequently this baseline does not establish reliable preservation of disputed numbers. Review precision/recall, full evidence correctness, independent dual OCR/vision reading, repeatability and wider document diversity remain unmeasured. No recommendation was promoted to a default.

All 34 source-file hashes and all four copied inputs/packages remained unchanged. Private workbooks, logs, references, field comparisons, usage counters and the accuracy matrix are saved only in ignored evaluation storage. The final workbook was selected from the processor's last saved-output message, preserving earlier outputs from the same run. Readable workbook/field checks completed; the earlier 75-test result remains the validation for the unchanged package. README and this log contain anonymous aggregate findings only. No commit or push was made.

### 2026-10-08 — OpenAI recommendation changed from Luna to Sol

The owner reported weaker-than-expected Luna handwriting recognition in separate testing and requested Sol as the recommended OpenAI model. Set the exact recommendation to `gpt-6.1-sol`, consistent with the previously discussed Sol 6.1 target and the [official model ID](https://developers.openai.com/api/docs/models/gpt-6.1-sol) checked on this date.

Updated registry metadata, the README and the generated package. Keep one shared OpenAI prompt; this change neither pins nor switches the runtime model. Other OpenAI models, including Luna, continue without a confirmation gate. The provider/account-scoped policy reference still obtains the recommended model from package metadata.

The owner's observation is external feedback, not a controlled comparison in this repository. Preserve all historical Luna run records, frozen packages, references and scores under their original model request and artifact hashes. Sol remains experimental with no recorded evaluation date; do not transfer Luna results to Sol or claim better handwriting accuracy before measuring it. Follow-up evaluation should include handwritten digits, leading zeroes, summary-label association, targeted re-reading and the same-document/two-purpose cases. No live Sol evaluation was run for this recommendation change. No commit or push was made.

### 2026-10-08 — Sol private rerun, partial completion

After the owner requested rerunning the same company invoices and reiterated approval, three of four scenarios completed with `gpt-6.1-sol` requested through the current Codex ChatGPT login to OpenAI. The CLI actual model remains Unknown. Source PDFs, prompts, custom settings and frozen references match the Luna baseline; only package recommendation metadata differs (Sol artifact hash `5e748c5a80570f206076c6b8b173d3f59c02ef0520c8c2da94478d8b390eeb34`). Each model has one run per completed scenario with implicit reasoning defaults, so this is not an equal-compute comparison.

Using the unchanged scorer and excluding the same disputed reference: mixed-project scored 6 / 9 versus Luna's 8 / 9; OCR-payment 6 / 7 versus 7 / 7; scan-payment 8 / 8 for both. All 10 expected document records in the completed scenarios were present. Custom project values were 2 / 2 correct, with 2 / 2 correctly absent observations counted separately. Three scored failures concern normalization: two cheque amounts retain a trailing slash and a correctly read date uses spaces, formats the processor does not normalize. One undisputed cheque identifier was omitted. Do not describe all workbook score differences as handwriting recognition errors or infer general model superiority.

Automatic execution review still rejected mixed-payment on destination-consent grounds after allowing the other scenarios; a destination-specific approval question is pending. It remains unexecuted and unscored, not a failed extraction. Private artifacts, integrity checks, comparisons and detailed scores remain in ignored storage. No prompt or processor changes were made during this comparison, no default was promoted, and no commit or push was made.

### 2026-10-08 — Sol rerun completed after explicit destination approval

The owner explicitly approved sending the remaining same company PDF through the current Codex ChatGPT account to OpenAI for the Sol Eval. Automatic review allowed the pending mixed-payment run; it completed in 233.8 seconds. The three completed scenarios were not rerun. All four runs requested `gpt-6.1-sol`, with actual model still Unknown in CLI metadata.

Final provisional workbook scores, excluding correct blanks and the same disputed reference: mixed-payment 7 / 9, mixed-project 6 / 9, OCR-payment 6 / 7 and scan-payment 8 / 8. Luna's corresponding scores remain 8 / 10, 8 / 9, 7 / 7 and 8 / 8. The mixed-payment denominator differs because Luna incorrectly filled an otherwise blank Total, which adds an error opportunity; Sol correctly left it blank. Sol also correctly extracted the undisputed cheque identifier in mixed-payment, though it omitted that identifier in mixed-project.

Across Sol's four scenarios, all 14 expected document records were present with no extras; custom printed values were 2 / 2 correct, with 2 / 2 correctly absent observations counted separately. Four scored amount failures across the two mixed scenarios retain a printed trailing slash, and one date failure retains spaces between the correctly read date parts. These are processor/output normalization limitations, not evidence that those digits were misread. One other scored field was omitted. Keep the fixed workbook scores unchanged and distinguish raw reading from usable numeric/date output in follow-up evaluation. These small single-run samples do not establish general handwriting superiority or qualify an automatic default.

Integrity checks confirmed unchanged source PDFs, copied inputs, prompts, custom settings, frozen references and evaluated packages. Final workbooks, comparison matrix, detailed results and execution/approval records remain private and Git-ignored. README and this log now reflect four completed scenarios. No prompt/processor changes, commits or pushes were made for the rerun.

### 2026-10-08 — Reusable prompts and two-layer evaluation, 0.3.1

The owner reaffirmed that the ultimate deliverables are reusable prompts and evaluation, not a company-specific invoice parser. Applied the observed failure classes to shared instructions, bounded normalisation and public synthetic cases; no private content or identifying layout was copied into public fixtures.

- Shared payment guidance now explicitly preserves leading zeroes, separates serial/account groups, uses existing bounded recovery for uncertain groups, and copies amount/date notation without rewriting the source strings to satisfy processing. Both family packages receive the common guidance, maintaining one prompt per family.
- The processor normalises a single terminal slash only in a Cheque's amount field. Internal slashes, quantities and invoice totals retain the existing unreadable handling. Spaced numeric dates use the existing calendar and ambiguity checks; ambiguous day/month order is not guessed. Original JSON and custom requested values remain source text.
- Added a reusable raw transcription scorer beside the workbook scorer. Capture comes from one manifest and is hash-checked; missing/ambiguous/modified artifacts are unavailable evidence. Standard and custom values can be evaluated without numeric/date normalisation concealing transcription changes. Existing workbook metrics remain separate and older references remain unchanged.
- Added one invented two-page printed PDF and two purposes, payment and project information. References include raw and workbook answers, an absent custom value, leading-zero identifier, terminal amount stroke, spaced date and a line amount with no summary label. Both rendered pages were visually inspected. This is formatting evidence, not a synthetic substitute for real handwriting evaluation.
- Updated both family packages to 0.3.1 and retained experimental status. Historical Luna/Sol private runs keep their frozen 0.3.0 package hashes and scores. The new sources require fresh LLM evaluation; deterministic checks cannot establish improved prompt accuracy. Broader held-out layouts and real handwriting references remain necessary.

Validation: 82 unit/regression tests passed, including both purposes through raw scoring and workbook processing, source-string preservation, leading-zero errors, missing/extra documents, ambiguous dates, unsafe slash forms, multiple manifests and missing/changed raw artifacts. Both packages rebuilt and passed drift/link checks; `git diff --check` passed. Prepared two new isolated OpenAI scenarios without a model call. No new live model accuracy is claimed.

No commit or push was made.

### 2026-10-08 — OpenAI 0.3.1 public live evaluation

At the owner's request to take the next step without committing, ran six public-fixture executions through the current Codex ChatGPT login to OpenAI: two each for `format-payment` and `format-project`, plus one each for `coal-payment` and `coal-ocr-energy`. Requested model was `gpt-6.1-sol`; CLI-reported identity remains Unknown. The frozen package hash was `883993c6faa76f6dd644060ef5215ec8fb64fafac54d4719d374b3d38bac0e8a`. Existing Python was supplied as recorded setup assistance. No company documents were used and no extraction prompt, processor or expected answer was changed during the batch.

All six executions produced a valid workbook; all package/source/custom/dataset integrity checks passed. Document coverage was 12 / 12 scenario records with no extras. Configured raw checks matched 36 / 36 across the four format runs. Original workbook scores were 10 / 10 and 9 / 10 for payment, 13 / 13 twice for project, 21 / 21 for coal payment and 25 / 25 for OCR energy. Correct blanks remain excluded. These selected checks include metadata, not only financial values; two content groups and repeated purposes are not independent layout diversity.

The one frozen-score difference is `8,750/ HKD` versus `8,750/` in the payment summary. Source HKD was preserved as a separate custom unit and the existing formatter appended it; the raw amount itself matched. The pre-run answer did not specify that unit and the raw scorer did not check it. Recorded this as a display/reference-contract gap without deleting the scorer's original error or changing the reference. Future versioned cases must explicitly score value, unit, context and summary display.

Behavioural review found the policy reminder in the second response in all six runs, failing the literal first-response rule. Route reports and companion ledgers cover A/C pages, but the preserved event streams do not independently establish image inspection; matching the wrong-hidden-text fixture is output evidence, not a verified visual-workflow pass. Route B, new Tesseract recognition, dual OCR, handwritten/held-out layouts and general accuracy remain untested in this batch. No default was promoted.

The evaluation runner now accepts an existing `--python`, saves the prompt/initial metadata before launch, streams logs and records elapsed time/CLI usage. The Codex adapter uses the supported automatic approval review mode with workspace sandbox retained. Added a telemetry regression ensuring completion/usage do not invent model identity and a subsequent failure remains a failure. Validation for this follow-up: 18 targeted build/adapter/scorer/raw tests passed, generated-package checks and `git diff --check` passed. Earlier 82-test validation remains the deterministic evidence for the unchanged 0.3.1 package.

Added the [public report](evaluations/2026-10-08-openai-0.3.1.md) and machine-readable counts/hashes; updated README and evaluation guidance. Full local logs/workbooks remain in ignored run storage. No commit or push was made.

### 2026-10-08 — Unit/context contract and auditable image inputs, 0.3.2

Implemented the next agreed step without committing. Clarified the shared extraction contract: preserve numeric notation in value, explicitly associated printed currency/unit separately, and requested printed context separately. Documented the existing summary composition rather than changing processor behaviour. Added two separately frozen `format-*-units-v1` scenarios, reusing the invented PDF for payment-with-currency/context and project-text-only purposes. Both raw and workbook expectations now enumerate units and context. Historical scenarios, private references and 0.3.1 scores remain unchanged. Rebuilt both experimental family packages as 0.3.2; entry prompts and recommended models are unchanged.

Added optional Codex `--attach-page-images` evaluation. The runner renders all pages of a small PDF, saves hashes/page order/archival images and exact invocation, and supplies the images through supported CLI arguments. Stdin is closed so inherited pipe content cannot augment the recorded prompt. The scorer independently checks those artifacts and distinguishes supplied, prepared-only, unavailable and not-captured states, with separate page counts/denominators. It does not treat an agent's checked ledger as proof, or claim attention/server-side delivery from an attachment. This is explicitly harness-assisted evaluation; autonomous visual inspection remains unverified. Claude Code's adapter rejects this unsupported eval mode rather than simulating support.

Three live runs requested `gpt-6.1-sol` through the current Codex ChatGPT login to OpenAI, using only public fixtures and supplied Python. CLI identity remains Unknown; package hash `f1ad8618b2244a60bf040dc6f12e984e4d1df66b6bc2f98bd76865186814e68d`. Payment-units scored raw 10 / 10 and workbook 12 / 12; project-units raw 10 / 10 and workbook 13 / 13; OCR-energy workbook 25 / 25 (raw not configured). All 6 / 6 document records and 6 / 6 supplied page inputs matched; all package/input/custom/dataset integrity checks passed. Each scenario ran once. Output matches in the OCR case do not isolate visual reading ability, particularly because examples in the references overlap the public corpus. No accuracy comparison against the differently configured historical runs is claimed.

The reminder still appears in the second response in all three runs. Timing was not fixed here. Handwriting, held-out layouts, route B and dual OCR remain follow-up work. Added the [0.3.2 report](evaluations/2026-10-08-openai-0.3.2.md), machine-readable counts/receipts, README usage and evaluation documentation. Validation: 91 tests passed, including eight new unit/context and image-provenance tests; generated-package drift/link checks passed. No default promotion, commit or push was made.

### 2026-10-08 — Owner replaces the reminder with a per-chat question, 0.3.3

The owner explicitly requested asking **Have you read the Readme about the data policy for your model?** in every new chat before starting work. This supersedes the earlier decision to remind without pausing. Both family entries now ask the exact English question and wait for an affirmative answer before document reading, rendering/OCR, setup, custom.md creation or extraction. A no/uncertain answer directs the user to README guidance; silence does not acknowledge it. After acknowledgement the original task continues, and another batch in the same chat does not ask again.

Added shared chat-state rules: acknowledgement is conversation-local, retained through documented same-chat compaction, never persisted in custom.md/profile/memory and never inherited by another chat. Confirmed extraction fields do not confirm reading the policy. Model recommendations remain metadata; the same question applies to all models with no extra model-mismatch gate. Reading acknowledgement does not claim acceptance of legal terms or verify account settings.

Updated AGENTS.md, both scoped policy references, README and architecture/evaluation guidance; rebuilt both experimental packages as 0.3.3. Existing historical reports and scores are untouched. The one-turn eval runner cannot obtain the required real user answer, so live launches are temporarily rejected before preparation/model invocation, including image attachments. Prepare-only remains supported for interactive follow-up; no synthetic acknowledgement or automatic bypass was added. A two-turn evaluation harness and live onboarding validation remain pending. No commit or push was made.

Validation: six targeted build/adapter/runner tests passed, generated-package drift/link checks and `git diff --check` passed. The new runner test verifies rejection before preparation or model calls for both families, with and without image attachments. Prepared one new OpenAI workspace without a model call; this is not a live behavioural pass.

The Codex package passed skill-creator validation. That generic validator rejects Claude Code's existing `disable-model-invocation` frontmatter key; the repository's adapter/build tests validate that tool-specific metadata, which remains unchanged.

### 2026-10-08 — Staged conversation eval and holdout infrastructure

The owner authorised the three follow-up areas: onboarding behaviour, extraction after acknowledgement, and handwritten holdouts. Added a Codex conversation runner with persistent exact session IDs and explicit start/reply/negative/continue/reset/report operations. It never uses the most recent session as a fallback, sends no initial page images and cannot obtain acknowledgement from an empty response, custom.md, or a scripted affirmative. The real reply must be provided verbatim with its provenance. Test state is bound to the evaluated conversation and is not a global skill acknowledgement file. Original one-turn live launches remain rejected and direct maintainers to this staged runner.

Separate onboarding traces from extraction scores: waiting has no field accuracy denominator; successful extraction after a real answer uses the existing raw/workbook scorer. Each extraction checks package and dataset integrity. A second batch has isolated files while resuming the same conversation. A reset opens a new session without transferring the acknowledged state. Added holdout source-exclusion/freeze verification and separate unclear-value abstention metrics; modified references, reused baseline sources and a changed package are rejected. Public documentation describes the boundaries and manual trace review.

Three live public turns (start, scripted no, scripted uncertain) completed in the same `gpt-6.1-sol`-requested session through the current Codex ChatGPT login. Actual identity remains Unknown. All three file snapshots were unchanged; both negative cases waited. A manual trace review of the negative turn found only reads of installed skill policy guidance. The first assistant message was a skill-use announcement, so strict first-message wording scored 0 / 1 despite asking the question and pausing before observable document work. No changes to the 0.3.3 package were made. See the [partial onboarding report](evaluations/2026-10-08-openai-0.3.3-onboarding.md).

Presented the exact question to the owner and await the real acknowledgement. Affirmative-resume, second-batch and reset live validation remain pending; no answer was invented. Three new private source candidates were selected from the prior inventory, excluding earlier baseline sources, but page review, answer freezing and handwritten model evaluation have not started. They remain under ignored storage. Validation: 102 unit/regression tests passed, generated-package drift/link checks and `git diff --check` passed. No commit or push was made.


### 2026-10-08 — Complete the three staged-eval follow-ups

The owner supplied the real policy-reading acknowledgement, which was relayed verbatim to the existing evaluated session. The original public extraction resumed; another custom purpose and four handwritten batches continued in that same session without repeating the question (5 / 5 continuations). A separate new chat over the public workspace asked again and waited. Both new-chat trials announced skill use before the exact question, so literal-first-message compliance remains 0 / 2. No/uncertain waits passed 2 / 2; four pre-acknowledgement turns left files unchanged, with policy-only shell reads manually reviewed. Silence remains no model call; live compaction remains untested.

Completed two public scenarios: raw 20 / 20, workbook 25 / 25, documents 4 / 4. Prepared four new private source-page holdouts, excluding all previous model-evaluation sources, with provisional visually reviewed references frozen before execution and pixel-identical page-copy checks. Automatic approval review required explicit authorization for those four specific pages and the OpenAI/Codex destination; the owner supplied it before any new private-page model execution. Private results: raw 19 / 19, workbook 18 / 19, documents 5 / 5. Overwritten/occluded values were unclear and blank 2 / 2, with unsupported filled values 0 / 2. Correct blanks are excluded from accuracy. One terminal-dash amount stayed faithful in raw output but remained flagged text in Excel rather than the reference's numeric amount; preserve this failure for a future normalization-contract decision.

Fixed an evaluation matching defect: requested/line sheets carry Document ID, so the scorer now derives Document type by joining source filename and unique ID to actual document metadata, never by matching the value being graded. Added a reversed-order same-page-document regression and duplicate-ID ambiguity check, plus fixed-sheet reference preflight validation. Preserved preliminary scores, frozen answers and output artifacts, then rescored. An alternative private reference v2 prepared during diagnosis was not run; the original v1 is the scored case after fixing the metadata join. This correction changes evaluation code, not extraction prompts or source answers.

All six extractions kept the same 0.3.3 package hash and unchanged datasets. Requested model was gpt-6.1-sol through the current OpenAI/Codex ChatGPT login; actual CLI identity remains Unknown. Sources are new to prior evals, not proven unseen layouts/training data; three cheques share a form. References need owner adjudication, one execution per case in a shared chat does not measure independent variance, and only configured fields are scored. No page-attachment receipt or verified image-attention claim is made.

Updated README, evaluation guidance, the [completed report](evaluations/2026-10-08-openai-0.3.3-onboarding.md), aggregate JSON and CSV accuracy matrix. Private data remain ignored locally. Validation: 104 tests passed, package drift/link checks passed and git diff --check passed. The reusable additions are the staged conversation runner, holdout freeze/verification, abstention metrics and corrected cross-sheet matching. Prompt/package version remains 0.3.3 and experimental. No commit or push.


### 2026-10-08 — Explicit terminal amount dash interpretation, 0.3.4

After committing progress as cf4cd73, the owner requested the next coding step without authorizing another commit. Addressed the 0.3.3 terminal-dash normalization gap with a reusable interpretation contract: a readable amount ending in one ASCII dash remains readable transcription, but its sign is unknown until the user confirms the convention for the selected documents. Default processing preserves text, explains the ambiguity and excludes it from arithmetic. The batch-only --amount-dash option accepts end-mark or negative for confirmed positive-ending/negative-sign conventions; it never infers a choice from totals or document type. Mixed conventions need separate batches. This adds no new task-blocking gate: unresolved documents continue as flagged text.

Shared parsing applies only to standard amount fields, including line and statement amounts. It does not repair malformed/multiply-signed values, convert quantities, override unclear fields or rewrite custom observations. Every converted amount retains its original notation in review reasons, and Run info records the selected option. Raw JSON stays byte-identical. Shared extraction guidance uses a finance-language clarification; tool adapters own the CLI options. Family entry prompts and the per-chat policy question are unchanged.

Added fixed invented processor inputs and three independently written expectation files under eval/processor-cases/amount-dash-v1, plus a repeatable local processor runner with core/Python versions and script/input/reference hashes. The shared scorer reports 17 / 17 workbook checks per convention, 51 / 51 total; correct blanks are separate and excluded. All 9 / 9 expected document review flags appear. No model or private PDF is used, and these results are not recognition accuracy. Earlier private answers and the 0.3.3 18 / 19 workbook score remain unchanged; no convention was assumed for those historical documents.

Rebuilt both family packages as experimental 0.3.4. Updated README, changelog, evaluation guidance and the [processor report](evaluations/2026-10-08-core-0.3.4-amount-dash.md), JSON provenance and CSV matrix. Validation: 108 unit/regression tests passed, package drift/link checks passed, Codex skill validation passed, git diff --check passed. Fresh model evaluation is still required; literal-first-policy-question timing remains unresolved. No commit or push in this step.


### 2026-10-08 — Live 0.3.4 model validation, three amount conventions

The owner requested a model accuracy validation after the deterministic 0.3.4 checks. Added one invented two-page PDF and three fixed custom/raw/workbook scenarios for unknown, positive end-mark and negative-sign interpretations. Visually reviewed both pages and recorded all ten input/reference hashes plus the unchanged package hash before model execution. No source/answer/prompt tuning took place after seeing results.

Ran the three scenarios once each, in that order, requesting gpt-6.1-sol through the current OpenAI/Codex ChatGPT login. Reused the exact previously acknowledged CLI session with fresh workspaces, preserving its real acknowledgement and historical context. This avoids fabricating consent but does not provide independent fresh-session evidence. CLI identity remains Unknown. The model received the public PDF and custom settings, not supplied extraction JSON or expected answers. No new private files were selected.

Results: raw 42 / 42, workbook 63 / 63, document records 6 / 6, review flags 6 / 6 and recorded conventions 3 / 3. Raw correct blanks 18 are excluded. Unknown amounts remained text and not checkable; positive/negative conventions affected standard numeric fields while raw/custom notation stayed unchanged. The negative scenario correctly replaced the prior batch's positive convention. These are configured-field/status/page checks on two unique printed pages, not broad handwriting/OCR or unseen-layout accuracy. Both family packages remain experimental, with no new-chat onboarding claim or automatic-default promotion.

CLI WebSocket reconnects recovered through HTTP fallback. The adapter had treated transient reconnect notices as terminal failures. Added a narrowly scoped, tested distinction requiring later successful completion; fatal/unknown errors and notices after completion still fail. The first complete execution was reclassified from preserved evidence only after exact session, exit status, output and all integrity checks matched. Original metadata and a stream-hash review record were retained. Subsequent runs used the corrected adapter directly. No model output or answer was edited, and the skill package hash stayed ef249d1898c70f819adf4a29e4a8b11cd195395dacda5391225439e7bd8aef36.

Published the [live report](evaluations/2026-10-08-openai-0.3.4-model.md), aggregate JSON/CSV and reusable public scenario definitions; updated README. Historical reports and private answer keys remain unchanged. Validation: 109 unit/regression tests passed, package drift/link checks and git diff --check passed. No commit or push.

### 2026-10-08 — Raw line-item and statement scoring

The owner requested the next coding/testing step. Extended the reusable evaluator to address a known blind spot: raw scoring previously excluded invoice lines and statement transactions, so numeric workbook checks could conceal changed transcription. New optional Raw line items and Raw statement lines tables compare printed strings using file/pages/type/document occurrence/line position, without matching on values or model-generated document IDs. They retain filled raw strings even if the field is flagged unclear.

Added separate invoice-line and statement-line recall/precision counts to the CSV, with numerator/denominator and undefined rates for unconfigured or empty scopes. Structural checks fail missing or extra all-blank rows independently of field accuracy. New reference validation rejects value-based identities, duplicate rows/columns, non-text comparisons, numeric reference values and incomplete source identities before public preparation or holdout freezing, and at scoring. Existing reference formats and historical scores are preserved.

Added an invented supplied-transcription fixture with two same-page invoices, an inconsistent printed total, trailing dash, an unreadable row and debit/credit transactions. It contains no real PDF or private company data. Baseline: 25 / 25 nonblank checks, 7 excluded blanks, invoice rows 4 / 4 and statement rows 2 / 2. Seven demonstrated control outcomes matched expectations: the baseline passed, and six deliberate transcription/coverage errors failed. Omitting the unreadable row still gives 25 / 25 field checks but fails row recall at 3 / 4. These are evaluator tests, not model recognition results.

Validation: 12 new regression tests and the complete 121-test suite passed; generated-package checks passed. Added the [regression report](evaluations/2026-10-08-raw-lines-regression.md), JSON hashes/details and CSV matrix, and updated README/evaluation guidance. Family prompts, package bytes and version 0.3.4 remain unchanged in this step; no model run or default promotion is claimed. Fresh model cases need line references frozen before execution. No commit or push.

### 2026-10-08 — Continue through image-only live tests; daily commit authorization

The owner instructed continued coding/testing until a product decision is needed, and explicitly authorized direct commits for today. This session-specific authorization supersedes the repository's ask-before-each-commit rule for today's local commits; it does not authorize a push or permanently change AGENTS.md. Committed the previously validated 0.3.4 amount handling and raw-line evaluator as 0a5137a.

Added versioned payment/energy scenarios over the existing public image-only PDF with raw document/custom/line references and two expected B pages. Reviewed both rendered pages and froze inputs and package before execution. Initial v1 references confused the certificate's Other worksheet with its raw document type. Found this from the documented open-vocabulary contract during execution before examining extracted answers; preserved v1 references and failures. Fixed the reference identity in v2 for unique one-document pages, added regression tests, froze v2 and ran two new model executions. No prompt, processor, package bytes or expected values were altered.

All four executions requested gpt-6.1-sol through OpenAI/current Codex ChatGPT login, with actual CLI identity Unknown. The same acknowledged session continued by exact ID without repeating the question. V1 payment raw 14 / 20 and workbook 21 / 21; v1 energy raw 10 / 34 and workbook 25 / 25. The raw failures result from certificate type matching. Fresh v2 payment raw 17 / 17 and workbook 21 / 21; fresh v2 energy raw 22 / 22 and workbook 25 / 25. V2 document records 4 / 4, raw line values 6 / 6, row slots 2 / 2 and review flags 4 / 4. Raw/workbook correct blanks (32 / 29) are excluded.

All pages were prepared as B with empty text layers and OCR disabled by the agent. Route reports and images match end-of-turn snapshots, but the CLI stream does not independently prove image inspection; no supplied-image receipts were captured. This repeated, known public source in a long shared chat is workflow evidence, not unseen-image, handwriting or local-OCR accuracy. No private source was used and both family packages remain experimental 0.3.4.

Added a no-overwrite scenario generator, three regression tests and the [live report](evaluations/2026-10-08-openai-0.3.4-scan-lines.md) with all four scores and provenance. Validation: 124 tests passed; package drift/link checks passed. Updated README and evaluation guidance. The next product decision is whether a brief skill announcement before the exact policy question is acceptable, provided document work still waits for a real affirmative, or whether literal first-message-only wording requires a tool-specific entry flow. Existing policy behavior is unchanged pending the owner's choice. No push.

### 2026-10-08 — Decision A: allow a brief skill announcement, 0.3.5

The owner chose A. Updated the shared chat-start rules, both family entry prompts, AGENTS.md, design/evaluation guidance and README: a brief skill-use announcement may precede the exact question, but a real affirmative still precedes document reading, rendering/OCR, setup, custom settings and workbook production. Per-chat acknowledgement and provider/account scope are unchanged. Rebuilt both experimental family packages as 0.3.5; extraction/processing scripts are unchanged.

Versioned the evaluator's opening contract as announcement-before-question-v1. Kept literal question_first as a historical diagnostic and retained literal-first-v1 for old turns, so reporting does not silently regrade historical results. Simple English announcements can pass automatically; other wording requires maintainer review, and early work or a missing/altered/repeated question cannot automatically pass. Added four regression tests covering those boundaries and preservation of legacy reporting.

A fresh public-case conversation requested gpt-6.1-sol through the current OpenAI/Codex ChatGPT login. Actual identity remains Unknown; package hash c2d5c1358ad71865d3afd83f6e32e40deba1fe932485ab881e94ba86f7b963a4. It announced the skill and explained the pause, then asked the exact question once. No command events and no changed files were observed. The conservative automatic checker referred the preface for review; a separate stream-hash-bound manual review passed it under A (1 / 1). Literal first-message remained 0 / 1 and was not hidden. No extraction was attempted and field accuracy is undefined.

Presented the question to the owner for this new test conversation. The owner then supplied a real affirmative reply, relayed verbatim to the exact waiting session with its origin recorded; no earlier-chat acknowledgement was transferred. Payment extraction resumed, then energy extraction used a different custom in the same chat. Neither post-acknowledgement turn repeated the question (2 / 2). Payment raw 17 / 17 and workbook 21 / 21; energy raw 22 / 22 and workbook 25 / 25. Total raw 39 / 39, workbook 46 / 46, document records 4 / 4 and expected review flags 4 / 4; raw/workbook correct blanks 32 / 29 are excluded. Package and dataset hashes remained unchanged in both executions. These are known public image-only pages in a shared session, with no verified image-attention or new handwriting-accuracy claim.

Validation: 128 tests passed, generated-package drift/link checks passed and Codex skill validation passed. Added the [opening and resume report](evaluations/2026-10-08-openai-0.3.5-onboarding.md), JSON provenance and CSV accuracy matrix. Prepared a local, ignored owner-review sheet for the four previously approved private handwritten pages; asked the owner to adjudicate an amount convention and provisional references. Original frozen references and historical scores remain unchanged pending those answers. No push.


### 2026-10-08 — Any policy-question reply continues, 0.3.6

The owner replaced the affirmative-only gate with a read-before-upload reply: "No, but I will read it before I upload any confidential data". Offer it alongside Yes at the first invocation in each new chat. Any user answer, including No, uncertainty or other wording, satisfies this workflow step without another confirmation. Only absence of a reply waits. A brief skill announcement remains allowed. Actual task changes or stop requests still apply.

Updated shared chat-start/custom-settings guidance, both family entry prompts and scoped policy references, AGENTS.md, README and design/evaluation guidance. Record response received with the original wording rather than asserting that a user has read the guidance, made a promise or provided legal consent. Provider/account scope and permission for external actions are unchanged. Rebuilt both experimental packages as 0.3.6; extraction/processing scripts and frozen answers are unchanged.

The conversation runner now stores any-response-v1 on new sessions, accepts any nonempty reply and records policy_response / response_received. Historical sessions retain their affirmative gate and scores. Public negative fixtures can test continuation but remain labelled scripted and cannot stand in for human consent or authorize private uploads. Added five regression tests covering reply variants, honest provenance/silence, public-fixture scope, versioned opening choices and fresh-chat state isolation.

Validation: 133 tests passed with the bundled Python runtime, package drift/link checks passed, Codex skill validation passed and git diff --check passed. The initial local-venv suite attempt lacked pypdfium2 (one error and ten skips); reran with the existing bundled dependencies, with no skipped tests. No new live model run or recognition-accuracy claim is made for 0.3.6. Prior 0.3.5 reports remain historical. No commit or push in this step.


### 2026-10-09 — Owner adjudication, cheque parties and Cash Memo invoices, 0.3.7

The owner confirmed the displayed reference fields for handwritten review groups 1, 2 and 4 and corrected group 3: both records are Invoices, including the Cash Memo. Explained that Billing documents is a worksheet bucket (Invoice/Credit note/Debit note by default), not a document type. The owner also required both Payee and Payer on cheques. Existing extraction fields and payment columns already support them, but the earlier private accuracy checks did not score these names.

Read the three existing approved page images to prepare party references without consulting model predictions. The owner subsequently confirmed all three Payee/Payer pairs and that the Cash Memo's terminal dash means a positive amount ending. Recorded these scoped decisions and versioned reference drafts in ignored local storage; original reference/lock hashes remain unchanged. Remaining unreviewed fields in group 3 retain provisional status. The confirmed amount convention applies only to that Cash Memo; raw notation remains unchanged. No private values enter tracked documentation and no new private model run was launched.

Updated shared payment guidance to read both parties by default, distinguish the drawer from the bank, preserve names, and explain absent/unclear parties without substituting the company profile, adjacent documents or a signature. Added payer to the payment example. Shared classification now treats a sale Cash Memo as Invoice while preserving its printed title; two invoices on one page remain separate records. Rebuilt both experimental family packages as 0.3.7; payment schema and deterministic extraction processing are unchanged.

Added the known-source public format-parties-v1 scenario, fixed raw/workbook party references and a no-overwrite generator, preserving older format scenarios. Extended workbook evaluation to derive source-order document occurrences and join them to custom/line rows by unique source/Document ID, supporting same-page invoices without value-based matching. Five new regression tests cover party omissions/swaps/bank substitution, unclear payer output, two billing records and reordered/ambiguous line identities. These tests validate processing/evaluation of supplied transcriptions; they do not establish new model recognition accuracy.

Validation: all 138 unit/regression tests passed using the bundled Python runtime, including five new tests. Both generated packages passed drift/link checks; Codex skill validation and git diff --check passed. Verified all four original private expected/lock hashes are unchanged and the new reference metadata is valid. No new live model evaluation, commit or push in this step.


### 2026-10-09 — Default positive amount endings, 0.3.8

The owner authorized a positive default for readable amounts ending in a single ASCII dash, unless user instructions or applicable source evidence say otherwise, and requested continued coding/testing without a clarification pause. Updated parsing defaults, shared extraction guidance, tool adapters and both experimental family packages. The raw/custom string stays unchanged; standard amount columns become positive with the original notation retained in review reasons. Run info separates the default positive assumption from an explicit batch option. Explicit negative and unresolved-text modes remain available; malformed signs, unreadable fields and quantities are not repaired.

Researched primary Oracle, SAP and Microsoft format documentation. Trailing-minus negative formats are documented in software, but this review did not establish a reliable country-by-country handwriting list. Added a short linked amount-notation reference distinguishing applicable format evidence from country/language/vendor guesses. No geographic auto-override or new confirmation gate was added.

Added the default invocation to the deterministic processor matrix using unchanged positive v1 expectations, plus regression coverage for default handling and truthful audit wording. The final four-mode matrix passed 68 / 68 nonblank workbook checks and 12 / 12 expected review flags; 24 correct blanks are excluded. Raw/config/reference bytes remained unchanged. The public amount-dash-model-v2-default case reuses the existing two-page source with no sign convention supplied in custom.md.

Initial public live testing used a fresh Codex chat and an explicitly labelled scripted No response to exercise any-response-v1; no human acknowledgement was invented and no private source was sent. Default, explicit negative and explicit unresolved-text scenarios each passed raw 14 / 14 and workbook 21 / 21. The party scenario passed raw 10 / 10 and workbook 11 / 12; its legacy reference omitted the printed currency from Requested data. Retained that failure and v1 references. A separately versioned v2 reference follows the existing unit contract and the source's HKD label, adds unit checks, and is frozen before a new execution.

Inspection also found the inherited review message called every convention confirmed, which was inaccurate for the new default. Corrected the catalogue and added an assertion against that wording. Preserved the preliminary package hash e16aa1101b2ff0d313a99d2c677c51eb753f2b9a3a622df3450911e32124486c and its four runs. Rebuilt the final package as 7d42c3f34d605205616feaf14451e81cc12e1664cdad22375fd10dd1e775b710 and began a fresh default-case retest using the labelled read-later fixture, followed by the corrected party scenario. These are two draft artifacts within uncommitted 0.3.8, not interchangeable evaluation evidence. References and model outputs were not edited to hide failures.


Final artifact results: default raw 14 / 14 and workbook 21 / 21; party v2 raw 11 / 11 and workbook 13 / 13. Combined final scope raw 25 / 25, workbook 34 / 34 and documents 4 / 4; 17 raw and 5 workbook correct blanks excluded. Payee/Payer passed 2 / 2 raw and 2 / 2 workbook checks. All six preliminary/final extraction turns continued after the labelled response without repeating the question. Both new-chat openings exceeded the narrow automatic layout patterns but passed separate maintainer trace review; automatic results remain visible. Source/reference and package/data integrity checks passed.

Published stage-separated live JSON/CSV and the [0.3.8 report](evaluations/2026-10-09-openai-0.3.8-default-dash.md), plus the final deterministic matrix. Requested model was gpt-6.1-sol via current OpenAI/Codex ChatGPT login; actual identity remains Unknown. Four public printed pages were reused, with no new private/handwriting evaluation or verified image-attention claim. Both families stay experimental. All 139 tests passed after the final reference correction, generated-package drift/link checks and Codex skill validation passed. No commit or push in this step; the owner requested uninterrupted coding/testing, not another commit.


### 2026-10-09 — Field-level handwritten and computer-generated endings, 0.3.9

The owner narrowed the prior default: an ending ASCII dash on a handwritten amount means a positive ending; computer-generated notation requires user confirmation. This supersedes the 0.3.8 unconditional positive default. Unknown origin also stays as printed pending a reply. The skill continues unrelated extraction and excludes unresolved values from arithmetic. It asks in finance language and reuses only an existing reply that actually covers the selected source/fields.

Implemented optional amount_notation on documents and individual line/statement rows. Origins are handwritten, computer-generated or unknown; document-wide handwritten flags never establish an individual field's origin. Auto processing converts handwritten endings and honours recorded, scoped per-field confirmations. This permits a confirmed printed negative total beside handwritten positive amounts without imposing one sign on the whole page. Legacy global options remain for an explicit user-confirmed batch-wide convention; conflicting field confirmations are rejected. Raw/custom values remain strings, unclear values stay blank and quantities/malformed notation are not repaired. Neither metadata validation nor the processor authenticates an agent's origin classification or claimed user reply.

Updated shared guidance, both adapters, README and both experimental generated packages. Added synthetic amount-dash-v3 inputs and pre-authored references; the seven-case deterministic matrix passed 119 / 119 nonblank checks and 21 / 21 expected review flags, with 42 correct blanks excluded. Input/reference/script hashes remained intact. Historical v1 references and the 0.3.8 live results remain unchanged; they are not accuracy evidence for 0.3.9. See the [processor report](evaluations/2026-10-09-core-0.3.9-amount-origins.md) and accompanying JSON/CSV.

All 144 tests passed. New coverage checks field origin versus the document flag, mixed tables, scoped positive/negative replies, missing/invalid metadata, override conflicts, unclear values and raw grading. The first suite exposed missing custom settings in a new test helper; fixed the helper and reran the complete suite successfully. Generated-package drift/link checks, Codex skill validation and git diff --check passed. No new model/private-document run, commit or push was performed. Recognition of actual handwriting and live confirmation behaviour still need a model evaluation for these package bytes.


### 2026-10-09 — Staged live clarification eval, no package change

The owner requested the next coding/testing step without committing. Added an entirely public two-page printed fixture, including a handwriting-style font as a false-handwriting trap. Source renders were visually inspected before model execution. It is not human handwriting and uses no company documents. Frozen references distinguish unresolved totals, a page-1-only positive reply and a later page-2 negative reply. Replies are labelled public scripted fixtures, not fabricated owner confirmations.

Added clarification.py and optional start-time scenario locks to the conversation harness. It resumes the exact session, sends only the current frozen reply, keeps future answers outside the model workspace, archives each raw/workbook stage separately and rejects modified sources/references/packages, out-of-order replies and unexpected/changed old workbooks. Existing conversation behaviour remains supported. Package bytes remain 0.3.9; no prompt or processor changes were made in this step.

The first live run exposed a scorer gap: line sheets store Document ID but omit Pages, so the new page-based reference could not match existing lines. Preserved the pre-fix 8 / 24 pending score and added a parent Pages join for line/statement sheets only, with duplicate-ID/swapped-value tests and protection against overwriting custom observation evidence pages. Unchanged artifacts were rescored. V1 then had correct configured values but two structural failures per stage because its reference omitted the required Requested values table. Preserved those failures and v1 answers. Authored v2 references with explicit detail-table checks, froze them before a new conversation, and reran all three stages.

The corrected live run passed raw 42 / 42, workbook 72 / 72 and review flags 6 / 6, with no blank cells in the denominators. The same two source pages were observed across stages, not six independent documents. Both pending totals stayed as text; the first reply changed only page 1 to numeric 360; the second changed page 2 to numeric -720 while keeping its line positive and reporting the arithmetic mismatch. Source fields/lines/custom observations and earlier workbook hashes remained unchanged. The computer handwriting-style font did not bypass confirmation.

Both new-chat policy openings included the exact question and choices but extra explanation exceeded the narrow automatic layout matcher. Kept automatic failures and separate stream-hash-bound maintainer reviews accepting the observed pause. No policy question repeated after the scripted response. Requested model gpt-6.1-sol via current Codex ChatGPT login; actual identity Unknown; codex-cli 0.162.0-alpha.2. Both experimental families remain unpromoted. Published the [stage-separated report](evaluations/2026-10-09-openai-0.3.9-dash-clarification.md), JSON and CSV, preserving the v1 reference defect and original scorer failure.

All 152 tests passed, including eight new clarification/reference/join regressions. Generated-package drift/link checks and git diff --check passed. No new private-data or human-handwriting accuracy claim, commit or push.

### 2026-10-10 — Partial private 0.3.9 regression and execution recovery

The owner selected a rerun of the same four approved private handwritten pages and authorized a local commit after that work. Kept the 0.3.9 package bytes unchanged (OpenAI hash 71b918aabef3688f5e9aa4463237898d12e8e0aaa8a2eae44b44f468b1f67653). New regression locks preserve the original holdout locks and source bytes, and freeze the owner's scoped reference review separately. Reused sources are explicitly known-source-regression, never fresh holdouts. Three cases have owner-confirmed configured references; the same-page invoice case has four owner-confirmed cells and remaining provisional checks. No reference was rewritten after predictions.

Resumed the existing benchmark session with its actual human policy reply through the already approved OpenAI/Codex destination, requesting gpt-6.1-sol. The first two pages passed raw 13 / 13 and workbook 13 / 13 nonblank checks, including 4 / 4 Payee/Payer checks in each layer. Their two expected document records were present. The third page timed out at 1,200 seconds, and its separate retry also timed out at 1,200 seconds despite WebSocket retries and HTTPS fallback. The final page was attempted separately with a recorded 300-second limit and also timed out. Preserve all five attempts: completion is 2 / 4 pages, not a full pass. Actual model identity remains Unknown.

The real handwritten terminal-dash and predeclared unclear-field checks are on incomplete pages and remain unavailable. Provisional accuracy and abstention rates are undefined. Published an aggregate-only [partial report](evaluations/2026-10-10-openai-0.3.9-handwritten-regression.md), JSON and CSV; private pages, field values, references and traces remain ignored. Larger rendered images were observed on the failing case, but a causal link to the connection failure was not established. No overall handwriting claim or automatic package promotion is justified.

Added regression freezing/verification and scoped metadata to the eval harness. A public scripted policy response cannot authorize private-case continuation. Incomplete executions can be retried in the exact same acknowledged session with a separate workspace and attempt ID; completed but inaccurate predictions cannot use this recovery path. A distinct next case can continue after failure without erasing or marking the prior attempt complete. Recovery prompts restrict work to the new workspace. Tests cover lock tampering/source substitution, private policy provenance, preserved failures, same-session retries and next-case recovery.

All 158 local tests passed, generated-package drift/link checks and Codex skill validation passed. The remaining two model results require working CLI connectivity; the failed attempts remain part of the evidence. No push was authorized or performed.

### 2026-10-10 — Continue unfinished private evaluation with recorded recovery

The owner requested completion of the remaining two pages. Kept the evaluated 0.3.9 package and frozen references unchanged. Added optional HTTPS transport for the Codex evaluation adapter, retaining the same ChatGPT endpoint, managed OpenAI login, requested model and exact session; no persistent user configuration or credentials are changed. A public connectivity-only probe succeeded. Stalled old-session attempts were explicitly interrupted and archived rather than discarded or scored as recognition failures.

A fresh HTTPS benchmark conversation opened normally. The owner supplied the actual response “No, but I will read it before I upload any confidential data” for that new chat. Recorded the response verbatim with its origin; did not transfer the older chat's reply or describe the new reply as verified reading. The model continued without demanding Yes. Automatic opening-layout checks still reject extra explanation/formatting; separate trace review records that only skill instructions were read before the reply. The public setup case completed before the two approved private pages were attempted.

Private image work was visible in the full CLI rollout even when ordinary CLI output appeared idle: the model opened the page and rendered/viewed a rotated recovery image. The initial ten-minute private attempts remained incomplete. Added explicit per-attempt deadlines and recovery of an earlier failed case after later batches. Optional resume-work copies hash-recorded archived intermediates into a new workspace, requires one manifest, and excludes the previous workbook and evaluator references. Fresh package/source/custom verification still applies. Retried incomplete work is not an independent repeat, and completed inaccurate predictions cannot use this recovery path.

All 165 local tests passed, including historical-case recovery, actual subprocess deadline enforcement, fixed HTTPS destination/authentication, unchanged archived artifacts and ambiguous-manifest rejection. Final review also found that the opening batch has no case ID on its policy turns; archived metadata now makes that batch recoverable after later work, while a completed opening batch still blocks reruns. Package drift/link checks passed. The last page needed a further 3,600-second attempt after its 1,800-second attempt prepared images but produced no extraction or workbook. It continued the same approved source and session with archived intermediates; every timeout and interruption remains recorded.

All four pages now have completed outputs, containing all five expected document records. Strict frozen-reference checks are raw 23 / 25 and workbook 25 / 27, excluding four correct blanks in each layer. Owner-confirmed scope is raw 20 / 21 and workbook 22 / 23; provisional scope is 3 / 4 in each layer. One strict difference is Payer capitalization: the model copied a second, visibly printed form of the same name. This limitation was declared before execution. A separate hash-bound maintainer source review supports that alternate, without claiming new owner confirmation or altering the frozen score. The other difference is a provisional amount; a private illustrated review was prepared and owner adjudication requested. No answer or reference correction was invented.

The real handwritten terminal dash remained in raw transcription and became a positive numeric workbook amount, with the individual field identified as handwritten and no source-specific sign reply supplied. Both predeclared unreadable observations stayed unclear and blank: one owner-confirmed and one provisional. Strict Payee/Payer checks are 5 / 6 in each layer, or 6 / 6 source-supported identities including the separately reviewed casing alternate. There are no missing/extra scored rows or unprocessed inputs in the completed outputs. These are selected checks, not verification of every field.

Published the [completion report](evaluations/2026-10-10-openai-0.3.9-handwritten-completion.md), aggregate JSON and CSV separately from the unchanged partial report. All 14 private execution attempts are retained: four completed, six timed out and four were interrupted for recovery. Slow execution and repeated recovery remain practical limitations. The package hash is unchanged, actual model identity remains Unknown, and both families remain experimental. Private files, answers, detailed traces and source reviews remain ignored. No new commit or push has been performed in this step.


### 2026-10-10 — Confirmed amount error and digit-boundary recovery, 0.3.10

The owner confirmed the first invoice Total in case-004, agreeing with the frozen reference. The model's different reading is now a confirmed error. Saved the actual reply in ignored storage with its two-cell scope (raw and workbook Total), and published a hash-bound owner-adjudication supplement. Original source, reference, prediction and completion report remain unchanged. The combined strict score stays raw 23 / 25 and workbook 25 / 27; owner-confirmed scope becomes 20 / 22 and 22 / 24, with remaining provisional checks 3 / 3 in each layer. The Payer source-alternate review remains a separate maintainer judgement.

Added one narrow paragraph to the shared PDF recovery reference: when a stroke beside or across a number could be a digit, rule, crease or overwritten mark, keep the label and surrounding context in the bounded recovery view; leave unresolved values unclear. It does not tell the reader to remove a leading digit, substitute a known amount or use arithmetic to fill it. The confirmed error motivates this hypothesis; its exact visual cause and whether the revised prompt fixes that private example are not established. Both generated family packages are now experimental 0.3.10; the entrypoints and model recommendations are unchanged.

Created digit-boundary-v1, three public synthetic printed raster pages covering a nearby rule, a genuine leading digit and an obscured prefix. Full-page previews were inspected; no PDF text layer remains, and all three pages select route B. Source/config/reference bytes were fixed before the new model execution. The generator refuses overwrites. These are one synthetic content group, not three independent business documents or human handwriting examples.

Added a reusable scorer/processor control runner and four meaningful regression tests. Correct supplied transcription passes raw 13 / 13 and workbook 15 / 15; all four injected errors fail raw scoring. A guessed standard Total remains visible as a raw error even when the workbook blanks the flagged field. An inconsistent unclear custom observation is rejected without a workbook. The first control-run attempt assumed all mutations would yield workbooks; kept that incomplete local attempt and updated the harness to represent the expected rejection explicitly. The final matrix records unavailable workbook scores rather than zeroes or passes. These controls perform zero model runs.

All 169 local tests passed. Prepared a fresh workspace for the public case, then started a separate bounded OpenAI/Codex model evaluation with requested gpt-6.1-sol. The new conversation uses an explicitly labelled scripted read-later response for the public fixture only; it does not claim a human reply or authorize private continuations. The completed live result is recorded below, separately from the deterministic matrix. No private document was newly sent in this step. No commit or push has been performed.

### 2026-10-10 — Complete OpenAI 0.3.10 public digit-boundary evaluation

The owner assigned Anthropic testing separately and requested completion of OpenAI testing/reporting without a commit. Finished reviewing the already completed public run: one extraction attempt completed in 226.76 seconds under a 900-second deadline, with raw 13 / 13 and workbook 15 / 15 configured nonblank checks. Two raw and three workbook correct blanks are excluded. All three expected invoice records and requested observations matched, with no missing/extra scored rows or unprocessed input. Both readable totals were retained correctly; the obscured complete Total remained unclear and blank, including its custom observation, with a workbook review flag. These overlapping checks are not independent samples.

The rollout records an image-tool call returning all three full pages and a second call returning one page-3 recovery crop. All pages selected route B; Tesseract was unavailable on the configured path/PATH. Preserved the distinction between route preparation, the agent's reading ledger, observed image-tool outputs and the absent CLI attachment receipt. Saved a hash-bound maintainer extraction-trace review; neither correct answers nor image calls prove model attention. Sources, settings, references, raw extraction and the current OpenAI package match their recorded hashes.

Opening-layout automation remains invalid because the model added explanation and combined its instruction reads. Retained that audit alongside the separate maintainer judgement accepting the observed pause before document work. The explicitly scripted public read-later reply led to extraction in the same session without repeating the question. It is not a human acknowledgement or authorization to process private sources. Silence, reset and compaction were not newly tested here.

Published the [live report](evaluations/2026-10-10-openai-0.3.10-digit-boundary.md), JSON evidence summary and unchanged scorer CSV, and updated README. Requested gpt-6.1-sol via current Codex ChatGPT login; reported identity remains Unknown. CLI is 0.162.0-alpha.17.2, different from the earlier private run's alpha.2, so no controlled prompt-only comparison is claimed. One known synthetic printed content group is not a handwriting benchmark or a fresh multi-route/custom-purpose regression. The owner-confirmed private amount error has not been rerun with 0.3.10. The package remains experimental. No Anthropic changes, new private uploads, commit or push in this completion step.

Final package-drift/local-link checks, report evidence hashes, preserved 0.3.9 completion-report hash and git diff --check passed. The first package check encountered an inaccessible sandbox temp directory; rerunning with the existing writable TEMP/TMP location passed without source changes. The recorded 169-test suite remains applicable because this completion step changed only reports/documentation, with no prompt or runtime changes.

### 2026-10-10 — Rerun the owner-confirmed private amount with OpenAI 0.3.10

The owner explicitly requested the same private case under 0.3.10, with reporting and no commit. Preserved the prior source, custom settings, references, prediction and locks. Created a new known-source-regression lock against the existing 0.3.10 package hash, adding the earlier scoped owner confirmation to the reference-status record without changing values or confirming unrelated provisional fields. Started a separate evaluation session so the earlier wrong prediction was not in its conversation. No evaluator answer or adjudication was supplied to the tested model.

The new opening repeated the policy question three times. Kept the automatic invalid audit and a separate trace review accepting the observed pause only; the once-per-chat behaviour fails. The owner supplied the actual new-session reply “Yes, I have read it.”, which was recorded with its origin. The public bootstrap and subsequent private batch continued without repeating the question. No response from another chat or scripted fixture was used to authorize the private continuation.

The private attempt completed once, without retry, in 1,670.30 seconds under a 3,600-second deadline. The target Total now matches the owner's reference in both raw extraction and the workbook. Both source documents are present, and the predeclared unclear custom observation remains blank. However, the neighbouring Cash Memo was classified Receipt rather than the owner-confirmed Invoice and placed on Reference documents. Strict raw checks are 3 / 7 (three correct, two misses, two nonblank extra values); workbook checks are 4 / 8 (four correct, three misses, one nonblank extra value), with an additional unexpected Reference documents row. Three correct blanks in each layer are excluded. Classification-sensitive joins explain the propagated missing/extra failures; the `invented` category here does not establish fabricated amounts.

Supplementary source-record review confirms the Cash Memo's original terminal dash remained in raw data and its workbook amount became the correct positive number under handwritten-origin auto processing, with no global sign override or explicit sign confirmation. This does not repair the classification score. Source images were opened in original, 90-degree and 270-degree orientations; all three image-tool calls returned content. The private turn did not visibly read document-types.md, but a causal explanation is not established. The target correction does not prove the new recovery paragraph caused it: CLI version and session history differ from the previous run, reported model identity remains Unknown, and this is one reused source rather than a fresh holdout.

The public printed-001 bootstrap separately revealed an existing reference-construction defect. Its line identity requires Document number, but all three frozen expected line rows omit it. The actual lines contain their parent invoice's number. Kept the resulting 19 / 49 workbook score, 11 excluded correct blanks and false missing/extra pairs. A hash-bound diagnostic on unchanged artifacts confirms 15 / 15 nonblank line values by their existing line positions; no reference correction or replacement score was published. That legacy case lacks raw expectations. The public issue is separate from the real private classification regression.

Published the [aggregate private comparison](evaluations/2026-10-10-openai-0.3.10-private-case-004.md), JSON and CSV, and updated README. Owner-confirmed, provisional and unmatched-extra counts are separate; private documents, amounts, names and detailed artifacts remain ignored. The next fixes concern Cash Memo classification, repeated onboarding questions and the legacy public reference, but none was applied to the evaluated package. The existing 169-test implementation result remains applicable. No commit or push.

Final report integrity, scope denominator and CSV consistency, original report preservation, private-field exclusion, generated-package/local-link checks and git diff --check passed. The prior 169-test suite was not repeated for this report-only completion; those passing checks do not override the observed model failures.

### 2026-10-10 — First Anthropic 0.3.10 live evaluation in Claude Code

The owner asked for Anthropic/Claude Code testing of the current 0.3.10 package, using only public synthetic fixtures and the model they had selected. Earlier approval to show private documents to OpenAI does not extend to Anthropic, so no private file was used. The work was done in a worktree reproducing the main checkout's uncommitted 0.3.10 state. The main checkout itself was not modified.

Before any extraction, a freeze record stored hashes for the package, sources, custom settings, company profile and answers. `conversation.py` stays Codex-only and the one-turn live launch stays blocked. Added a minimal Claude staged runner (`eval/runner/claude_session.py`). It executes `run.py --prepare-only` workspaces in fresh persisted chats with exact session IDs. It sends a labelled scripted read-later reply only after the exact question is asked, and writes execution evidence to a separate batch. The prepared records remain `prepared_only`. The adapter gained a session command; the earlier one-turn command is unchanged. The requested model was `claude-opus-5-5`, passed through unchanged; the recommended Sonnet was neither selected nor tested. Every CLI event reported `claude-opus-5-5`; that is reported, not verified, identity.

The baseline exposed harness problems, not prompt problems. The adapter's original allowlist omitted `reading_capabilities.py`/`pdf_routes.py`, which the package tells the agent to run with an existing interpreter. That was fixed before the first case. In non-interactive mode, no PowerShell allow rule matched `& "<interpreter>" script.py`; a public smoke test confirmed this. Compound commands with `cd`, variables or `echo` were also denied. In three baseline runs the agent fell back to native PDF reading with manual route notes. In coal-ocr-energy it concluded every shell command was blocked and stopped to ask the user, producing no workbook. That failure is preserved as unscorable. All eight completed baseline runs scored workbook 174 / 174 and raw 13 / 13.

Kept the package and prompt unchanged and made the evaluation sessions Bash-only (harness v2). A freshly prepared batch matched the freeze. All nine reruns were valid: raw 13 / 13, workbook 199 / 199, documents 19 / 19, requested observations 39 / 39, with no extra rows, unsupported fills, guessed blanks or page errors. Correct blanks are excluded. Native, image-only, wrong-hidden-OCR and mixed PDFs are reported separately for payment and coal-energy purposes. They share one content group. The hidden-OCR trap was resolved to visible values in every completed OCR run. The digit-boundary pages kept 684 and 1684 and left the obscured total unclear.

Policy question: 18 / 18 new chats asked the exact question once, with both choices and a brief announcement, before any document work. None repeated it after the reply. All wrapped it in Markdown bold, and 11 / 18 added a sentence after the choices. The automatic layout check therefore accepts none of them. The checker now routes an exact-question-once layout to review instead of `invalid`. Whether emphasis/trailing text is acceptable under decision A is left for the owner. Added a path-free summary tool and seven regression tests. Each case ran once per harness on known synthetic content, so these results do not establish general accuracy, repeatability, handwriting or OCR-assisted reading. The package remains experimental and Last eval stays unset. No commit or push was performed.

### 2026-10-10 — Sonnet/Opus repeats and Fox private regression for Anthropic 0.3.10

The owner asked for Sonnet 5.5 in new chats and repeated tests. They also decided that the coal cases are custom-field demonstrations, not accuracy benchmarks. The existing coal answers remain for earlier reports, but no raw references are added and new reports call coal a demonstration. The owner then authorized the Fox 2025 documents for Anthropic in this chat. From the offered options they chose: only the four frozen single pages; one owner reply relayed per listed waiting chat; Sonnet and Opus, three runs each.

The runner now runs each prepared repeat in its own new chat. The first Sonnet attempt (harness v2) completed 3 / 27 public chats. Sonnet combined several scripts in one Bash call, `dontAsk` denied it, and Sonnet stopped to ask rather than work around the denial. Those failures are kept. A PreToolUse hook that approved safe combined commands was blocked by Claude Code's safety classifier as self-modification; it was not used or worked around. The owner chose a recorded environment note instead (harness v3). That note exposed a harness bug of mine: the allow rule required the interpreter path in quotes, and Sonnet writes it unquoted. Harness v3.1 fixed this, with regression tests. The package and prompt never changed.

Final public results: Opus (v3) and Sonnet (v3.1) were each 27 / 27 valid. digit-boundary scored raw 39 / 39 and workbook 45 / 45, with identical values across repeats. All coal demonstrations produced their requested fields. Sonnet read files beyond the skill before the policy reply in 12 / 27 chats (folder listing or `custom.md`, never a PDF); Opus did so in 0 / 27.

Private regression locks were refrozen for the Anthropic package without changing references. The runner gained `prepare-private`: private chats wait for a human reply, scripted replies are refused, and the lock is verified before and after execution. The owner replied for 24 chats, then gave a new reply for 12 new Sonnet chats.

Strict Fox scores excluding correct blanks:

| Model | Raw | Workbook | Documents | Unclear observations kept blank |
|---|---|---|---|---|
| Opus | 71 / 75 | 77 / 81 | 15 / 15 | 6 / 6 |
| Sonnet v3.1 | 68 / 75 | 74 / 81 | 15 / 15 | 6 / 6 |

Neither model filled a value where the reference is blank. Every Sonnet v3.1 difference, and three of four Opus differences, is the account holder's name in the source's alternate casing. That alternate was declared before earlier runs and is still counted strictly. The other Opus difference is a flagged unclear Total on page 004. Aggregate-only results are published without values. These are four reused pages, not a fresh holdout or general handwriting accuracy, and the package remains experimental. No commit or push was performed.

### 2026-10-10 — Owner accepts the printed alternate Payer casing

The owner accepted the title-case company name as a correct Payer and asked for a normalization instruction later. A maintainer re-rendered cheque pages 001, 003 and 005 and confirmed that both forms are printed on each. Versioned v2 references list both forms for the Payer cell, with all else unchanged. They were frozen with new locks citing the owner decision and source review; the v1 references, locks and scores are retained. The scorer gained support for a list of accepted printed forms, which leaves single-value references unchanged. A new rescoring tool reuses hash-checked copies of predictions without touching the original batch. Against v2, Opus scores raw 74 / 75 and workbook 80 / 81, and Sonnet v3.1 scores 75 / 75 and 81 / 81, published as a supplement. The normalization prompt is not yet written: which printed form the workbook should prefer is an open owner decision. No commit or push was performed.

### 2026-10-10 — Anthropic 0.3.11: quiet pre-reply wait and one printed Payer form

Following the owner's decisions, two rules went into shared core. Until the user answers the policy question, the agent must not list folders or open files outside the skill, including custom.md and the company profile, because file names can be confidential. When a cheque prints the drawer twice, Payer takes the account-holder line exactly as printed and quotes the other form in a note. The evaluation checker for Claude chats (`claude-layout-v2`) now accepts the question in bold and one closing sentence without a question mark after the verbatim choices. The Codex checker and historical contracts are unchanged.

Both family packages were rebuilt as 0.3.11 because core changed. Only Anthropic was evaluated (`322d6393…`); OpenAI 0.3.11 (`a418b467…`) is unevaluated. The core changelog had no 0.3.10 entry; the 0.3.11 entry notes this rather than inventing one.

Private references were re-frozen for 0.3.11 in two forms: accepting both printed Payer forms, and strict account-holder-only for rule compliance. 78 new chats completed: 27 public and 12 private per model. The owner gave a new reply for the 24 new private chats.

| Model | Public | Fox raw | Fox workbook | Fox documents | Payer rule |
|---|---|---|---|---|---|
| Opus | 27 / 27, all correct | 73 / 77 | 78 / 82 | 14 / 15 + 1 extra | 9 / 9 |
| Sonnet | 27 / 27, all correct | 74 / 75 | 80 / 81 | 15 / 15 | 9 / 9 |

Opus's Fox shortfall is one run that typed a same-page cash sale as "Cash memo" instead of Invoice, against the 0.3.7 rule. Sonnet's is one flagged unclear Total. Both kept 6 / 6 unclear values blank and filled no blank-expected values. The new pre-reply rule worked for Opus (0 / 39 breaches) but not for Sonnet (19 / 39), which read the rule and still listed the folder; this needs another iteration. These are known synthetic cases and four reused pages, not general accuracy. No commit or push was performed.

### 2026-10-11 — OpenAI 0.3.12: load classification mapping before each batch

The owner requested a fix for Cash Memo being classified as Receipt, a new model evaluation of the same Fox page, and confirmation that the previously adjudicated amount remains correct. No commit was authorized. The earlier 0.3.10 trace had not read the shared document-type mapping; that mapping already correctly treats a sale-recording Cash Memo as Invoice. The OpenAI entry now requires reading it before classification, even for familiar titles, and says payment status alone does not determine type. No source-specific values or title-to-type postprocessing were added.

Only the OpenAI family advances to 0.3.12. It inherits shared core 0.3.11, so a comparison with 0.3.10 is not an isolated test of this routing sentence. Anthropic remains 0.3.11 with identical package bytes. Three frozen public controls distinguish a paid Cash Memo, a genuine payment acknowledgement and a Tax Invoice / Receipt. Supplied-transcription checks pass raw 9 / 9 and workbook 17 / 17; all three injected wrong classifications remain visible. All 186 unit/regression tests and generated-package checks pass. These local results do not establish model recognition accuracy.

A fresh requested gpt-6.1-sol Codex session was opened on the public controls. The owner supplied an actual new policy reply for that exact session. Its opening asked once and only read skill instructions, with unchanged workspace; the automatic layout audit remains invalid because of explanatory trailing prose and combined instruction reads. A hash-bound maintainer review records the observed pause without changing that automatic score. The private known-source regression was separately frozen against the new package, with the old source, custom settings and mixed owner/provisional references unchanged. Live extraction results are pending.

The live evaluation is now complete. Public classifications pass 3 / 3, raw 9 / 9 and workbook 17 / 17. The private page keeps both documents as Invoice and reads the owner-confirmed target Total correctly in raw and Excel. It scores strict raw 4 / 5 and workbook 7 / 7, excluding three correct blanks per layer. The only raw mismatch is a currency prefix present in the prediction but absent from the frozen reference. Maintainer visual review finds a source currency mark before the total; digits and terminal dash agree. This is documented separately without modifying the reference, owner-review scope or strict score. The covered requested number stays unclear and blank (1 / 1). Handwritten dash processing remains positive without a confirmation or global override.

Each case completed once, without retry: public 151.61 seconds; private 211.94 seconds. The same new session did the public controls first, so the private result is not an independent fresh-chat trial. The private trace reads document-types.md and returns images on three image calls. Requested model remains gpt-6.1-sol; reported identity is Unknown. No policy question repeats after the actual reply. Published the [aggregate report and matrix](evaluations/2026-10-11-openai-0.3.12-cash-memo.md); earlier reports and outputs are preserved. The changed package remains experimental, with no general handwriting or repeatability claim. No commit or push.

### 2026-10-11 — Prepare three direct fresh-chat Fox repeats on unchanged OpenAI 0.3.12

The owner requested three new chats directly on the same authorized Fox page, without a public example first, to test Cash Memo classification and the previously adjudicated target amount. The package remains byte-identical to the preceding 0.3.12 evaluation. Added an explicit `conversation.py start-private` benchmark entry that verifies an existing frozen private case, prepares an isolated workspace with no answers and opens a new session directly on that source. The ordinary public start remains separate. Each private chat requires its own actual policy reply; scripted replies are rejected and the package/lock are rechecked before extraction.

Three new sessions have reached their first policy question. Each asks it once and reads only the skill instructions before waiting. Their automatic opening layout remains invalid because of explanatory suffixes/combined instruction reads; separate hash-bound reviews retain the observed wait. At this preparation stage no PDF reading has begun. Three session-specific reply questions were presented to the owner. All 189 local tests pass, including the direct-start and rejected-scripted-reply cases. The three-run plan, exact source/package/reference hashes and primary/supplemental scoring definitions were frozen before extraction. Results remain pending; this preparation is not recognition evidence. No commit or push.

### 2026-10-11 — Anthropic 0.3.12/0.3.13 opening fixes, usage-limit failures and reruns

Sonnet kept listing the folder before the policy reply after reading the shared rule. The owner chose a family-prompt fix (0.3.12): before a reply the only allowed tool call is reading the skill's references. The owner also chose to fix Sonnet's shortened or extra reply choices (0.3.13: offer exactly the two choices word for word). Both changes are in `skills/anthropic/SKILL.md`; shared core and OpenAI 0.3.11 are unchanged.

The checker for Claude chats (`claude-layout-v3.1`) automatically accepts a short announcement naming the skill (no question, no completed-work claim), bold around the question or choices, one lead-in line and one closing sentence. Choice wording must stay verbatim. CLI `<synthetic>` notices are now labelled transport errors instead of model mismatches; they still fail the execution.

The account reached its usage limit during 0.3.12 private runs (20 failed) and the first 0.3.13 attempt (54 public and 24 private openings failed). All are kept as failures. The owner chose a full rerun. One 0.3.13 Opus public run failed on a dropped connection. The evaluator briefly saved the runner with a syntax error, so the first relay of five Sonnet private replies failed before any CLI call; the same owner reply was delivered later, and this is recorded.

0.3.13 results:

| Model | Public | Fox raw | Fox workbook | Opening |
|---|---|---|---|---|
| Sonnet | 27 / 27 valid, all correct | 74 / 75 | 81 / 81 | No pre-reply tools and verbatim choices in 39 / 39 chats |
| Opus | 26 / 27 valid, all correct | 73 / 75 | 80 / 81 | 39 / 39 verbatim |

Both had 15 / 15 Fox documents, 6 / 6 unclear values kept blank and the account-holder Payer line on every cheque run. These are known fixtures and four reused pages, not general accuracy; the package remains experimental.

The owner supplied three actual policy replies, one for each waiting session. All three direct extractions then completed once, with no public examples, retry, prompt change or replacement run. Cash Memo is Invoice in 3 / 3, but the target Total is correct in only 2 / 3 in raw and Excel. Run 1 repeated the extra-leading-digit error and wrote it into Excel; its Total was not marked unclear in raw. The processor general handwriting warning yields a workbook wrong_flagged score, not successful detection or rejection of the numeral error. Run 2 has only the known currency-prefix raw mismatch; run 3 passes all configured checks.

Strict scores are raw 13 / 15 and workbook 20 / 21, excluding nine correct blanks per layer. Owner-confirmed cells score raw 4 / 6 and workbook 11 / 12; provisional nonblank cells score 9 / 9 in each layer. All six document records and classifications are correct, and all three predeclared covered observations stay unclear and blank. Two of eight configured raw cells vary across sessions; one of ten workbook cells varies. The sessions took 223.86, 225.73 and 223.12 seconds and returned image content on 2, 2 and 3 image calls respectively. All read the document-type reference. These observations do not establish the cause of the recognition variation.

Published the [three-direct-repeat report](evaluations/2026-10-11-openai-0.3.12-direct-fox-repeats.md), JSON and CSV, and added the newer result prominently to README. The preceding single-run report remains unchanged. These are three fresh sessions on one reused page, not a general handwriting accuracy estimate. Classification is consistent within this sample; the target reading is not stable. The unchanged 0.3.12 package remains experimental. No commit or push.

### 2026-10-11 — OpenAI 0.3.13: local handwritten-token verification before acceptance

The owner requested a reusable prompt improvement for the recurring extra-leading-digit error, followed by three fresh chats directly on the same Fox page, with no answer hardcoding and no commit. In the earlier 0.3.12 direct repeats, both a correct and an incorrect run inspected an original page and an upright whole-page render; rotation alone does not distinguish success. This observation motivates a local inspection step but does not prove the cause of the error.

The OpenAI entry now routes handwritten amounts and requested numeric measurements to handwritten-numbers.md before acceptance, including initially confident readings. The reference calls for a local enlarged amount-block view retaining labels, complete tokens, nearby rules and adjacent rows; tracing questionable strokes across that context; retaining genuine digits; and recording first/local readings plus visual boundary evidence in the reading ledger. Unresolved complete values remain blank and unclear. Repeated amounts, arithmetic and a generic handwriting warning cannot justify an unresolved token. The reference states that these are two views read by the same model, not independent verification. It includes no expected amount, supplier, source-specific coordinate or rule that prefers fewer digits.

Only OpenAI changes to 0.3.13. Shared core/runtime are unchanged and the concurrently completed Anthropic 0.3.13 package is byte-identical before/after the build. All 190 current unit/regression tests, package/link checks and skill validation pass. The three new direct-private sessions have their own actual owner replies, identical frozen source/custom/answers and the new package hash. No public examples or prior answers are passed to them. Opening repeat 1 asks the policy question twice; repeats 2 and 3 ask once. All observed only skill reads and waited before document work; automatic layout failures remain recorded. Extraction results are pending. No commit or push.

The three new extractions are complete, each once with no retry or replacement. Target Total is correct in raw and Excel in 3 / 3, and Cash Memo remains Invoice in 3 / 3. Strict scores are raw 14 / 15 and workbook 20 / 21, excluding nine correct blanks per layer. Runs 1 and 2 pass all configured checks. Run 3 deliberately marks the neighbouring Cash Memo Total unclear and omits it because a crossed leading mark remains ambiguous to the model; this is scored as a missed readable reference, not a correct abstention. The separate line amount was not substituted. All six document records/classifications remain correct, and all three predeclared covered requested values stay blank.

All three traces read the new reference and request local target views that return image content. Maintainer inspection confirms the crops retain labels, full tokens and nearby rows/rules. All ledgers record first/local readings and boundary reasons; all initial target readings were already correct. Thus these traces do not demonstrate correction of a wrong initial reading or establish causality. They show the new procedure being used alongside correct target readings. Two views read by the same model are not independent verification.

The [new report and accuracy matrix](evaluations/2026-10-11-openai-0.3.13-direct-fox-repeats.md) compare the three runs with preserved 0.3.12 results. Target correctness improves from 2 / 3 to 3 / 3 in this sample; aggregate workbook accuracy stays 20 / 21, with a missed neighbouring amount replacing the prior sample's wrong target value. Owner-confirmed cells score raw 5 / 6 and workbook 11 / 12; provisional nonblank cells score 9 / 9 in each layer. The only varying scored value is the neighbouring Total. These are three repeats of one reused page, not an unseen holdout; genuine-leading-digit and broader cases were not live-tested on the changed package. Opening question counts are 2, 1, 1, with no repeats after replies and original automatic format failures retained. No prompt change was made after execution, and no commit or push.

### 2026-10-11 — Primary design targets: Gemini, Grok and ChatGPT

The owner changed the design focus to Gemini, Grok and ChatGPT. README now leads with these three targets and distinguishes their planned capabilities from current packages. The architecture retains one prompt per provider family: `google` for Gemini, `xai` for Grok and `openai` for ChatGPT. Model versions do not create maintained prompt forks, and recommendations never switch the user's model.

The existing OpenAI prompt, core contracts, PDF routes and evaluator remain reusable. Google/xAI sources and the three application adapters are planned work, not newly shipped packages. Codex execution evidence does not qualify ChatGPT application behaviour. Model recommendations for the two new families remain pending; their application/account policy guidance must be established before release. This change neither runs a model evaluation nor authorizes sending Fox documents to a new provider.

Claude/Anthropic packages and reports are retained as secondary support. Cursor/Copilot adapter work is deferred behind the three primary targets. The documented implementation sequence is application capability contracts, family prompts/adapters, then comparable fresh-chat evaluations using frozen public references. Current registry versions, generated package bytes and historical results are unchanged by this design update. No commit or push.

### 2026-10-11 — CLI delivery selected for all three primary targets

The owner selected CLI delivery. This resolves the preceding application-versus-CLI question: Gemini uses Gemini CLI, Grok uses Grok Build CLI, and ChatGPT/OpenAI uses the existing Codex CLI route. Browser/mobile adapters leave the current scope. Official documentation reviewed today is linked in the architecture's CLI integration contract; it establishes available CLI interfaces, not completed repository integration.

Reuse the OpenAI prompt, Codex adapter, staged evaluator and historical evidence. Plan `skills/google/` with `adapters/gemini-cli/` and `skills/xai/` with `adapters/grok-build/`. Keep one extraction schema, local workbook processor and scoring implementation. The two new adapters must verify skill loading, local PDF/image access, available Python/OCR, workbook writing, exact-session resume and event capture before model accuracy runs. No new API agent loop is required by this decision.

CLI execution does not imply offline inference or API-account policy. Record the actual authentication/provider route and retain the once-per-chat policy reply workflow in headless runs. New provider policy references and Gemini/Grok recommended models remain pending. No software was installed, no authentication was changed, no private document was sent, and no new model evaluation was run for this design update. Registry/package versions and generated package contents remain unchanged; no commit or push.

### 2026-10-11 — Complete local CLI previews and OpenAI public repeat evaluation

The owner asked to complete the work possible here. Added Google and xAI family prompts, CLI operation/policy references, registered 0.1.0 previews and preparation-only adapters. Generated packages reuse core 0.3.11; no separate processor or model override was introduced. Gemini uses explicit file-path loading outside discovery directories until a native manual-only integration is verified. Grok uses its documented disable-model-invocation flag. The builder rejects unknown invocation formats and automatic file-path adapters, and displays undecided recommendations as Pending evaluation. Both previews prepared the public payment and energy scenarios locally, without a provider call or copying answers into model workspaces. Anthropic's package remains byte-identical (`42e4d09398ee2f4acb3fb4d4650147c1c4d79944e04683ef338a95a4a6725483`).

OpenAI advances to 0.3.14 only for its opening: both exact replies are in the entry, the question uses one channel, and document work waits for the reply. Extraction instructions are unchanged. Added public_repeats.py with frozen public-only plans, one-time trial reservation, labelled scripted read-later responses, separate opening/extraction scoring, and exact-session continuation after hash-bound maintainer trace review. The original failure/audit stays visible. Added read-only CLI readiness discovery and fixed UTF-8 decoding of the Codex version diagnostic.

The frozen public plan contains four scenarios with three fresh chats each. The first digit-boundary trial failed before session creation because the local sandbox denied Codex's session-directory write; it was not replaced. Later trials used the existing Codex authentication/session storage through approved execution. All 11 started sessions completed valid extractions. Cash Memo classification scores raw 27 / 27 and workbook 51 / 51 across three repeats; digit-boundary scores raw 26 / 26 and workbook 30 / 30 across two valid repeats; OCR-layer payment and energy purposes score workbook 63 / 63 and 75 / 75 across three repeats each. Aggregate workbook is 219 / 219, excluding 93 correct blanks. Configured raw is 53 / 53, excluding four correct blanks; coal raw scoring is not configured. No scored workbook value varies between valid repeats.

All 11 started chats ask exactly once and never repeat after the scripted reply. Strict automatic opening results remain ten invalid and one requires_review. Four combined instruction reads needed maintainer trace review before continuation; no source-document work was observed in those openings. All original results remain preserved. The CLI stream does not independently prove image viewing, and these are known synthetic sources, not unseen or human-handwritten evidence. No new Fox evaluation was run and no old score was changed.

Published the [0.3.14 CLI report](evaluations/2026-10-11-openai-0.3.14-cli-public.md), JSON and CSV, plus a [CLI smoke-test handoff](cli-smoke-tests.md). All 199 local tests and package/link checks pass. OpenAI/Gemini packages and xAI source pass the Codex skill validator; generated Grok includes a documented Grok-only field that this validator rejects, retained and checked through repository packaging tests. Local probes find Codex, usable Python/PDF rendering and no Tesseract on the probed route; Gemini/Grok are not found on PATH and their authentication was not checked. No third-party software was installed, no private material sent, no account settings changed, and no commit/push. Remaining work needs target-CLI verification, selected model/account access, live adapters/evals and opening-format qualification; no package is promoted.

### 2026-10-11 — OpenAI-only MVP and public-repository readiness

The owner selected ChatGPT / OpenAI for the MVP and deferred Gemini and Grok to the next phase. The prior CLI decision remains in force: delivery is the existing Codex CLI package, including ChatGPT sign-in, not a new browser/mobile integration. Retain the Google/xAI previews and Anthropic evidence without treating their pending integration as an OpenAI MVP blocker. No prompt, package version, recommendation or evaluation result changes in this scope update.

README now leads with the OpenAI package, installation and use before detailed evaluation history. Earlier results remain visible in an expandable section. Architecture and the CLI handoff record the revised sequence. Git ignore rules now cover the default run folder and root-level custom settings, company profile and output workbook; arbitrary user filenames still need review before staging.

A working-tree inventory found 484 publishable files before this documentation update, no files larger than 5 MB, no tracked files in ignored eval run/raw directories, and no matches for the checked common credential formats or known private source names in scanned text files. This limited scan is not a complete secret or Git-history audit. Apache-2.0 licensing and local tests/evaluation evidence are present. No GitHub Actions workflow is present. A separate clean-install smoke test remains outstanding; existing evaluations used prepared environments. Public experimental source sharing is reasonable with these limitations stated; a stable release or full workflow qualification is not supported by the current evidence. No commit or push.

Validation after the scope/documentation changes: all 199 local tests pass, generated-package/registry checks pass, changed documentation has no missing local file links, and default workspace outputs match the new ignore rules. No live model evaluation was rerun.

### 2026-10-11 — Clean installation and pre-publication review

The owner authorized a commit and push once clean-install and publishable-file/history checks pass. A copied OpenAI 0.3.14 package ran in a new document workspace with a fresh uv cache and PDF virtual environment, using no repository development dependencies for its runtime. The first dependency download failed on sandbox DNS restrictions; approved network access resolved it. Installed setup, custom settings, manifest creation, PDF preparation and workbook processing all completed. The current agent inspected and transcribed the known synthetic invoice; this was not a fresh-chat or blind accuracy evaluation. All 16 integration checks pass, with one processed document, three line items, zero unprocessed inputs and the expected missing-profile direction review. Installed package and source hashes are unchanged.

README now includes explicit optional PDF dependency setup. The [release-readiness report](evaluations/2026-10-11-openai-0.3.14-release-readiness.md) and JSON record the scope, versions, checks and limits. After fetching origin, the initial release inventory covered 484 publishable files and all locally reachable history (9 commits, 443 blobs); PDF text and XLSX contents were also scanned. Three path-pattern hits were scanner definitions, manually cleared. The 14 distinct PDFs contain 25 reviewed synthetic pages; the two answer-key versions contain invented fixture data. No unresolved secret/private-source finding or tracked private run output was identified. No history rewrite is needed. Final staged checks precede the authorized normal commit/push to main; no tag, force push or model qualification is implied.

The final working inventory including the readiness report/JSON contains 486 files, with the same cleared findings and no decoding errors. All 199 regression tests were rerun successfully; package/registry consistency, documentation links and whitespace checks pass. The OpenAI package remains experimental with its earlier opening-format and handwriting limitations unchanged.

### 2026-10-11 — Three fresh first-use chats and versioned evaluation corrections

The owner requested the next two MVP steps: three new chats exercising the complete user workflow and corrections to evaluation scoring/reporting, without committing. Added the public `first-use-v1` protocol and runner. Three fresh Codex CLI sessions began outside the repository with only the installed 0.3.14 skill and synthetic OCR-layer PDF. Plain-language payment/energy requirements replaced prefilled custom.md; no company profile, extraction, page images or answer files were installed. Package, sources and two-purpose references were frozen before execution. Each action was reserved once, with no retries or replacement results. Existing host tools/authentication/global context remained available, so this is not a pristine operating-system test.

All three chats read the installed instructions, asked the exact policy question with both choices and waited. Each then received the labelled public read-later fixture; this records scripted response handling, not human consent. All created custom.md, recovered from local PDF dependency incompatibility, read the PDF and produced Excel without evaluator edits to their artifacts. Initial results are raw 50 / 50 and workbook 67 / 67, excluding 51 / 43 correct blanks. Chat 1 processed a scan-format second batch in the same session, retaining byte-identical settings and its earlier workbook, and without another policy question. Across all four batches: raw 65 / 65, workbook 88 / 88, excluding 68 / 57 correct blanks. All eight expected document records are present, but reuse the same two-document business content. Missing moisture stays blank; sample values/units/labels and the inconsistent printed total are preserved. Requested model was gpt-6.1-sol via existing Codex ChatGPT login; runtime identity remains Unknown.

Added `workflow-audit-v2` to distinguish exact question/options, observable waiting and opening format. Markdown and static combined installed-instruction reads no longer trigger false failures; additional prose still requires review. All three new chats retain legacy invalid results and v2 requires_review format outcomes, alongside 3 / 3 exact question/options and observed pauses. Re-auditing the previous public batch preserves its original 10 invalid / 1 requires_review and startup failure; v2 finds 11 / 11 exact question/options and observed pauses, with all 11 still requiring format review. No historical field score or reference was rewritten.

New raw references cover the payment and energy purposes. Raw scoring optionally maps model-chosen custom keys to the exact user-requested labels; incorrect labels still fail and earlier key-based cases are unchanged. Image evidence is now obtained from actual image-tool returns in exact-session traces, not agent-authored ledgers. Each batch has two returned images; same-session follow-up counts new calls only. Missing evidence is not inferred. Returned pixels do not establish model attention or general reading accuracy.

Published the [first-use report](evaluations/2026-10-11-openai-0.3.14-first-use.md), JSON/CSV, protocol documentation and README update. Execution harness hashes remain frozen; subsequent UTF-8/reporting and conservative command-wrapper checks are evaluator-only changes. Final audit results match all three saved opening observations. All **211 local tests** pass, including label mismatch, unexecuted report, output preservation, exact-option and tool-evidence regressions; generated-package/registry and whitespace checks pass. OpenAI package/prompt stays byte-identical at 0.3.14 and experimental. No private Fox files were used; no commit or push.

### 2026-10-11 — OpenAI 0.3.15: concise opening and one permitted host explanation

The owner requested removal of extra opening text, three new test chats and updated reports without committing. Inspecting the earlier traces found a host base instruction requiring a linked explanation whenever a skill pauses for a reply. The OpenAI entry now gives the exact short announcement and excludes discretionary headings, task recaps, setup plans and closing sentences. It preserves the exact question/options, wait-for-reply behaviour and higher-priority host requirements, allowing only a brief necessary disclosure. OpenAI advances to 0.3.15; extraction guidance, shared runtime/references and other family packages are unchanged. Generated OpenAI package hash is dbadd0982cb76f54bcbe2b2141996a6ead202878c0854de591c225fd8b75f7b2.

Three fresh Codex CLI sessions used new external workspaces and the existing first-use-v1 public protocol, requested gpt-6.1-sol through the existing ChatGPT login. All use the exact short announcement and exact question/options, wait with only installed-instruction reads and still include one source-linked waiting explanation. The host disclosure rule is independently present in all three captured session metadata records. Strict v2 format remains requires_review in 3 / 3; the prompt alone has not removed the required disclosure.

After seeing that result, the owner explicitly approved one necessary Codex explanation and source link with a new format contract. Added codex-opening-v3 and a supplementary review tool: exact ordered question/options, at most one recognised waiting explanation, a link confined to the installed skill entry or chat-start reference, matching-session host-rule evidence, and observed waiting. Repeated confirmation, Yes-only conditions, unrelated links, multiple explanations and unknown wording do not automatically pass. It judges the permitted opening format, not every detail of host-instruction compliance. All three openings pass v3; original v2/legacy results remain untouched. Reports explicitly label this as retrospective grading because v3 was approved after observing those openings. New plans now freeze v3 and its grader hash in advance and reject changed grader files before continuation.

All three chats complete custom.md creation, PDF processing and Excel output without evaluator edits. Initial totals: raw 50 / 50, workbook 67 / 67, excluding 51 / 43 correct blanks. Chat 1 completes its second scan batch in the exact session, retaining byte-identical settings and its first workbook, without repeating the policy question. Four-batch totals: raw 65 / 65, workbook 88 / 88, excluding 68 / 57 correct blanks. All eight expected document records are present; they reuse the same synthetic content. Four batches return two new images each through actual image-tool outputs. No private Fox material was used. Runtime model identity remains Unknown; requested identity is not verified.

Published the [0.3.15 report](evaluations/2026-10-11-openai-0.3.15-first-use.md), extraction JSON/CSV and separate v3 opening JSON/CSV; updated README and evaluation/protocol documentation. Extraction scores match 0.3.14 in this narrow sample. All **218 local tests** pass, including six new format/evidence tests and a frozen-grader drift test. Skill validation, package/registry consistency and final report/link/whitespace checks pass. Broader unseen/handwritten and prospectively frozen v3 confirmation remain future evidence, not completed claims. Package remains experimental. No commit or push.

### 2026-10-11 — Prospective 0.3.15/v3 confirmation: opening acceptance not stable

The owner requested three more fresh chats using the already approved opening grader, with no commit. Froze the unchanged 0.3.15 package, codex-opening-v3 hash, prompts, public sources, references and seven harness files before launching three new Codex CLI sessions in new external workspaces. Archived the execution harness. Requested model remained gpt-6.1-sol through the existing OpenAI ChatGPT login; runtime identity remains Unknown. The public first-use protocol still has two initial payment trials, one energy trial and a same-chat scan follow-up in chat 1. Nothing was retried, replaced or edited to fit an answer.

Automatic v3 opening acceptance is **0 / 3**, with all three requires_review. Exact question/options, ordered choices, fixed short announcement and observed pause all pass **3 / 3**. Each has one relevant source-linked waiting explanation, but wording such as require me to and labels such as skill's first-response rule fall outside the unchanged recogniser's narrow grammar. The host disclosure requirement is present in each exact-session trace. Manual inspection is recorded separately and does not overwrite automatic grades. This prospective outcome does not confirm the earlier retrospectively graded 3 / 3 result; it exposes a grading-coverage limitation without demonstrating missing questions, premature processing or extra approval requests.

All three initial extractions complete with raw **50 / 50** and workbook **67 / 67**, excluding **51 / 43** correct blanks. The scan follow-up completes in the same session with byte-identical custom.md and an unchanged first workbook. No post-reply turn repeats the policy question. Four-batch totals are raw **65 / 65**, workbook **88 / 88**, excluding **68 / 57** correct blanks; all eight expected records are present, reusing the same invoice/certificate content. The two initial payment trials have zero differing cells among 32 raw and 35 workbook scored-value entries; those consistency comparisons include blanks and do not inflate accuracy denominators. Each batch returns two new images through image-tool output. No Fox/private material is used.

Published the [prospective confirmation report](evaluations/2026-10-11-openai-0.3.15-v3-confirmation.md), extraction JSON/CSV and opening JSON/CSV; README now leads with the unconfirmed opening stability rather than the earlier retrospective pass. Prompt, runtime, grader, references and original reports remain unchanged. Final checks verify frozen hashes, stored/recomputed grades, JSON/CSV totals, links, package/registry consistency and whitespace. No local test code changed, so the previous 218-test result is retained as historical validation rather than rerun. The next coding step is broader disclosure recognition under the approved one-line format, tested against positive and negative cases and frozen before another independent batch. No commit or push.

### 2026-10-11 — V4 paraphrase recogniser, guarded negatives and fresh 0.3.15 tests

The owner requested broader recognition of necessary waiting explanations while retaining extra-confirmation and Yes-only rejection, followed by three fresh chats under a frozen new grader, without committing. Added codex-opening-v4; v3 and the installed 0.3.15 package remain byte-identical. V4 separates visible explanation text from its link target, validates the installed skill entry/chat-start source and matching-session host requirement, and recognises bounded complete waiting clauses with quotation/punctuation and source-label variants. It handles require me to, says to, instruct me to, according to and as required by forms. Negative guards and full-clause matching retain review for extra confirmation, Yes-only conditions, unrelated appended actions, multiple explanations or unknown structure. Directory names containing confirmation are not treated as visible user instructions.

Before model execution, all **227 local tests** pass. Authored grading cases accept **12 / 12** valid paraphrases and reject **18 / 18** invalid conditions plus **48 / 48** appended-requirement variants. Added dependency-drift and report-version tests. New plans freeze v4 and its dependencies and reject changes before continuation; the report tool defaults to each plan's own contract and marks explicit cross-version rescoring retrospective. These are deterministic grading tests, not model accuracy evidence.

Froze and archived the 0.3.15 package, v4 hash 68bbcd1bea77397d2126f1edc423f283281c22150a1c1cf7cc9678bb2453d974, v3/workflow dependencies, references, prompts and eight harness files before three new external-workspace Codex CLI chats. Requested model remains gpt-6.1-sol through existing OpenAI ChatGPT login; runtime identity stays Unknown. One attempt per action, no replacement, no private Fox files, and no prompt/grammar changes after seeing the outputs.

On the three new openings, v4 automatically passes **1 / 3** while unchanged v3 passes **0 / 3** on those same outputs. Exact question/options, fixed short announcement and observed waiting pass **3 / 3**. One explanation uses require this pause plus an after asking quote; another adds a second explanatory sentence after quoting the rule. Both remain unsupported_explanation/requires_review under the frozen grammar. The third source-label/require me to quotation now passes. No extra confirmation or Yes-only demand was observed in the live openings. This demonstrates a limited recognition improvement, not stable full acceptance or justification for changing the frozen results.

All three initial extractions complete without evaluator edits: raw **50 / 50**, workbook **67 / 67**, excluding **51 / 43** correct blanks. Both payment trials have identical scored values (zero varying cells among 32 raw/35 workbook entries, including blanks only for that consistency comparison). The same-session scan follow-up also completes, retaining byte-identical custom.md and previous outputs with no repeated policy question. Four-batch totals are raw **65 / 65**, workbook **88 / 88**, excluding **68 / 57** correct blanks. All eight expected records are present, reusing the same synthetic content; each batch returns two new page images. The [v4 report](evaluations/2026-10-11-openai-0.3.15-v4-confirmation.md), extraction/opening JSON and CSV, and deterministic grading matrix preserve all diagnostics and distinguish opening recognition from extraction accuracy. No commit or push.

Final checks confirm frozen package/reference/harness/test hashes, saved opening grades and report hashes, JSON/CSV fields and totals, all 78 deterministic case results and 86 local documentation links. Package/registry consistency and whitespace checks pass. The 227 tests were run on the final code before freezing; later edits only complete reports and documentation.


### 2026-10-11 — V5 quoted rule plus application; opening acceptance not stable

The owner requested support for a quoted rule followed by one explanation clause, preserving extra-confirmation and Yes-only rejection, then three fresh 0.3.15 chats without committing. Added codex-opening-v5, retaining byte-identical v3/v4 and package sources. V5 first applies v4 source/visible-text protections, then independently matches the quoted waiting rule and optional bounded application clause. Unknown conditions, unrelated actions and a third sentence remain reviewable. New plans freeze v5 plus v3/v4/workflow-audit dependencies; old plans retain their original dependency set. Stored results and reports preserve every applicable grader version.

The full suite passes 238 tests; 21 affected tests pass again after a final grammar simplification, before freezing. Authored fixtures accept 20 / 20 valid forms and reject 31 / 31 invalid forms plus 120 / 120 appended-requirement variants. Froze v5 hash 937ac85106f99bc411b836b4006cdd9c5cccc72ad31102829dbe933672dfd0c9 and unchanged package hash dbadd0982cb76f54bcbe2b2141996a6ead202878c0854de591c225fd8b75f7b2, nine harness files, sources, references and prompts before calls; archived the harness and four test files. Requested gpt-6.1-sol through existing OpenAI ChatGPT login; runtime identity Unknown.

Three fresh external-workspace CLI chats preserve exact question/options, order, announcement and observed waiting in 3 / 3. Automatic v5 acceptance is 2 / 3, identical to v4 on those same outputs. The remaining explanation puts the application before its quotation and remains unsupported_explanation. Neither fresh passing output exercises the new parser branch. A separate, explicitly retrospective v5 rescore of the previous v4 batch accepts 3 / 3 (original v4: 1 / 3); these known development examples do not establish independent improvement. No outputs, prompt or grammar were changed after seeing the new results. Public synthetic fixtures only; no Fox/private inputs. See the [v5 evaluation](evaluations/2026-10-11-openai-0.3.15-v5-confirmation.md). No commit or push.


All three initial extractions and the same-session scan follow-up complete without evaluator edits: raw 65 / 65 and workbook 88 / 88, excluding 68 / 57 correct blanks. Initial-only totals are 50 / 50 and 67 / 67. All eight expected records are present, reusing the same synthetic content; two new page images are returned per batch. The two initial payment chats have zero varying scored-value cells among 32 raw and 35 workbook entries, with blanks included only for consistency. The scan follow-up preserves custom.md and prior outputs, processes only the requested new PDF and does not repeat the policy question. Published extraction/opening JSON and CSV, deterministic matrix and separate retrospective grades; updated README and protocol/evaluation guidance. No commit or push.

Final validation passes: frozen package/reference/harness/test hashes, saved and recomputed opening grades, result/trace/workbook hashes, four-batch totals, three JSON/CSV pairs, 171 matrix cases and 89 local links. Package/registry consistency and whitespace checks pass; all changes after freezing are documentation/reporting artifacts.


### 2026-10-11 — V6 application before quotation; source-link spelling remains reviewable

The owner requested support for an explanation preceding a quoted rule, with extra-confirmation/Yes-only rejection retained, then three fresh 0.3.15 chats and no commit. V6 validates the entire leading source-linked application using preserved v4 grammar, then the entire quoted waiting rule using preserved v5 grammar. Both clauses must pass; quotes do not exempt unsafe conditions. The original source-target case is preserved. Source/host/order/waiting checks remain intact; unknown forms and extra clauses remain reviewable. Historical v3/v4/v5 files and the 0.3.15 package are byte-identical.

All 252 tests pass before freezing. Authored grading fixtures pass 28 / 28 acceptable forms, 43 / 43 rejected forms and 168 / 168 appended-condition variants. New plans freeze v6 and v3/v4/v5/workflow-audit dependencies; historical plans retain their own set. Froze v6 hash 3b96566757cd337605e2cc4238f1db8a649dab89097d3c91cff242aa625dd426, unchanged package hash dbadd0982cb76f54bcbe2b2141996a6ead202878c0854de591c225fd8b75f7b2, sources, references, prompts and ten execution files, then archived the harness and five test files. Requested gpt-6.1-sol via existing OpenAI ChatGPT login; runtime identity Unknown.

Three fresh public CLI chats preserve exact question/options, order, announcement and observed waiting in 3 / 3. V6 automatically accepts 2 / 3, identical to v5 on the same outputs. Chat 1 uses /C:/... for the installed source link; the unchanged source resolver reports unrelated_source. This is an unsupported path spelling, not evidence of a private upload or missing policy question. Neither passing fresh output exercises the new branch. A separate retrospective v6 rescore of the previous known v5 batch accepts 3 / 3 versus the original frozen v5 2 / 3. No mid-batch prompt, grammar or score changes. Public synthetic files only; no Fox/private material. The [v6 report](evaluations/2026-10-11-openai-0.3.15-v6-confirmation.md) keeps these evidence types separate. No commit or push.


All three initial extractions and the same-session scan follow-up complete without evaluator edits. Initial scores are raw 50 / 50 and workbook 67 / 67; four-batch totals are 65 / 65 and 88 / 88, excluding 68 / 57 correct blanks. All eight expected document records are present, reusing the same content; each batch returns two new page images. The two payment chats have zero varying scored-value cells among 32 raw and 35 workbook entries, with blanks included only for consistency. The follow-up retains custom.md and earlier outputs, processes only the new scan input and does not repeat the policy question. Published extraction/opening JSON and CSV, deterministic matrix and separate retrospective scores; README and evaluation/protocol guidance are updated. No commit or push.

Final validation passes for frozen package/reference/dependency/harness/test hashes, saved/recomputed grades, result/trace/workbook hashes, four-batch totals, three JSON/CSV pairs, all 239 deterministic cases and 91 local links. Package/registry and whitespace checks pass. Only reports/documentation changed after the freeze.


### 2026-10-11 — V7 slash-drive source aliases with exact path validation

The owner requested /C:/... source-link support, preservation of path safety and extra-confirmation/Yes-only rejection, then three fresh 0.3.15 chats without committing. V7 removes exactly one slash before an absolute drive prefix on Windows, resolves the target and matches only the installed SKILL.md or references/chat-start.md. It rejects traversal, foreign files/chats/drives, UNC/device paths, drive-relative names, alternate streams, encoded paths, controls, queries and ambiguous trailing segments. Installed-root redirection and final-target escape are rejected; deterministic tests simulate OS-resolved symlink/junction destinations without needing link privileges. Only the target is canonicalised internally; original evidence and visible-text guards remain unchanged. V3 through v6 and package 0.3.15 stay byte-identical.

All 269 local tests pass before freezing. The Windows grading matrix passes 16 / 16 accepted path spellings and 28 / 28 rejected paths; 28 accepted paraphrases, 43 rejected conditions and 168 appended requirements each pass with both relative and slash-drive links, totalling 522 authored cases. New plans freeze v7 plus v3/v4/v5/v6/workflow-audit dependencies; old plans retain their declared dependency sets. Froze v7 hash 52528d96f3a74f058d9fb3147282b53bc2b89cd4c83218727a556848c3ca154f, unchanged package hash dbadd0982cb76f54bcbe2b2141996a6ead202878c0854de591c225fd8b75f7b2, references, sources, prompts and eleven execution files; archived the harness and six test files before calls. Requested gpt-6.1-sol through existing OpenAI ChatGPT login; runtime identity Unknown.

Three fresh public CLI chats pass exact question/options, order, announcement and observed waiting in 3 / 3. V7 automatic acceptance is 1 / 3, equal to v6 on the same outputs. All links pass source validation; referrals concern require this question and a reply and before I can begin, which remain outside frozen grammar. No fresh output exercises the slash-drive alias. The previous known v6 batch scores 3 / 3 under separately labelled retrospective v7 grading (original v6: 2 / 3), exercising the repaired link. No mid-batch prompt/grammar/score change. Public synthetic inputs only; no Fox/private material. The [v7 report](evaluations/2026-10-11-openai-0.3.15-v7-confirmation.md) distinguishes fresh results from development evidence. No commit or push.


All three initial extractions and the same-session scan follow-up complete without evaluator edits. Initial totals are raw 50 / 50 and workbook 67 / 67; four-batch totals are 65 / 65 and 88 / 88, excluding 68 / 57 correct blanks. All eight expected records are present, reusing the same content, with two new page images per batch. Both payment chats have zero varying scored-value cells among 32 raw and 35 workbook entries, including blanks only for consistency. The follow-up preserves custom.md and earlier outputs, processes only the new PDF and does not repeat the policy question. Published extraction/opening JSON and CSV, path/language grading matrix and separately labelled retrospective scores; README and protocol/evaluation guidance are updated. No commit or push.

Final validation passes for frozen package/reference/dependency/harness/test hashes, saved/recomputed opening grades, result/trace/workbook hashes, exact coverage, four-batch totals, three JSON/CSV pairs, 522 matrix cases and 93 local links. Package/registry and whitespace checks pass. No code or package changed after freezing.


### 2026-10-11 — V8 question/reply and can-begin wording

The owner requested require this question and a reply and before I can begin support while preserving source safety, extra-confirmation and Yes-only checks, then three fresh 0.3.15 chats without committing. V8 applies two bounded prose rewrites only after an unsupported explanation verdict, protecting link labels/targets and double-quoted rules. It then revalidates the complete explanation through unchanged v7. Another reply/question, added conditions and unrelated actions remain rejected. V3–v7 files and the 0.3.15 package remain byte-identical.

All 289 local tests pass before freezing. The Windows matrix passes 34 accepted forms, 55 rejected conditions and 204 appended requirements with each of relative and slash-drive links, plus 16 accepted and 28 rejected path cases with new wording: 630 authored cases. New plans freeze v8 and v3/v4/v5/v6/v7/workflow-audit dependencies, retaining historical plan compatibility and diagnostic versions. Froze v8 hash 39406d4f47b617e80b9fff609e1cd3b794a01338929b0777e0c8b849dd0290c7, unchanged package hash dbadd0982cb76f54bcbe2b2141996a6ead202878c0854de591c225fd8b75f7b2, sources, references, prompts and twelve execution files; archived the harness and seven test files before calls. Requested gpt-6.1-sol via existing OpenAI ChatGPT login; runtime identity Unknown.

Three fresh public CLI chats pass exact question/options, order, announcement, sources and observed waiting in 3 / 3. V8 automatic acceptance is 2 / 3, identical to v7 on those same outputs. The remaining explanation uses one reply, outside frozen grammar. Neither new variant occurs in the fresh outputs. The previous known v7 batch scores 3 / 3 in a separately labelled retrospective v8 rescore, versus original frozen v7 1 / 3. No post-result grammar/prompt/score change. Public synthetic fixtures only; no Fox/private inputs. The [v8 report](evaluations/2026-10-11-openai-0.3.15-v8-confirmation.md) separates development examples from fresh evidence. No commit or push.


All three initial extractions and the same-session scan follow-up complete without evaluator edits. Initial totals are raw 50 / 50 and workbook 67 / 67; four-batch totals are 65 / 65 and 88 / 88, excluding 68 / 57 correct blanks. All eight expected document records are present, reusing the same synthetic content; each batch returns two new page images. Both payment chats have zero varying scored-value cells among 32 raw and 35 workbook entries, with blanks included only for consistency. The follow-up preserves custom.md and prior outputs, processes only the new scan and does not repeat the policy question. Published extraction/opening JSON and CSV, the path/language grading matrix and separately labelled retrospective grades; README and evaluation/protocol guidance are updated. No commit or push.

Final validation passes for frozen package/reference/dependency/harness/test hashes, saved/recomputed opening grades, result/trace/workbook hashes, exact coverage, four-batch totals, three JSON/CSV pairs, 630 matrix cases and 95 local links. Package/registry and whitespace checks pass. No code or package changed after freezing.

### 2026-10-11 — V9 one-reply wording

The owner requested `one reply` support while preserving source safety, extra-confirmation and Yes-only checks, then three fresh 0.3.15 chats without committing. V9 maps only prose `one reply` / `one response` to the existing determiner after an unsupported explanation verdict, protecting links and double-quoted rules. The complete explanation is revalidated through unchanged v8. More/additional replies, affirmative-only restrictions, appended requirements and unsafe sources remain rejected. V3–v8 and the 0.3.15 package remain unchanged.

All 294 local tests pass before freezing. The Windows matrix passes 40 accepted forms, 67 rejected conditions and 240 appended requirements with each of relative and slash-drive links, plus 16 accepted and 28 rejected path cases: 738 authored cases. New plans freeze v9 and v3/v4/v5/v6/v7/v8/workflow-audit dependencies; historical plans retain their dependency sets. Froze v9 hash 4e4e083323835f3a8579b818a5b64b7af49e03e482aecd420b57a2dbd59a6c16, unchanged package hash dbadd0982cb76f54bcbe2b2141996a6ead202878c0854de591c225fd8b75f7b2, sources, references, prompts and thirteen execution files; archived the harness and eight test files before calls. Requested gpt-6.1-sol via existing OpenAI ChatGPT login; runtime identity Unknown.

Three fresh public CLI chats pass exact question/options, order, announcement, sources and observed waiting in 3 / 3. V9 automatic acceptance is 3 / 3, identical to v8 on those same outputs. None uses the new determiner variant; chat 3 exercises the previous question-and-reply extension. The previous known v8 batch scores 3 / 3 in separately labelled retrospective v9 grading, versus original frozen v8 2 / 3, including the repaired one-reply example. The [v9 report](evaluations/2026-10-11-openai-0.3.15-v9-confirmation.md) separates development evidence from fresh results. No Fox/private inputs or post-result grammar/prompt/grade changes.

All three initial extractions and the same-session scan follow-up complete without evaluator edits. Initial scores are raw 50 / 50 and workbook 67 / 67; four-batch totals are 65 / 65 and 88 / 88, excluding 68 / 57 correct blanks. All eight expected document records are present, reusing the same content. Each batch returns two new page images. The two payment chats have zero varying scored-value cells among 32 raw and 35 workbook entries, with blanks included only for consistency. The follow-up preserves custom.md and earlier outputs, uses the new scan, and does not repeat the policy question. It reuses previous extraction structure after viewing the new images and is not an independent recognition trial. Published extraction/opening JSON and CSV, regression matrix and retrospective scores; README and protocol/evaluation guidance are updated. No commit or push.

Final validation passes for frozen package/reference/dependency/harness/test hashes, saved/recomputed opening grades, result/trace/workbook hashes, exact coverage, four-batch totals, three JSON/CSV pairs, 738 matrix cases and 97 local documentation links. Package/registry and whitespace checks pass. No code or package changed after freezing.


### 2026-10-11 — Repeat with unchanged frozen v9 and 0.3.15

The owner requested another three fresh chats with the already-locked v9 grader, checking opening/extraction stability and updating reports without committing. Before calls, verified the same grader/dependencies, package, references, thirteen execution files, prompts, model request, provider and scripted public reply against the preceding v9 plan. Archived thirteen execution files and eight tests in a new ignored batch. The earlier 294-test and 738-case validation remains historical evidence; unchanged code did not require a new unit-suite run. Requested gpt-6.1-sol via existing OpenAI ChatGPT login, HTTPS, codex-cli 0.162.0-alpha.17.2; runtime identity Unknown.

Three distinct new CLI sessions again pass v9 openings 3 / 3, giving 6 / 6 across the two prospectively frozen v9 batches. V8 also passes all six of those same outputs. None uses one reply/response, so the repeat does not establish that extension on fresh wording. Exact question/options, order, announcement, safe source and observed waiting all pass. Public known synthetic inputs only; no Fox/private sources. Scripted read-later responses remain labelled fixtures, not human consent.

All four phases complete: initial raw 50 / 50 and workbook 67 / 67; including same-session scan follow-up, raw 65 / 65 and workbook 88 / 88, excluding 68 / 57 correct blanks. Eight expected document records are present, reusing the same content. No extra inputs, missing records, policy repeats or changed prior workbooks. Custom.md is byte-identical on follow-up. Each phase returns two new page images. Across both batches, four initial payment chats agree on 32 raw / 35 workbook scored entries; two energy chats agree on 37 / 40; two scan follow-ups agree on 32 / 35. Blank entries count only for repeatability, not accuracy. Aggregate eight-phase scores are 130 / 130 raw and 176 / 176 workbook, excluding 136 / 114 correct blanks; these are repeated content, not independent documents.

All three initial capability probes report a local pypdfium2 4.30.0 PdfDocument context-manager error. Chats 1/2 recover with declared dependencies via uv; chat 3 retains a failed route and then renders with installed PyMuPDF. Recovery was model-led within original attempts, with no evaluator edits or changed package. Reported final accuracy does not erase the runtime limitation. The [repeat report](evaluations/2026-10-11-openai-0.3.15-v9-repeat.md), opening/extraction JSON and CSV, runtime observations and cross-batch stability JSON preserve the evidence. README updated; earlier reports unchanged. No commit or push.

Final validation confirms frozen hashes and 21 archived files, historical-report preservation, three new session IDs, stored/recomputed openings, result/trace/workbook hashes, exact coverage, aggregate denominators, both new JSON/CSV pairs, comparison/runtime hashes and 99 local documentation links. Existing matrix/fixture hashes and whitespace checks pass. No new unit-test run or code/package change is claimed for this repeat.


### 2026-10-11 — PDF renderer compatibility and shared runtime (0.3.16)

The owner requested the renderer fix, consistent capability/preparation dependencies, testing and an eval report while retaining frozen v9 and making no commit. Reproduced the old 0.3.15 probe failure using installed pypdfium2 4.30.0: PdfDocument lacks the context-manager exit method. Updated the probe, preparation and recovery scripts to use explicit close semantics; the probe closes child resources even on a failed render. Route inspection accepts the 4.x/5.x bounds accessor names. Added OCR-off probing and aligned managed recovery dependencies.

Added pdf_runtime.py as a shared in-process entry for probe, prepare and render. Codex uses the same entry/launcher for all PDF actions, distinguishes installation-free discovery from explicit uv dependency setup, checks actual render status and compares environment metadata. Existing-interpreter operation remains available without installation. The OpenAI entry prompt and extraction rules are unchanged. Shared code rebuilds produce OpenAI 0.3.16, Anthropic 0.3.14, Google/xAI 0.1.1, all experimental; only OpenAI receives new live model evidence in this task. OpenAI artifact hash: 2f03d23ca01d755c4cf6ed94c752d809ef03df201a94a26d8b8c49dc11bd7743. The prior 0.3.15 package is archived for regression evidence.

All 298 local tests pass, including four new runtime tests. The focused PDF suite passes 23 / 23 on actual system PDFium 4.30.0. The reusable eval/tools/check_pdf_runtime.py passes 9 / 9 checks in each of existing 4.30.0, existing 5.14.0 and managed uv 5.14.0 environments: 27 / 27 runtime assertions, not extraction accuracy. Checks cover identical probe/preparation environment metadata, all four PDF formats and eight images, pending visual verification, recovery rotation/crop, no overwrites, and a failed input followed by a successful input. Visually inspected managed page/recovery renders. Package and whitespace checks pass.

V9 hash 4e4e083323835f3a8579b818a5b64b7af49e03e482aecd420b57a2dbd59a6c16, its dependencies, the evaluator and payment/energy references remain byte-identical. The public first-use 0.3.16 plan freezes the new package with the same evaluator before calls, archiving thirteen execution files, two PDF tests and the deterministic tool. Requested gpt-6.1-sol through existing OpenAI ChatGPT login, HTTPS, codex-cli 0.162.0-alpha.17.2; runtime identity Unknown. Three fresh openings pass unchanged v9 in 3 / 3; initial extraction scores raw 50 / 50 and workbook 67 / 67, excluding 51 / 43 correct blanks. All three call the new runtime probe and preparation entry successfully, without evaluator edits. No private Fox sources are used.


The same-session scan follow-up also completes: raw 15 / 15, workbook 21 / 21, with unchanged custom.md and earlier workbook and no repeated policy question. Four-batch totals are 65 / 65 raw and 88 / 88 workbook, excluding 68 / 57 correct blanks; eight expected document records are present with no extras or unprocessed inputs. Supplementary command/route auditing finds successful shared-runtime probe and prepare in 4 / 4 phases with identical effective interpreter/library metadata, Python 3.14.5 and PDFium 5.14.0, without the old context-manager failure or alternate-renderer recovery. Each phase returns two new page images. The [0.3.16 eval report](evaluations/2026-10-11-openai-0.3.16-pdf-runtime.md) links deterministic, opening, extraction and runtime evidence; README and evaluation guidance are updated. No package/grade changes after freezing, no commit or push.

Final checks pass for the frozen package and sixteen archived execution/test files, locked evaluator/references, saved/recomputed opening grades, result/trace/workbook hashes, coverage, totals, both model JSON/CSV pairs, deterministic/runtime evidence hashes, four environment matches, 104 local links and whitespace. The 298-test suite and generated-package check passed before the model freeze; older 0.3.15 evidence is retained separately.

### 2026-10-11 — Varied public first-use cases and reference erratum

The owner asked to carry out the next step after the PDF runtime fix, without committing. Added two new public synthetic PDFs containing three pages and four documents: an Invoice and Cash Memo on one native-text page, an image-only Invoice and a native-text lab certificate. Visually reviewed all pages; observed routes A / B / A. Two purposes request payment details versus repeated certificate measurements with different printed units and an absent ash field. Both retain standard document sheets. The printed 125.75 total deliberately disagrees with subtotal 120.00 plus tax 5.00.

Added a reusable varied-use runner, authored references, source generator and nine tests. Tests exercise raw and real-workbook positive controls, missing documents, same-page source order, invented dates, silent total correction, unit conversion, wrong purposes, frozen evidence and attempt retention. The full suite passes 307 tests. Package/registry checks pass. The OpenAI 0.3.16 package, v9 and prior scorers remain unchanged. Before model calls, froze source/reference/prompt/package bytes and 43 execution/core/data files in plan 103679b1c35492b5d66c029b43f52a53087626137e84c830e1f307c0d6ff6155, with archived execution files.

Ran two new CLI sessions, one per purpose, requested gpt-6.1-sol via existing OpenAI ChatGPT login, HTTPS, codex-cli 0.162.0-alpha.17.2; actual runtime identity remains Unknown. Neither received pre-run examples, answers, settings or profile. Both pass unchanged v9 openings and complete setup, custom.md, PDF reading, extraction and Excel after a labelled scripted read-later policy reply. No evaluator edits or replacement retries. Each returns three page images. Both use successful shared-runtime probe and prepare with identical Python 3.14.5 / PDFium 5.14.0 metadata. No private Fox sources were used.

Original frozen v1 scores are raw 79 / 129 and workbook 93 / 151, excluding 78 correct blanks in each layer. Investigation found a reference authoring error: Other was used as document type instead of the existing contract's Lab certificate. Both model outputs correctly retain Lab certificate on the Other sheet; strict identity matching produced missing-plus-extra certificate/observation records. Retained the original references, plan, grades and model outputs. Added versioned v2 references and a retrospective reviewer that permits only that identity correction, verifies archived evidence and reproduces original grades before regrading. Two additional tests cover the erratum and continued unit-error detection; the focused suite passes 11 / 11. No second full-suite run is claimed.

Retrospective v2 scores are raw 104 / 104 and workbook 122 / 122, excluding 78 / 78 blanks. All eight document executions, six lines and 22 observations match; these reuse four unique documents, three unique lines and two input files. Cash Memo classification, printed total preservation/arithmetic flagging, absent fields and sample units all match. The corrected scores are not a prospectively frozen pass or evidence of stability. A separately versioned execution plan using v2 is the next confirmation step; the original v1-bound runner is retained for reproducibility. Published original, opening, corrected-reference and runtime JSON/CSV evidence with the [varied-use report](evaluations/2026-10-11-openai-0.3.16-varied-use.md); README and evaluation guidance updated. Prompt/package/v9 remain unchanged; no commit or push.

Final verification passes for the unchanged package/v9, all 43 archived execution files, two distinct sessions, saved/recomputed openings, original raw/workbook evidence, runtime route hashes, original/corrected denominators, all three JSON/CSV pairs and 117 local documentation links. Package/registry and whitespace checks pass. Original v1 errors and separately labelled retrospective v2 results remain intact.

### 2026-10-11 — Prospective v2 confirmation with unchanged 0.3.16 and v9

The owner requested freezing the corrected v2 answers, running fresh payment and certificate chats, updating eval evidence, retaining v9 and making no commit. Added varied_use_v2.py as a versioned entry loading the unchanged varied-use execution engine in an isolated module namespace with v2 selected. V1 imports, execution/scoring files and historical plan hashes remain intact. The entry rejects v1 plans before reserving attempts. Seventeen focused tests pass, including six v2 workflow/version controls alongside eleven existing reference tests. No new full-suite run is claimed; the earlier 307-test run is historical evidence.

Before calls, froze unchanged package 0.3.16 hash 2f03d23ca01d755c4cf6ed94c752d809ef03df201a94a26d8b8c49dc11bd7743, unchanged v9 hash 4e4e083323835f3a8579b818a5b64b7af49e03e482aecd420b57a2dbd59a6c16, source PDFs, prompts and 44 execution/core/data files. Archived all execution files and two test files. Plan hash: 37a4fd016c4a223077322e7ae6eb0900be0c94acfe8a6ea74cb85726be5e31ce. Payment v2 hash b915e4ef581ba599add824b8e15cd19f4c08b2887efba0ef153f6c591a6d5ec7 and quality v2 hash 79f5b3036123892e6969fd2ab3c1c6c010bb5670650557f5b0aed9afd220fcb3 match the prior erratum byte-for-byte. Captured 162 historical report hashes to verify preservation.

Two distinct fresh CLI sessions used gpt-6.1-sol requested via existing OpenAI ChatGPT login, HTTPS and codex-cli 0.162.0-alpha.17.2; runtime model identity remains Unknown. Only the installed skill and the same two known public synthetic PDFs were supplied. No earlier example, settings, profile, answer or evaluator extraction was supplied. Each session received one labelled scripted read-later public reply after the observed exact-question/options pause. No private Fox files, evaluator edits, replacement retries or post-result reference changes.

Both openings pass unchanged v9, both workflows complete and both runtime pairs successfully use matching Python 3.14.5 / PDFium 5.14.0 probe/preparation environments. Payment scores 45 / 45 raw and 55 / 55 workbook; quality scores 59 / 59 and 67 / 67. Totals: 104 / 104 raw and 122 / 122 workbook, excluding 78 / 78 correct blanks. All eight document executions, six line rows and 22 requested observation rows match, reusing four unique documents and two PDFs. Cash Memo classification, missing fields, printed total 125.75 with arithmetic failure, and all four sample measurements/units/contexts match. Three page images return in each chat; sources and package bytes remain unchanged, and policy questions do not repeat.

Supplementary comparison against the prior outputs retrospectively scored with v2 finds zero changed scored entries: payment 76 raw / 83 workbook entries, quality 106 / 117, including blanks only for consistency. This is repeatability on known content, not independent-document or general handwriting accuracy. Published the [prospective confirmation report](evaluations/2026-10-11-openai-0.3.16-varied-v2-confirmation.md), extraction/opening JSON and CSV, runtime and comparison evidence. README and evaluation commands updated. Historical v1 failure and retrospective v2 results remain intact. Prompt/package/v9 unchanged; no commit or push.

Final verification passes for the 44 archived execution files, two archived test files, unchanged package/v9/reference hashes, two distinct exact-session continuations, saved/recomputed openings, result/trace/workbook and route hashes, all score denominators and structural checks, both JSON/CSV pairs, 116 local links and preservation of all 162 historical reports. Package/registry and whitespace checks pass.

### 2026-10-11 — Frozen difficult-document regression, unchanged 0.3.16 / v9

The owner requested locked difficult-document answers, the old Fox page as regression, different-document counterexamples, updated eval evidence and no commit. Reused the existing private case without changing reference values or broadening owner approval: two invoice classifications and two totals are owner-confirmed; other cells and detailed row coverage remain provisional. A new regression lock binds it to package 0.3.16. Added the existing public digit-boundary raster PDF and conflicting-OCR coal invoice/certificate to this batch. These are known synthetic documents, not new handwriting holdouts. All five public source pages were visually reviewed against the locked references.

Plan 1e32645095703f234f950971e13dccdb7a0378ff4788f2dd12db74a2bc1f6281 freezes source/settings/answers, unchanged package 2f03d23ca01d755c4cf6ed94c752d809ef03df201a94a26d8b8c49dc11bd7743, unchanged v9 4e4e083323835f3a8579b818a5b64b7af49e03e482aecd420b57a2dbd59a6c16 and 43 execution/core/data files. Execution files are archived and orchestration is hash-locked. Three distinct fresh CLI sessions request gpt-6.1-sol through the existing OpenAI ChatGPT login, HTTPS, codex-cli 0.162.0-alpha.17.2; runtime identity remains Unknown. Each receives the package, one PDF, frozen custom.md and a synthetic company profile, without answers, examples, pre-answer images or an interpreter hint. This tests extraction with existing settings, not first-use requirements gathering.

All three openings ask the exact question with both choices and pause, but unchanged v9 accepts 0 / 3 automatically. One explanation yields unsupported_explanation and two yield unsupported_application_clause. Preserve all as requires_review; do not patch v9, retry or replace them. An actual human answer bound to the Fox session and labelled scripted read-later answers for the public sessions allow separately scored extraction. No extra confirmation or Yes-only condition was observed in the openings.

All three extractions complete. Fox scores raw 4 / 5 and workbook 6 / 7, excluding 3 / 3 blanks. Owner-confirmed subsets are 1 / 2 and 3 / 4; provisional subsets are 3 / 3 in both layers. The earlier target amount and both invoice classifications match, including Cash Memo. The neighbouring total is left blank with an unclear flag because the model reports an overwritten leading mark: count it as a miss in both layers against the unchanged owner reference. The predeclared covered invoice number remains unclear/blank with no unsupported fill. The model repairs its own Unicode title encoding within the same execution; no evaluator repairs or replacement retries occur.

Public digit-boundary scores raw 13 / 13 and workbook 15 / 15, excluding 2 / 3 blanks. A table rule is not made into a digit, a real leading digit is retained, and the covered-prefix total remains blank. OCR-energy scores workbook 25 / 25, excluding 15 blanks; this legacy reference does not configure raw accuracy. Visible total and both sample measurements/units/pages are retained despite wrong hidden OCR and instruction-like footer text; the arithmetic mismatch is flagged. All 7 configured documents, 3 line rows and 10 requested observation rows match across 3 processed files, with Fox structural scope still provisional. Route reports are B, B/B/B and C/C; image tools return 6, 6 and 2 images including repeated/enlarged views, not 14 unique pages or proof of attention.

Deterministic boundary controls pass the supplied correct transcription and detect 4 / 4 injected errors; they are not model calls. Final verification recomputes unchanged opening and extraction scores, verifies frozen files and package, semantically checks runner-reserialized answer copies and preserves 169 historical report files byte-for-byte. Package/registry and whitespace checks pass; no new full-suite run is claimed. Published the [difficult-regression report](evaluations/2026-10-11-openai-0.3.16-difficult-regression.md), aggregate JSON/CSV, README summary and evaluation guidance. Private details and orchestration stay ignored. The neighbouring handwritten miss and v9 explanation coverage remain outstanding; no prompt/scorer change, commit or push.

### 2026-10-11 — Experimental Cursor adapter for the unchanged xAI prompt

The owner asked for a Cursor adaptation of the existing xAI-family skill, using Cursor with Grok 4.7 at Effort High, without a model-specific prompt fork, a model or effort override, a commit, or any private document. Cursor docs reviewed the same day specify explicit skills through `disable-model-invocation: true` in `.cursor/skills/<name>/`, one-message slash invocation unless started as a Custom Mode, and manual rules only when `alwaysApply` is false and both description and globs are omitted. The CLI docs describe `agent create-chat` and `--resume` for a fresh chat. The local PATH has no `agent` executable, so that fresh-chat path was not executed and this maintainer chat was not treated as a blind extraction.

Added `adapters/cursor/` and generated explicit package `invoice-reader-xai-cursor` 0.1.1 from the unchanged `skills/xai` source. The builder now accepts the `cursor` invocation format and injects `disable-model-invocation` for manual packages. The adapter records print-mode arguments without `--model` or an effort flag. `dist/grok-build/invoice-reader-xai` remains the separate Grok Build preview. OpenAI package `2f03d23ca01d755c4cf6ed94c752d809ef03df201a94a26d8b8c49dc11bd7743` and Codex opening v9 `4e4e083323835f3a8579b818a5b64b7af49e03e482aecd420b57a2dbd59a6c16` were unchanged. Cursor opening checks are a separate observation record and were not observed.

A public capability smoke in this IDE chat wrote files, rendered page 1 of `digit-boundary-v1.pdf`, and received that PNG back as an image. Python 3.14.5 rendered it with pypdfium2 4.30.0, which is outside the scripts' declared `>=5.13,<6` range; `uv` was not on PATH. The image observation is not an extraction score. Four isolated workspaces were frozen for the public cases. Coal raw accuracy is not configured. No case was extracted, so every accuracy count is not run. Published the [Cursor baseline](evaluations/2026-10-11-cursor-xai-baseline.md) and JSON. Focused adapter/build tests passed, and package/registry checks passed. No commit or push.

### 2026-10-13 — Cursor execution scores for the unchanged xAI prompt

The owner asked to score the workbooks already written into the 2026-10-11 Cursor preparation, without editing the prompt, rerunning digit-boundary, or changing OpenAI 0.3.16, opening v9, or the frozen answers. Pairing comes from the stored chats and their `process.py --out` commands. File names and modification times were not the pairing rule, and no score was selected as best.

Four linked workbooks and one provisional repo-root Cash Memo workbook were copied into `eval/runs/2026-10-12-cursor-xai-execution`. Frozen package, source, adapter, and dataset hashes were recomputed and matched the preparation lock. The existing scorer scored raw and workbook separately. `valid: true` there means those hashes matched and the linked files were admitted. The preparation `meta.json` files stay `prepared_only: true` and `valid: false`. Coal raw accuracy stays not configured. Correct blanks stay out of the denominator. The designated Cash Memo workspace still has no workbook; a separate folder is ready for one new chat. Two policy replies are absent from the stored user messages, so those openings stay unverified. `結果.md` is not an opening trace.

The interpreter recorded in the chats is `existing Python interpreter`, Python 3.14.5, with installed pypdfium2 4.30.0. The prompts supplied that path. This is evaluator setup assistance on an existing machine, not a clean install of the declared `pypdfium2>=5.13,<6` range. Published the [execution report](evaluations/2026-10-12-cursor-xai-execution.md), JSON, and CSV. No commit or push.

### 2026-10-13 — OpenAI final verification for Friday experimental release

The owner requested final verification and set Friday 2026-10-16 as the public-release target. This is a target date, not automatic publication authorization. The full current suite passes 320 tests. Generated-package/registry checks pass. OpenAI 0.3.16 package tree remains 2f03d23ca01d755c4cf6ed94c752d809ef03df201a94a26d8b8c49dc11bd7743, exactly matching the model-evaluated package. No prompt, v9, reference, shared-runtime or Cursor implementation changes were made for this verification.

A new copied-package document workspace and fresh uv cache complete setup, shared PDF probe/preparation/recovery, template creation, fresh manifest and workbook processing. Observed Python 3.14.5, PDFium 5.14.0, Pillow 12.3.0 and openpyxl 3.1.5. Probe/preparation report the same interpreter and libraries. Reused the known public printed fixture and its reviewed supplied transcription, inspected the rendered page and reopened the workbook. All 24 integration assertions pass, including values, evidence, coverage, review flags and unchanged source/package bytes. This is installation/processing verification, not a new model accuracy result or fresh operating-system/CLI installation.

Built an ignored local OpenAI-only ZIP with 35 members; each member matches the package bytes. ZIP SHA-256 f9855c51eeb13e3b830a4ad4098da4d3d763281a875bfc1b4e97aa2ce1643330. Refreshed origin and scanned publishable files plus locally reachable Git history, PDF text and XLSX contents. Only three known scanner-pattern matches occur; no unresolved findings. Sixteen prior binary contents retain their reviewed hashes; two newer synthetic PDFs add three reviewed pages. Root Cursor output and the duplicate Cash Memo PDF are now ignored through narrowly scoped rules, with local files preserved and canonical fixtures unchanged.

Published the [0.3.16 verification report](evaluations/2026-10-13-openai-0.3.16-release-readiness.md) and JSON, and refreshed README's installation evidence. The report retains handwriting misses, v9 explanation-format reviews and limits of synthetic accuracy evidence. It specifies a reviewed publication diff, final hash check and explicit commit/push approval; no commit, tag, push, upload or scheduled publication occurred.

The owner proposed three maintainer-facing prompt parts: goals/principles, custom-requirement instructions, and prohibited behaviours. This remains a discussion proposal. Custom instructions would describe how to maintain each user's external custom.md, not embed one user's settings into the family prompt. Shared contracts and tool commands keep their existing ownership. Prefer compiling authoring parts into one installed prompt; do not make users manage three prompts or create model-version forks. Friday's verified bytes stay unchanged. A later lossless split must demonstrate byte-identical generated output; changed instructions or ordering require a versioned evaluation.

### 2026-10-13 — Three-part OpenAI prompt and 0.3.17 candidate

The owner approved splitting before publication and requested 0.3.17. Part 2 is named **Workflow and custom settings**: it governs requirements, each user's external custom.md, reading and delivery. Part 1 owns goals/principles; Part 3 owns prohibited behaviours/error handling. These are maintenance boundaries. The builder expands the three source parts into one complete installed SKILL.md, excludes authoring fragments and rejects missing, duplicate, unreferenced, empty, nested or unsafe includes. Timing-sensitive constraints remain next to their workflow step. Custom fields cannot override global constraints. No model-version prompt fork or model override is introduced.

Original prose is reorganized with explicit all-parts-applicable and custom-cannot-override statements. This is a new prompt version, not a byte-identical refactor. Compared with the preserved 0.3.16 package, only SKILL.md and version metadata change. Core 0.3.16, PDF helpers, adapter and field references are unchanged; all four other generated packages retain their hashes. The [maintenance guide](prompt-maintenance.md) explains source ownership and verification.

All **326 tests** pass, including six new composition tests; generated-package and skill-frontmatter checks pass. A copied-package Windows install with fresh uv cache passes **24 / 24** assertions using existing uv/base Python, Python 3.14.5, PDFium 5.14.0, Pillow 12.3.0 and openpyxl 3.1.5. Probe/preparation share interpreter/libraries. The known public invoice is rendered and inspected, its supplied transcription processed, and workbook reopened. This is deterministic installation evidence, not model accuracy. All 35 release ZIP members match the package; package SHA-256 is e355b2548d97021fd1727b515e7d948d2c7c090f741f87176b6cc08f6bfaa07c.

Frozen package, unchanged v9 and unchanged answer references precede four fresh Codex CLI sessions: payment, certificate quality, public digit boundaries and the known private Fox page. Requested model gpt-6.1-sol, tool codex-cli 0.162.0-alpha.17.2, provider OpenAI via existing ChatGPT login/HTTPS; runtime model identity remains Unknown. The public reply fixtures are labelled scripted. Fox receives the actual human policy response bound to that new session. No preliminary examples, interpreter hints, replacement runs or post-result answer edits are used.

Payment scores **45 / 45 raw, 55 / 55 workbook**; certificate quality **59 / 59, 67 / 67**, with different model-created custom settings and full four-document coverage in each. Together they exclude **78 / 78** correct blanks. Digit boundaries score **13 / 13, 15 / 15**, excluding **2 / 3** blanks. Fox scores **5 / 5, 7 / 7** with mixed references: owner-confirmed subsets **2 / 2, 4 / 4**, provisional subsets **3 / 3, 3 / 3**, excluding **3 / 3** blanks. Both confirmed totals and Invoice classifications match; the neighbouring total missed in the prior 0.3.16 execution is present. Both obscured-field controls retain blank/unclear observations, **1 / 1** each. Fox completes its original slower attempt without intervention. These single known-source executions do not establish stability or general accuracy.

All four openings ask the exact policy question/options and pause. Unchanged v9 accepts **3 / 4**; the payment explanation remains requires_review with unsupported_application_clause. Preserve that result alongside successful extraction. Published aggregate [report](evaluations/2026-10-13-openai-0.3.17-prompt-parts.md), clean-install JSON and both model JSON/CSV pairs; private source values, answers and traces remain ignored. README and evaluation index updated. Preserved all **179 historical reports**, four other packages and v9. Friday 2026-10-16 remains the experimental-release target; no commit, tag, push or publication.

Final publication scan covers 678 publishable files and 10 commits, 320 trees and 604 blobs across locally reachable history. Only the three reviewed scanner-pattern matches in current/historical tools/check.py remain; no unresolved findings, decode errors or suspicious working paths. PDF text and archive contents are scanned, with visual-only/encrypted content and unreachable-history limits retained. All 86 checked local links resolve. The 0.3.17 ZIP remains local and ignored; final diff review and explicit publishing approval are still required.

### 2026-10-13 — Approved public experimental release

After reviewing the completed 0.3.17 results and limitations, the owner authorized release and making the repository public now, bringing the earlier Friday target forward. The publication scope is the reviewed repository plus the unchanged OpenAI-only ZIP and checksum. Keep 0.3.17 experimental, explicitly invoked, and marked as a GitHub pre-release. The one v9 explanation review and limited handwriting evidence remain visible; there is no promotion to a general accuracy claim or automatic invocation.

Added [release notes](releases/0.3.17.md) and the README download link. Verified the repository is private before publication, has no existing releases, and local main matches origin/main. Rechecked the evaluated package, all 35 archive members, 179 historical reports, four other packages, v9 and test-log hashes. No executable code or evaluated artifact changes follow the 326-test/24-check verification. The publication operation will commit the reviewed pending work, push main, attach the exact ZIP/checksum to v0.3.17 and make the repository public; GitHub release metadata records the resulting publication state.

The final staged-byte comparison exposed Git newline conversion in seven copied OpenAI reference files. Added narrowly scoped .gitattributes rules preserving source/generated reference bytes, then refreshed the index. A clean export of all 679 staged files rebuilds **5 / 5 packages** with hashes identical to the evaluated working packages, including OpenAI e355b2548d97021fd1727b515e7d948d2c7c090f741f87176b6cc08f6bfaa07c. The release ZIP and model inputs remain unchanged. This corrects publication-byte preservation without changing runtime instructions or repeating model trials.

### 2026-10-18 — xAI prompt 0.1.2 and a scoped Cursor comparison

The covered-digit misses and the unreliable Cursor opening belonged in different layers. OpenAI and Anthropic already passed the shared PDF rule on the same covered-digit file, so `core/` stayed unchanged. The xAI family prompt now distinguishes a nearby untouched rule and a real leading digit from a covered, overwritten, cropped, or merged glyph. A visible fragment stays evidence only. The same prompt tells the model to ask the policy question once in the assistant message and end that turn. The Cursor adapter states that AskQuestion does not wait and is not a reply. That sentence is not in the Grok Build adapter. There is still one xAI prompt, with no model or effort pin. Family version is 0.1.2. `last_eval` stays empty.

Cursor tree `71d0552230f86c0e5c25d3af707d86ed091198bd537ef9a0d559b51db68b04e5` was compared with frozen 0.1.1 `ba89c43560d1cfc8362135ea9465be5f44f4769f338ca6522501df1fa4527657` and with a no-skill arm. The Grok Build tree changed to `b1e72ffff1740e8093486eb7c4c914592b7dc10a015a5a71beccd58213a6a96b` and was not run. The OpenAI tree stayed `e355b2548d97021fd1727b515e7d948d2c7c090f741f87176b6cc08f6bfaa07c`. Every recorded turn reported Grok 4.7 256K High Fast. The 17 October CLI check was `2026.10.14-941492e`; on 18 October the version command reported `2026.10.16-e3cb207`, so that day's repeats stay separate. The runtime was Python 3.14.5, pypdfium2 5.14.0, Pillow 13.0.0 and openpyxl 3.1.5. All 22 saved route reports say pypdfium2 5.14.0.

The improved skill waited once on 14 of 14 first invocations, accepted a scripted No or uncertain reply, stopped on a stop reply, and did not ask again for a second workbook. Digit-boundary was 15 / 15 on three runs, Cash Memo 17 / 17 on three runs, and the new meter invoice 12 / 12. The new covered receipt total stayed blank on three runs. One of those three wrote the clear storage fee as `80 . 00` and did not mark it unclear. The prompt was not edited after that output. The frozen package matched the amounts on the runs that finished, including a compliant opening on some chats and AskQuestion or a same-turn extraction on others. Four frozen chats never received the scripted reply and have no workbook; those are harness gaps and are kept. The no-skill arm kept the same covered and clear amounts under the same explicit instruction, with unstable sheets and one Cash Memo run that used the printed titles instead of the skill's Invoice label. The shared covered-digit sentence means the abstention is not evidence for the prompt change alone. No currency cost was returned. Accountant review time was not measured.

Published the [comparison](evaluations/2026-10-18-cursor-xai-comparison.md), JSON and CSV. The `tests/` suite passed 346 tests. Package check passed. No commit or push.

### 2026-10-23 - Independent public snapshot and diverse-data benchmark

The owner chose a new repository with independent Git history. The source
snapshot excludes private owner instructions, datasets, runs and identifier maps.
Historical reports keep their original scope, scores and package hashes. Public
links now point to this repository. Original Git history is not imported.

Three fresh Luna/high Codex chats using unchanged OpenAI 0.3.17 score 31 / 31 raw
and 36 / 36 workbook fields across a utility invoice, an obscured receipt and a
new same-page credit-note/proforma diagnostic. Correct blanks are excluded;
there are no missing or extra scored rows. All three openings pass unchanged v9.
Sources, references and graders were frozen before calls. Public replies are
labelled scripted fixtures. No customer document is part of this batch.

The [report](evaluations/2026-10-23-openai-diverse.md) records execution settings,
hashes, limits and priorities for a private Fox development/confirmation split.
No new failure justifies a prompt revision; keep 0.3.17. All 347 local tests and
the generated-package check pass. Full publication checks apply separately.
