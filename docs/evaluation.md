# Evaluation

Unit tests verify deterministic validation, custom observations, safe workbook output, manifest isolation and scoring regressions. They do not measure a model's reading accuracy. Model evaluations run the packaged skill in a fresh workspace holding only the package, selected source and user settings. Expected answers are stored in the results directory, not the model workspace. This is context isolation, not a claim of filesystem isolation: personal skills/configuration may remain visible to the CLI.

## Cases and expectations

Original printed cases use `eval/answer-key.xlsx`. Their expectations are converted and copied into each run. Custom scenarios use versioned `expected.json` plus `custom.md`. The same `coal-pack.pdf` supports payment and coal-energy scenarios, including multiple samples, an absent requested measurement, a deliberately inconsistent total and instruction-like document text. No real client material is included.

`make_custom_cases.py` creates the fixture and settings but never overwrites an existing answer file. `make_pdf_route_cases.py` adds scan, OCR and mixed versions and refuses to overwrite existing fixtures/answers. Each format has payment and energy scenarios with the original visible answers, adjusted only for source filename. The OCR version intentionally substitutes incorrect hidden numbers; its image is unchanged. The mixed version has a native invoice and scanned certificate. All share the `coal-pack` content group, not independent business-document diversity. Change expected answers only when correcting a documented specification error, never to match a model output. Photos, handwriting and holdout layouts remain to be added.

PDF tests verify per-page dispatch, rendered evidence, OCR fallback, capability states and fixed fixture answers. Mocked Tesseract results exercise control flow, not the engine's real recognition. Live eval must examine the preserved route report and the agent's reading review as well as workbook values. The workbook scorer does not currently validate the reading-review ledger or compute automatic route-selection accuracy; inspect those traces separately. It does score the wrong-hidden-value trap through the visible expected values and records each case's format category/content group. No new LLM accuracy is established by preparation or deterministic tests.

## Run and score

### Diverse synthetic documents: 23 October 2026

The [new snapshot benchmark](evaluations/2026-10-23-openai-diverse.md) adds
three fresh Codex Luna/high chats using unchanged OpenAI 0.3.17: a utility
invoice, an obscured receipt, and a new credit-note/proforma pair. Frozen
references score 31 / 31 raw and 36 / 36 workbook fields, with correct blanks
excluded and no missing or extra scored rows. The prompt remains unchanged;
the report scopes the evidence and identifies the next difficult-source groups.

### Three-part prompt regression: 0.3.17

The [0.3.17 report](evaluations/2026-10-13-openai-0.3.17-prompt-parts.md)
evaluates the newly composed prompt in four fresh sessions: payment, certificate
quality, digit boundaries and the known private Fox page. Package, answers and
unchanged v9 are frozen before calls. This reuses known documents; it does not
add unseen holdout evidence. The report separates opening review, raw fields,
workbook fields and owner-confirmed/provisional private references. Earlier
reports and other family packages remain unchanged.

### Difficult-document regression with frozen 0.3.16 / v9

The [difficult-document batch](evaluations/2026-10-11-openai-0.3.16-difficult-regression.md)
adds one known private Fox regression and two public counterexamples: raster
digit boundaries and conflicting hidden OCR with repeated certificate samples.
Sources, answers, package and 43 execution files were frozen before three fresh
sessions. Owner-confirmed private cells are reported separately from provisional
references. The public fixtures are existing synthetic sources, not new holdouts.

Keep opening format separate from extraction: all three exact policy questions,
choices and pauses are observed, while unchanged v9 returns `requires_review`
for the attached explanation wording in all three. Do not silently repair the
grader or relabel these openings as passes. The actual human Fox reply and
labelled scripted public replies allow extraction to be measured separately.
Coal's existing reference scores only workbook output; do not infer a raw
accuracy rate from the presence of a raw JSON artifact. Correct blanks remain
excluded. The report links the aggregate JSON/CSV and retained private evidence.

### Varied multi-file first use

The [0.3.16 v2 confirmation](evaluations/2026-10-11-openai-0.3.16-varied-v2-confirmation.md)
records two fresh executions with the corrected references frozen before calls.
Both purposes pass all scored fields and unchanged v9. Original v1 and
retrospective-v2 results remain separate.

For new corrected-reference tests, use `eval/runner/varied_use_v2.py` with the
[v2 prospective protocol](../eval/workflows/varied-use-v2/README.md#prospective-confirmation).
Its `plan`, `start`, `reply` and `report` commands use the same arguments as v1.
The versioned entry selects v2 references in an isolated copy of the unchanged
execution module, preserving v1 imports, hashes and historical evidence. Both
entries are frozen with the plan. It rejects a v1 plan before reserving an
attempt. Freeze the new plan before either model call; fresh execution and
retrospective regrading are separate evidence.

The [first results](evaluations/2026-10-11-openai-0.3.16-varied-use.md) retain a v1
reference error: certificate type was mistaken for its Other worksheet. The
[v2 erratum](../eval/workflows/varied-use-v2/README.md) fixes only that identity;
its scores on the original outputs are explicitly retrospective. The commands
below reproduce the frozen v1 protocol. New corrected prospective runs need a
separately versioned plan using v2 references.

`eval/runner/varied_use.py` runs two fresh public CLI sessions over the same new
PDFs, with payment and certificate-quality purposes. The [v1 protocol](../eval/workflows/varied-use-v1/README.md)
defines four documents across three pages: two same-page invoices (including a
Cash Memo), an image-only invoice and a native-text certificate. It tests optional
missing fields, multiple samples/units and a printed total that fails arithmetic.
Answers, source PDFs, the package and the execution/scoring code are frozen before
calls. Model workspaces receive only the package and PDFs. Failed attempts cannot
be retried in place; raw/workbook scores, excluded blanks and delivery completion
remain separate. This broadens source/layout coverage, not repeatability evidence.

```text
python eval/runner/varied_use.py plan eval/runs/NEW_BATCH --workspace-root NEW_EXTERNAL_DIRECTORY --model YOUR_SELECTED_MODEL_ID --provider "ACTUAL_ACCOUNT_ROUTE"
python eval/runner/varied_use.py start eval/runs/NEW_BATCH --trial 1
python eval/runner/varied_use.py reply eval/runs/NEW_BATCH --trial 1
python eval/runner/varied_use.py start eval/runs/NEW_BATCH --trial 2
python eval/runner/varied_use.py reply eval/runs/NEW_BATCH --trial 2
python eval/runner/varied_use.py report eval/runs/NEW_BATCH --out NEW_REPORT.json
```

`reply` sends the labelled scripted read-later policy response only after the exact
question, both choices and an observed pause. It is for these public synthetic
fixtures, never private consent. Existing v9 and extraction graders are reused
unchanged. A model/grader/package edit requires a new plan and separate evidence.

### PDF runtime compatibility checks

`eval/tools/check_pdf_runtime.py` checks the generated package through one shared entry for probe, preparation and recovery. Use `--python EXISTING_INTERPRETER --out NEW_LOCAL_FOLDER` for installation-free execution, or `--uv --out NEW_LOCAL_FOLDER` for explicit managed dependency setup. It preserves detailed local execution evidence, refuses existing output folders, compares probe/preparation interpreter and library metadata, checks all four public PDF formats, rotated/cropped recovery, no-overwrite behaviour and partial-input retention. These are deterministic rendering/routing checks, not model extraction accuracy. See the [0.3.16 runtime report](evaluations/2026-10-11-openai-0.3.16-pdf-runtime.md). Keep the opening grader/reference freeze separate from package changes.

### First-use workflow without prefilled settings

The [first-use-v1 protocol](../eval/workflows/first-use-v1/README.md) starts three fresh Codex CLI sessions outside the repository. Only the generated skill and a public PDF are present initially; ordinary-language requests require the model to create custom.md, handle setup and generate Excel. Expected answers remain in the evaluator batch. Two payment trials and one energy trial share the source; chat 1 also processes a new scan batch in the same session. This tests setup and setting reuse, not an unseen-content holdout.

`eval/runner/first_use.py` freezes the plan, reserves one attempt per action and retains incomplete results. Its report separates raw/workbook checks, excluded blanks, exact-session continuation, preserved outputs, policy behaviour and actual image-tool returns. User-facing field labels allow model-chosen internal keys; missing/wrong labels still fail. Historical raw definitions remain unchanged. Reports never turn missing scores into a successful zero-denominator result. See the [0.3.14 results](evaluations/2026-10-11-openai-0.3.14-first-use.md).

`workflow-audit-v2` separates the exact question/options, observable waiting and opening format. It accepts presentation-only Markdown and static combined PowerShell reads confined to installed skill instructions, while extra prose remains `requires_review`. `eval/tools/review_openings.py BATCH --out NEW_JSON` adds diagnostics to an older public-repeat batch without rewriting its scores. Image evidence must come from actual image content in a matching tool-call output in the exact session trace; a self-authored ledger is insufficient. Returned images do not prove attention or source grounding.

On 2026-10-11 the owner allowed one necessary Codex waiting explanation with a source link. `codex-opening-v3` is an additional format contract: it accepts the exact optional short skill announcement, question and ordered choices, followed by at most one narrowly recognised explanation. Accepting that explanation requires the disclosure instruction in the matching session's captured base instructions and a link to this installed skill's entry or chat-start reference. Extra confirmation, Yes-only conditions, multiple explanations, unrelated links and unsupported wording do not automatically pass. Observable waiting is still required. This judges format, not complete compliance with every host instruction or the quality of extraction.

Run `python eval/tools/review_first_use_openings.py BATCH --out NEW_OPENING_REPORT.json` to produce separate JSON/CSV for the plan's declared contract alongside the unchanged first-use report. It retains the strict v2 status and evidence hashes. The initial 0.3.15 openings were observed before the owner approved v3; their v3 grades are explicitly retrospective, not a predeclared confirmation study. Do not substitute these grades for the frozen originals.

The subsequent [prospective v3 confirmation](evaluations/2026-10-11-openai-0.3.15-v3-confirmation.md) freezes the unchanged contract and grader before three fresh chats. Automatic format acceptance is **0 / 3**: all three still ask/wait correctly, but natural-language explanation/link-label variants fall outside the narrow recogniser. Preserve `requires_review` and separate trace observations from automatic grades. This exposes a grading-coverage limitation; it does not justify changing the frozen recogniser mid-batch or claiming stable format acceptance.

`codex-opening-v4` implements the owner's requested paraphrase improvement without changing that one-line disclosure policy. It separates the visible explanation from its source URL, verifies the installed source, and recognises complete waiting clauses through a bounded grammar. An explicit negative guard and whole-clause matching reject extra confirmation, Yes-only conditions and unrelated appended actions. Unknown wording still requires review. Tests cover accepted paraphrases, rejected conditions, valid explanations with unsafe suffixes, host evidence, source boundaries and unchanged waiting requirements. V3 remains byte-identical.

`codex-opening-v5` additionally parses a quoted waiting rule followed by at most one application clause in the same explanation paragraph. It validates the quote and application separately; an extra condition, third sentence or unrelated action remains reviewable. It also recognises `require this pause` and an `after asking` rule prefix. V3 and v4 remain byte-identical.

`codex-opening-v6` also accepts a complete source-linked application followed by one quoted waiting rule, separated by a colon, semicolon or sentence boundary. It validates both complete clauses with the preserved v4/v5 recognisers. Quoted text receives the same extra-confirmation/Yes-only guard as other visible prose; unrelated actions or a third clause remain reviewable.

`codex-opening-v7` recognises one slash before a Windows absolute drive path (`/C:/...`) as a display alias. It canonicalises only the source target, checks its resolved identity against the two installed source files, and preserves visible prose/negative guards. Traversal, foreign targets, UNC/device paths, drive-relative paths, alternate streams, encoded path spellings and redirected installed roots are rejected. Path aliases require native Windows resolution.

`codex-opening-v8` adds bounded prose equivalents for `require this question and a reply` and `before I can begin/start`. It protects link labels/targets and double-quoted rules from rewriting, then revalidates the entire explanation through v7. Added confirmations, another reply, conditions and unrelated actions remain rejected; all v7 source checks stay in effect.

`codex-opening-v9` treats prose `one reply/response` as a bounded determiner variant of `a reply/response`, then revalidates the complete explanation through v8. Link labels/targets and double-quoted rules stay untouched; more/additional/only, added confirmations and other conditions are not removed.

New first-use plans freeze v9 and its v3/v4/v5/v6/v7/v8/workflow-audit dependencies before calls, store every applicable historical grade alongside v9, and reject grader/dependency drift. Existing plans retain their original dependency set. The review tool defaults to the contract recorded in the plan; selecting another version explicitly is labelled retrospective. A new grader does not rewrite an earlier score or establish better document extraction. Versioned model results must identify which contract was frozen before execution.

**0.3.3 and later:** the one-turn runner rejects live launches before invocation/image attachment. Use `conversation.py` for staged Codex evaluation, or `--prepare-only` for manual evaluation in another tool. Versions 0.3.3–0.3.5 require a real affirmative; 0.3.6 accepts any reply, with labelled negative fixtures restricted to public cases. Do not insert an evaluator-written "Yes", treat confirmed custom fields as policy acknowledgement, or count a skill waiting for an answer as an extraction error. Earlier extraction results retain their original versions.

### Deterministic processor evaluation

`python eval/runner/processor.py` runs seven cases for 0.3.9: missing-origin default, the three legacy explicit conventions, mixed-origin auto and two scoped scripted replies affecting only the printed invoice Total. Versioned `amount-dash-v3` supplies origins and expectations before execution. Handwritten neighbours stay positive, computer-generated/unknown amounts remain text until confirmed, and raw/custom values are unchanged. Each execution records input/reference/script hashes and Python/core versions. See the [0.3.9 processor report](evaluations/2026-10-09-core-0.3.9-amount-origins.md).

Historical 0.3.8 used an unconditional positive default and its four-mode matrix and model case `amount-dash-model-v2-default` retain that contract. Do not treat its expected answers or scores as the current origin-sensitive rule. The current deterministic cases provide origin labels as input; they do not measure a model's ability to identify handwriting or ask/handle a real confirmation. Future live testing must separately score origin classification, pending-confirmation behaviour, scoped replies and unchanged raw values on mixed pages.

### Staged Codex conversation evaluation

`conversation.py start --case CASE --model MODEL --provider ACCOUNT_ROUTE [--python PATH]` prepares a public case and starts one persistent CLI session. It prints the conversation folder and saves the exact session ID, messages, commands, file snapshots and turn outcome. The first turn never attaches page images. This uses the CLI's supported [session continuation](https://learn.chatgpt.com/docs/codex/cli) and locally checked `codex exec resume --help`; it never uses `--last` or changes the user's model from inside the skill.

- `negative CONVERSATION --kind no` or `--kind uncertain` sends a clearly labelled negative test fixture. These remain waiting fixtures under 0.3.3–0.3.5. Under 0.3.6 they permit extraction in public cases and remain explicitly scripted; they are not human reading acknowledgements.
- `reply CONVERSATION --reply-file ACTUAL_REPLY_FILE --origin HUMAN_REPLY_REFERENCE` sends the real user's text verbatim to that exact session. For 0.3.6 any nonempty reply changes the phase to `response_received`; historical sessions still require an explicit affirmative. The runner does not authenticate the human behind a text file: the maintainer must provide honest provenance, not an invented reply. A reply needs an origin and cannot default to Yes.
- `continue CONVERSATION --case NEXT_CASE` gives another batch to the session after its response step, with isolated extraction artifacts. No new acknowledgement is manufactured. The record checks for a repeated policy question, exact session continuity and workbook creation.
- `reset CONVERSATION` opens a different session over the same workspace to test whether a new chat asks again. It does not transfer acknowledgement or replace the acknowledged conversation's ID.
- `report CONVERSATION` writes `conversation-score.json` and calls the existing scorer only for extraction runs actually attempted after the versioned response step. While waiting, extraction is `not_run` and accuracy undefined. The silence path is no resume call; tests verify that an empty reply cannot acknowledge it, rather than sending a fake silence message.

State in `eval/runs/` is a session-bound test record, not a global skill acknowledgement or a file the installed skill uses. Preserve model/provider/package/dataset identity and snapshots per extraction. Complete outcomes do not prove the requested model identity; unknown stays Unknown. Pre-answer command audits are deliberately conservative: only simple skill-reference reads qualify automatically; other commands need maintainer trace review. Separate literal first-message wording from waiting/no-document-work observations. Neither CLI snapshots nor agent-authored ledgers establish the absence of unlogged reads.

Starting with 0.3.5, owner decision A permits one brief skill-use announcement before the exact question, in one message or two. `announcement-before-question-v1` records `opening_status` separately from the historical `question_first` diagnostic. Automatic acceptance recognises only the question alone or simple English skill announcements; other wording/languages require maintainer review rather than being accepted merely for containing a skill name. A missing, changed or repeated question, text after the question, premature document commands, changed workspace or incomplete turn cannot automatically pass. Save manual trace conclusions with the stream hash; do not describe an automated review referral as a demonstrated behavioural failure.

Turn audits record their scoring contract. Reporting older turns without that field retains `literal-first-v1`; do not silently regrade the historical 0 / 2 literal-first result under A. Those historical contracts retain their affirmative-only resume semantics. Choosing A was a product decision, not an acknowledgement. New 0.3.6 sessions record `any-response-v1`: the exact question can be followed by the two declared reply choices; any actual reply permits continuation. Unrecognised opening layouts require trace review. Preserve the verbatim reply and human/scripted actor rather than asserting that policy reading occurred.

### Staged Claude Code session evaluation

`conversation.py` remains Codex-only. For Claude Code, first prepare public cases with `run.py --prepare-only`. Then run `claude_session.py run PREPARED_BATCH --cases ... --model ID --provider ROUTE`. It refuses a workspace containing anything beyond the installed package, source, `custom.md` and company profile, or one whose package/dataset hash differs from the prepared record. Each case gets one new persisted chat with a fixed `--session-id`, and later turns use `--resume` with that exact ID. The first turn invokes `/invoice-reader-anthropic` by name, without page images.

When the exact question appears and no document work occurred, the runner sends the labelled public fixture `No, but I will read it before I upload any confidential data` (`scripted_public_fixture`). Affirmative scripted text is rejected. If the agent works without asking, or asks something else, the chat stops for review; no reply is manufactured. `say RUN --text-file FILE --actor human --origin TEXT` continues a stopped chat with recorded provenance.

Execution evidence goes to a new batch; the prepared record stays `prepared_only`. That evidence is every turn's prompt, argv, stream, stderr, snapshots, permission denials, CLI-reported model/cost, output workbook, archived work folder and raw extraction. A run is valid only when the final turn completed and exactly one `output.xlsx` exists. The package and dataset must be unchanged, and every reported model must match the requested one. `report` calls the existing scorer. `eval/tools/claude_session_summary.py` publishes a path-free JSON/CSV with opening-layout, route, page-image-read and denial digests for manual review.

The evaluation session uses `--setting-sources project,local`, `dontAsk` permissions and workspace-scoped writes. The package scripts run via `uv run` or the supplied interpreter through **Bash only**. Under CLI 2.1.286, no PowerShell allow rule matched a `& "<interpreter>" script.py` call, so the PDF helpers were denied there. Web tools and subagents are disallowed. Reads outside the workspace are denied by default. This is configuration-level context isolation, not OS isolation. The opening audit reuses the Codex layout check. An exact question that appears once in an unrecognised layout (for example in Markdown bold) is `requires_review`, never an automatic pass. See the [2026-10-10 Anthropic report](evaluations/2026-10-10-anthropic-0.3.10-claude-code.md).

Harness v3, chosen by the owner, appends an environment note to the first prompt. It says that one Bash call runs one skill script with a literal path, and that a denied combined command does not block others. It is recorded as evaluator-provided environment information; the package is unchanged. A hook that auto-approved combined commands was rejected by Claude Code's safety classifier and is not used. v3.1 also allows the supplied interpreter written without quotes. Each repeat (`--runs N`) is a separate new chat with its own run folder.

The Claude opening checker records `claude-layout-v3.1`. Under owner decisions it automatically accepts the following, as long as the choice wording is verbatim and no tool other than the skill's references was used before the reply: a short announcement (240 characters or fewer) naming the invoice-reader skill that asks nothing and claims no completed work, Markdown bold around the question or choices, one lead-in line between them, and one closing sentence. Other layouts still need review. A CLI-inserted `<synthetic>` notice, such as "Connection lost mid-response", is recorded as `transport_error` and fails the execution; it is not treated as a different model.

Private cases use `claude_session.py prepare-private CASE_DIR... --runs N --python PATH --out FOLDER`. Each case needs an existing holdout or regression lock for the evaluated package hash; it is verified before preparation, before execution and after execution. Private chats stop at the policy question. The person's actual reply is sent with `say RUN --actor human --origin TEXT --kind policy_response`. Scripted replies are refused for private cases, and a new chat needs a new reply. `eval/tools/claude_private_summary.py` publishes aggregate counts and difference kinds (casing only, spacing/punctuation only, blank, different) without field values or paths.

A reference cell may list several printed forms, for example `"Payer": ["UPPERCASE NAME", "Title Case Name"]`, when each form is verified on the source and accepted by the owner. Any listed form matches exactly, and other text remains an error. Add such alternatives only in a new, separately frozen reference version. `eval/tools/rescore_reference.py BATCH --map CASE=REFERENCE_DIR --out NEW` rescores copied, hash-checked predictions against it; the original batch and scores are untouched, and results are published as a supplement.

Coal scenarios are custom-field demonstrations, by owner decision. Their existing answer files remain for reproducibility of earlier reports; new reports describe them as demonstrations, not accuracy, and no raw references will be added.

### Scoped amount clarification

The public [dash-origin-printed-v2 fixture](../eval/scenarios/dash-origin-printed-v2/README.md) (corrected from v1) exercises a three-stage conversation on the same source: both totals unresolved, only page 1 confirmed positive, then page 2 confirmed negative. A computer-generated handwriting-style font on page 2 tests whether appearance alone is wrongly treated as proof of handwriting. This is not a human-handwriting benchmark.

`conversation.py start` freezes the optional clarification plan, all phase references, settings and source hash before the initial model call. After a policy response, `python eval/runner/clarification.py CONVERSATION --phase first` (then `second`) resumes that exact session with the next predeclared public fixture reply. Replies are explicitly recorded as `scripted_public_fixture`, never human confirmation provenance. The actual model receives only the current reply, an output filename and instructions to preserve earlier workbooks/reuse its manifest. Future answers stay outside its workspace.

Each phase has a distinct extraction archive and raw/workbook snapshot. The runner checks frozen sources/replies/references, package integrity, ordered one-time phases and earlier workbook hashes. An unexpected extra workbook or changed old result invalidates execution; it never silently picks the newest file. Source data remain identical but expected workbook values change only according to the frozen reply scope. This follows the [official Codex CLI exact-session resume interface](https://learn.chatgpt.com/docs/cli/reference); authentication still uses the caller's existing account.

The final numeric score cannot establish correct behaviour before confirmation. Report every phase, raw preservation, scoped conversion and trace observations separately. Unknown model identity remains Unknown. No package recommendation is promoted from this narrow fixture.

### Private handwritten holdouts

Use new sources excluded from prior model runs/prompt development, and record the exclusion IDs and original file hashes. Keep company sources, page images, identifiers, answers and run records under ignored storage. Public reports contain aggregates only. Before a tested model sees a holdout, review its source, save custom/raw/workbook expectations, and freeze them with `holdout.freeze`: it records source/configuration/answer/package hashes and refuses reused baseline sources or an existing lock. `conversation.py continue --case ABSOLUTE_PRIVATE_CASE_DIRECTORY` verifies the lock before execution and again afterwards. Absolute source paths belong only in ignored private case files.

Workbook custom/line sheets store `Document ID`. The scorer joins that ID and source filename to a unique document row to supply `Document type` for reference matching; it never matches on the value being graded. Duplicate document IDs do not resolve to an arbitrary type. This supports multiple documents on one page without requiring the reference to predict model-chosen IDs. Holdout preparation rejects unsupported fixed-sheet reference columns. If an evaluation-code defect is found, preserve the original scores, explain the correction and rescore unchanged artifacts; do not change answers to match predictions.

Record whether answers are agent-reviewed provisional or owner-verified. For crossed-out/ambiguous writing, predeclare unclear observations with blank values; do not assign a convenient exact number after seeing predictions. `holdout.abstention` separately reports unclear-field counts, kept-unclear/blank counts, unsupported filled values and missing observations. No unclear fields means undefined abstention rate, not a perfect score. After first use, the case is no longer a fresh holdout for further prompt tuning. These mechanisms do not themselves establish handwritten accuracy; live readings and independent reference adjudication remain necessary.

See README commands. `--prepare-only` makes inspectable workspaces and invalid-for-scoring metadata; it never invokes a model. Historical live evaluations required `--model`, used the caller's configured account and could consume subscription/API usage. Specify the actual provider/account route with `--provider`; it is not inferred from the recommended model. Failed workspaces are retained for diagnosis. Remove them yourself when no longer needed.

For 0.3.6, review the exact question and the read-before-upload choice; silence waits, while Yes, read-later, No, uncertainty and other replies continue without another confirmation. Task stop/cancel instructions still apply. Verify same-chat reuse, fresh-chat reset and compaction separately. Report `response_received`, not verified reading or consent. Keep historical 0.3.3–0.3.5 outcomes under their original gate; no historical scores are rewritten. Public scripted replies are fixture evidence, not real human acknowledgements, and cannot authorize private-data uploads. Keep onboarding outcomes separate from field accuracy.

Each run records the package content hash, source/settings/answer hash, family version, tool version, requested model and any model identity exposed by CLI events. If the CLI does not expose model identity, it stays Unknown; requested identity is not verified identity. A reported different model invalidates the run. Partial/failed runs must be kept visible in the matrix, not discarded from the report.

The optional `--python PATH` supplies an existing interpreter to the model and records `setup_assistance`; it is not a test of unattended dependency installation. The Codex adapter uses supported automatic approval review (`--approve-for-me`), retaining the workspace sandbox and execution rules. The runner saves the prompt and initial metadata before execution, streams CLI output to disk, and records elapsed time and any reported usage. Execution-valid means completion and artifact checks passed, not that extraction or behavioural checks passed.

Scoring uses only the run's copied expectation, not today's core columns. Source identities are matched one-to-one; duplicate and extra output rows are counted. Missing sheets, unexpected custom columns and missing evidence metadata are structural failures. The current scorer verifies reference metadata, not the semantic truth of arbitrary evidence quotations; maintainers must inspect source-grounding and policy/clarification behaviour in traces.

## Matrix definitions

- `correct`: matching nonblank expected cell. `correct_blank`: both blank, excluded from accuracy.
- `miss`: expected value left blank. `wrong_flagged`: incorrect value with a relevant review reason. `silent_error`: incorrect value without that flag. `invented`: supplied value where no value was expected, including cells on extra matched-table rows.
- Field accuracy = correct / (correct + miss + wrong_flagged + silent_error + invented).
- Field precision = correct / all supplied scored values.
- Printed-value recall = correct / all expected nonblank scored values.
- Document recall = matched / expected documents; precision = matched / actual documents. Misplaced documents count as missing and extra in their respective buckets.
- Review confusion counts use expected Needs review values. Table details retain all row counts; no per-document results are overwritten by later documents.
- Every rate has numerator and denominator columns. A zero denominator is undefined, never 100%.

The matrix identifies each case/scenario, tool, model evidence and artifact/dataset hash. Cells include only columns explicitly specified by that case; score.json retains table details so standard and custom results can be distinguished. These figures describe these public tests only, not a guarantee about future user documents. The scorer exits nonzero for invalid runs, extraction differences or structural failures. An empty batch is an error.

## Raw transcription and workbook usability

The reusable prompts and evaluation contracts are the product. A private-document failure should lead to an independently specified, non-private case or holdout category, not a company-name/layout exception in the prompt. Preserve prior model results and artifact hashes when changing shared instructions or processing.

The `format-payment` and `format-project` cases share `format-pack.pdf` and differ in requested custom fields. Their expectations have two sections: `tables` for the workbook and `raw_tables` for extracted strings. The source and answers are authored independently of processor output. The invoice contains a line amount without a Total label; the payment page has a leading-zero identifier, terminal slash and spaced date. These are invented printed examples, not evidence of handwriting recognition. Initial authoring included the invoice's visible line-item expectation before any model run; later reference changes require an explicit erratum.

- Raw capture uses exactly one `invoice-reader-work/*/manifest.json`. It consolidates only manifest-referenced extraction files and records their hash; zero/multiple manifests are unavailable evidence, never a guessed selection. More than one root `output*.xlsx` makes an automatic run invalid until its final artifact is adjudicated.
- `Raw documents` rows match `File`, `Pages`, `Document type`, `Document occurrence`. Columns such as `fields.cheque_number` and `fields.amount` compare the extracted strings. Occurrence follows record order within a source/page/type, so preserve reading order when multiple documents share those attributes; arbitrary model document IDs and the value being scored are not matching keys.
- `Raw requested values` adds `Field key` and `Occurrence`; columns use `observation.value`, `observation.status`, `observation.pages`, etc. All raw specs must use text comparison. Whitespace is collapsed, while punctuation, case and leading zeroes remain significant. Raw data marked unclear is not silently erased before scoring.
- Workbook scores retain their existing numeric/date comparison. Raw scores and workbook scores have separate counters, denominators and details. For example, copying an amount without its printed terminal stroke can pass the numeric workbook check while failing raw transcription. Correct transcription that the processor cannot parse can fail the workbook check without a recognition error.
- Cases opt in with `raw_tables`; older cases show `raw_status=not_configured`. Required but missing/invalid/hash-mismatched raw artifacts show `unavailable`, leave raw rates undefined and make the eval command fail. They never become a successful 0 / 0 result or erase a valid workbook score.

Neither layer proves that arbitrary quoted evidence is true. Raw scores cover configured standard/custom fields and, when explicitly configured, line items and statement lines. They do not verify visual-review traces or all layout associations. Table details separate standard values from observation status/page checks. Use independent source review and broader handwritten/held-out layouts before claiming general accuracy; do not retrofit historical private scores to make a revised processor look like a new model run.

### Raw invoice and statement lines

New references can opt into `Raw line items` and `Raw statement lines`. Both use exactly `File`, `Pages`, `Document type`, `Document occurrence`, and `Line` as identity; `Line` is the one-based position within that document's corresponding array. Columns use `item.FIELD` (for example `item.quantity`, `item.unit_price`, `item.line_total`, `item.debit` or `item.reference`) with text comparison only. The [fixed scorer fixture](../eval/scorer-cases/raw-lines-v1/README.md) demonstrates the format and regression command. A supplied unclear flag never erases a filled raw value before grading; the array of unclear field names itself is not scored by these tables.

Document occurrence follows reading order among documents with identical file/pages/type. No matching by model-chosen IDs, descriptions or amounts is permitted. This detects swapped rows without pairing values to whichever reference would give a better score. `Pages` is the document page range, not line-level physical-page evidence. Splitting or merging a row is a structural difference under this ordered reference contract.

The CSV adds `raw_line_item_recall`, `raw_line_item_precision`, `raw_statement_line_recall` and `raw_statement_line_precision`, each with numerator and denominator. These measure matched source/ordinal slots, separately from field accuracy; swapped values may preserve row coverage but fail text checks. Unconfigured or zero-denominator rates are undefined. Missing or extra all-blank rows still fail structural checks even when nonblank field accuracy is perfect. Correct blanks stay excluded, and a guessed value in an expected blank contributes an invented-value error.

New line references reject value-based identities, duplicate rows/columns, non-text comparisons and numeric reference values before public preparation or holdout freezing, and again at scoring. Existing runs without these tables retain their original graded columns; no historical denominator is expanded. The deterministic scorer regression is not a new model/PDF accuracy measurement, and does not change the family packages or their evaluated hashes.

The [image-only line scenarios](../eval/scenarios/coal-scan-lines.md) demonstrate this in a live workflow. Their v1 references mistakenly used a bucket name as a certificate type; v2 deliberately omits the open-vocabulary type from document/custom matching on unique single-document pages, while retaining full invoice-line identity. Do not apply that choice to ambiguous multi-document pages. Preserve faulty-reference scores and publish the erratum; new scores need separately frozen references and clearly identified executions. Known content in a continued conversation cannot establish unseen-image recognition, even with a perfect score.

The [2026-10-08 partial live evaluation](evaluations/2026-10-08-openai-0.3.1.md) preserves a currency-display difference under the original references. Its raw checks did not enumerate the payment observation's unit: a perfect raw score therefore did not establish complete transcription. Freeze explicit value, unit, context and summary-display expectations in future cases before execution. Also audit reminder timing and actual image-reading evidence separately; an agent-authored `checked` ledger is not independent proof of visual inspection.

## Unit/context cases and image-input receipts (0.3.2)

`format-payment-units-v1` and `format-project-units-v1` reuse the printed format PDF with new, separately frozen configurations/answers. Payment requests the printed currency and Re: context; its summary is `Lobby hinge inspection: 8,750/ HKD`. Project requests only the reference text and expects no unit/context. Both raw and detailed workbook checks enumerate those parts, so omitting HKD, repeating it inside the value or borrowing currency for a text reference can fail. Historical `format-payment` answers and scores remain unchanged. `make_unit_cases.py` refuses to overwrite existing cases.

The optional Codex `--attach-page-images` mode is **harness-assisted image input**, not a test of the model autonomously finding/rendering/opening pages. It uses the CLI's image attachment option ([official CLI documentation](https://learn.chatgpt.com/docs/codex/cli); local `codex exec --help` checked 2026-10-08). The runner, rather than the evaluated agent, renders each page at requested 200 DPI using the existing renderer and its pixel cap, records source/page hashes and page order, and saves an archival copy of each PNG. It saves `image-inputs.json` and `invocation.json` with hashes before execution and checks the original source/image bytes after execution. Stdin is closed to prevent inherited piped input from supplementing the recorded prompt.

The scorer recomputes receipt, invocation and archived-image hashes, verifies one ordered attachment per physical page, and checks the runner's input-integrity/completion result. `image_input_status=supplied_to_cli` means those CLI inputs are established; it **does not assert server-side receipt, model attention, semantic correctness or verified inspection**. Agent-authored ledgers and correct answers cannot substitute for these records. `prepared_only`, `not_captured` and `unavailable` remain distinct; unestablished rates are undefined, never 100%. Missing/changed required evidence fails scoring without erasing workbook/raw scores. Old runs have no such receipt and remain `not_captured`.

The receipts are provenance records maintained by the evaluator, not cryptographically signed attestations against a malicious evaluator. Do not aggregate assisted and autonomous modes as equivalent reading-route accuracy. This iteration does not resolve first-response reminder timing or provide an automatic semantic audit of image attention.


### Cheque parties and same-page invoices (0.3.7)

`format-parties-v1` (and unit-corrected `format-parties-v2`) adds explicit Payee/Payer workbook and raw-field checks over the existing public format-pack.pdf. It keeps the amount-focused custom to test whether standard payment parties are still read. The no-overwrite generator is `eval/tools/make_party_case.py`; older format references remain unchanged. The v1 live run exposed a legacy reference omitting the displayed unit; keep that failure. Version 2 retains the same PDF/custom and adds the unit required by the existing extraction contract, with a fresh execution. See the 0.3.8 report for exact artifact hashes and limited evidence. Deterministic controls detect omitted/swapped parties and a bank substituted for the drawer. Unreadable names remain blank with field-specific review reasons.

Workbook scoring derives Document occurrence from document-row order within File/Pages/Document type, then joins type/occurrence to line/custom sheets through a unique File/Document ID. This lets two same-page Invoices have independently matched lines even if those line rows are reordered. Duplicate IDs do not resolve to an arbitrary document; ordinals are never selected by the value being scored. Reference authors must state source reading order; a reversed document order is not silently matched by amount. Document occurrence is a derived evaluator identity, not a new workbook output column.

Owner adjudication of private references is scoped to the values actually reviewed. Keep earlier locks, references and scores unchanged; save revisions separately and label reused sources as known content. Confirming one amount-ending convention applies only to the named document, not all suppliers or batches. New fields do not retroactively become part of older accuracy denominators.

For a later package, `holdout.freeze_regression(...)` verifies the original lock and exact source bytes, then freezes a separate case with `evaluation_kind=known-source-regression`. Include the scoped owner review and authorization records in `review_files`. Use `owner-verified` only when all configured reference cells were reviewed; otherwise use `mixed-owner-and-provisional` and publish the two scopes separately. This does not turn a reused source into an unseen holdout or transfer the old package's evaluation.

Private continuations require a recorded human policy reply in that exact conversation; a public scripted response cannot substitute. Source disclosure still needs its own authorization. If an extraction execution fails, `conversation.py continue CONVERSATION --case SAME_CASE --retry-failed` keeps the failed attempt and starts a separate workspace and attempt ID in the same session. It accepts only incomplete executions, not completed predictions with low accuracy. Retain the timeout/error in the report, report the retry separately, and never treat a transport failure as a zero-accuracy extraction or silently choose the best completed prediction.

For direct private repeats without a public bootstrap, use `conversation.py start-private --case ABSOLUTE_FROZEN_CASE --model USER_SELECTED_MODEL --provider PROVIDER --python INTERPRETER`. Each invocation creates a new session and workspace, verifies the private lock against the installed package and leaves answers outside that workspace. The opening names only the source and settings, without examples or expected values. It waits for an actual human reply in that exact session; scripted public replies cannot resume it. Locks and package bytes are rechecked before the reply invokes document work. Source disclosure still requires authorization. Run the normal `reply` and `report` commands for every session, retain all predictions and report repeatability separately from accuracy. The reusable skill package and its model recommendation are not changed by this harness entry point.

A different case can continue after an incomplete extraction when that conversation already has its policy response. Its metadata records `after_failure`; the new prompt limits work to the new workspace. This does not recover or mark the preceding attempt complete. A failed opening without a policy response still cannot proceed to document work.

`--retry-failed` also finds an earlier incomplete case in that same conversation after other batches have run, including the opening batch whose policy turns do not carry a case ID. Archived execution metadata fills that gap; later retry turns retain their order. Any recorded completed execution for the requested case prevents this recovery path; it cannot select away an inaccurate completed prediction. `--timeout-seconds` records and enforces a per-attempt deadline (default 1,200; allowed 1–3,600 seconds), without inheriting a stale deadline from a different attempt.

For a slow but progressing attempt, `--retry-failed --resume-work` copies its archived intermediate work into a new workspace and records the copied-file hashes. It requires exactly one archived manifest. The source, custom settings and package are freshly prepared and verified; the prior workbook and evaluator answers are not copied. The model continues that batch with the existing manifest and page renders. This is continuation of interrupted work, not an independent repeat. Earlier failure records and artifacts remain unchanged.

For diagnosed WebSocket failures, `continue ... --retry-failed --transport https` opts into HTTPS using an explicit Codex provider alias. It retains the `https://chatgpt.com/backend-api/codex` endpoint, managed OpenAI authentication, requested benchmark model and exact session. No credentials are copied into configuration and no persistent user settings change. The default transport remains unchanged. Record `codex_transport` and the invocation arguments, keep interrupted attempts, and report transport recovery separately from extraction accuracy. This fallback was tested first with a public connectivity-only prompt; a successful probe does not itself establish private-document extraction. The provider settings follow the [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

Workbook line and statement references may use `Pages`, joined from the unique parent document through File/Document ID. Requested values retain their own observation Pages; that evidence is never overwritten with parent page ranges. Duplicate parent identities leave the join unresolved.

`digit-boundary-v1` adds three public raster-only controls: a nearby table rule, a genuine leading digit and an obscured prefix. The committed source and expectations are fixed before model execution. The generator refuses to overwrite them. `eval/tools/check_digit_boundary.py --out NEW_FOLDER` runs supplied transcriptions plus four deliberate errors through raw scoring and the processor. It records an invalid custom observation as rejected, with no workbook accuracy denominator. A standard field guessed despite `unclear` remains visible in raw scoring even if processing blanks the workbook cell. These controls are not live recognition results or human handwriting evidence.

When an owner reviews a provisional value after a run, preserve the original report, lock, reference and prediction. Save the actual reply with its exact field scope and publish a separate supplement bound to those artifacts. Confirming an existing reference changes the review scope, not the original score. Do not quietly move other fields into the owner-confirmed denominator or relabel a maintainer source review as owner approval.

`cash-memo-classification-v1` contains three public native-print controls: a paid Cash Memo recording a sale, an actual payment acknowledgement, and a Tax Invoice / Receipt recording a sale. Raw scoring identifies documents by File/Pages and scores Document type directly, so a classification mistake is visible without depending on the same type for matching. Workbook scoring also checks bucket placement and two invoice line items. `tests/test_cash_memo_eval.py` checks the supplied correct transcription (raw 9 / 9, workbook 17 / 17) and injects each of the three wrong classifications. These processor/scorer checks do not establish model recognition accuracy. The fixture generator refuses to overwrite frozen documents or references.

## CLI previews and public repeated-chat runs

Google/Gemini CLI and xAI/Grok Build previews support the same `run.py --prepare-only` workspaces. Their eval adapters deliberately reject live completion claims until session/telemetry integration is tested. Prepared artifacts are not accuracy evidence. See [CLI smoke tests](cli-smoke-tests.md) for installation modes and the staged integration checks.

The [Cursor xAI baseline](evaluations/2026-10-11-cursor-xai-baseline.md) prepares the same four public cases for `invoice-reader-xai-cursor`. It reuses the xAI prompt and the existing scorer, and it does not apply Codex opening v9. A prepared workspace is not a model accuracy result. Coal raw accuracy stays not configured when the locked reference has no raw tables.

The [Cursor xAI execution scores](evaluations/2026-10-12-cursor-xai-execution.md) score IDE chats that wrote into those prepared folders. They are per-execution artifact scores with an evidence label on each run. They are a separate batch from the preparation record, whose `meta.json` files stay `prepared_only` and `valid: false`. Coal raw accuracy stays not configured. The designated Cash Memo workspace has no workbook. A verified fresh-chat baseline is still absent.

The [17–18 October 2026 Cursor comparison](evaluations/2026-10-18-cursor-xai-comparison.md) is a separate fresh-chat sample for xAI family 0.1.2. It compares no skill, frozen Cursor 0.1.1, and current Cursor 0.1.2 on four public synthetic files. The reported model string was Grok 4.7 256K High Fast. The 18 October CLI build is listed separately from the 17 October chats. Coal was not rerun. Grok Build was rebuilt from the shared prompt and was not run. `last_eval` stays empty. The comparison is not a general accuracy claim.

`public_repeats.py` freezes a public-only case list, package and fixture hashes before running numbered fresh Codex sessions. It uses a labelled scripted read-later reply solely for public fixtures, never a human acknowledgement. A trial is reserved before launch; failed attempts and original opening audits cannot be overwritten. Incomplete openings requiring command inspection may resume only in the exact same waiting session after a hash-bound maintainer trace review, with a separate continuation record. No inaccurate completed extraction is retried. The report retains planned versus recorded trial counts alongside the existing raw/workbook accuracy matrix. Missing or failed executions do not acquire invented cell-accuracy denominators. Coal scenarios currently configure workbook checks only; captured raw JSON alone does not create a raw accuracy score.
