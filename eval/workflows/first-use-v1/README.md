# First-use workflow references, version 1

These predeclared public references test the installed OpenAI skill in three fresh Codex CLI sessions outside the repository. The package and references are frozen before execution. Expected answers remain in the evaluator's batch directory, never in the model workspaces.

- Chat 1: `coal-ocr.pdf`, payment follow-up. Then `coal-scan.pdf` as a second batch in the same session, retaining the earlier workbook and settings.
- Chat 2: the same `coal-ocr.pdf`, certificate energy/moisture comparison.
- Chat 3: `coal-ocr.pdf`, payment follow-up again in a new session.

The source files are existing known synthetic fixtures, not unseen documents or human handwriting. The second batch changes the PDF format but reuses the same business content. This protocol has two initial payment trials and one energy trial, not three repeats per purpose.

Only the complete generated skill and source PDF are installed initially. There is no prefilled custom.md, company profile, extraction, answer file or page image. The ordinary-language request specifies the desired column names and optional fields. The model must create its own settings and extraction, set up usable tools, read the document, preserve the printed inconsistent total, and produce Excel without the evaluator editing its work.

`payment.json` and `energy.json` preserve the workbook expectations from the earlier coal scenarios, using user-facing field labels as the Requested values identity. New raw expectations independently compare source strings. The internal custom-field key is chosen by the model; the evaluator maps that key to the exact label in its generated custom.md. Missing/wrong labels still fail, and values are never rewritten to fit references. Historical reference files are not changed. Correct blanks are excluded from headline denominators.

No company profile is requested; the direction review is expected. Invoice identifiers are requested only from the invoice itself, not a certificate's reference to another document. Energy observations retain both samples, labels and units, while absent moisture remains absent. The standard workbook sheets remain part of the checks.

## Run

Use an existing authenticated Codex CLI and choose the benchmark model yourself. `OUTSIDE_REPO_NEW_FOLDER` must not exist and must be outside the repository and its ancestors. Use a fresh batch name.

```text
python eval/runner/first_use.py plan eval/runs/MY_FIRST_USE --workspace-root OUTSIDE_REPO_NEW_FOLDER --model YOUR_MODEL --provider ACTUAL_PROVIDER_ACCOUNT_ROUTE --transport https
python eval/runner/first_use.py start eval/runs/MY_FIRST_USE --trial 1
python eval/runner/first_use.py reply eval/runs/MY_FIRST_USE --trial 1
python eval/runner/first_use.py followup eval/runs/MY_FIRST_USE --trial 1
python eval/runner/first_use.py report eval/runs/MY_FIRST_USE --out docs/evaluations/NEW_REPORT.json
```

Run `start` and `reply` for trials 2 and 3 too. Each action reserves a single attempt; an existing attempt cannot be overwritten, including on failure. The only automated policy reply is the labelled public test fixture "No, but I will read it before I upload any confidential data". It is never human consent and this runner has no private-source input option. A missing question/choice, observed workspace change or unrecognised pre-reply command stops automatic continuation. Additional opening prose remains a separate review diagnostic, not an automatic format pass.

Run `report` after the planned actions; it writes aggregate JSON and a matching CSV, refuses existing destinations and keeps unscored values undefined. Detailed model traces, workbooks and local paths stay in ignored batch storage. The report records execution-time harness hashes separately from its current reporter hash. A core delivery completion is not an automatic opening-format pass or a general accuracy qualification.

For the owner-approved Codex format that permits one necessary waiting explanation and source link, also run:

```text
python eval/tools/review_first_use_openings.py eval/runs/MY_FIRST_USE --out docs/evaluations/NEW_OPENING_REPORT.json
```

This adds a separate report using the plan's declared opening contract, preserving earlier grades. Acceptance requires the matching session's actual host disclosure instruction, the ordered exact question/options, at most one recognised explanation linked to the installed skill, and observed waiting. Unknown wording still requires review. The initial 0.3.15 v3 grades were assigned after the owner approved the new format on seeing those openings; they must be labelled retrospective. The extraction references and scoring do not change.

New plans now freeze `codex-opening-v9`, its grader hash and its v3/v4/v5/v6/v7/v8/workflow-audit dependencies before execution. They retain all applicable historical grades alongside v9 diagnostics. Grader or dependency changes invalidate continuation. Existing plans retain their declared contract and dependency set; the report command selects that version, never silently upgrades it. An explicit `--grader codex-opening-v9` on an older batch is supplementary retrospective grading.

V4 recognises bounded paraphrases of a single waiting explanation, including `require me to`, `says to`, direct quotations, and `according to`/`as required by` forms. Acceptance still requires a relevant link to the installed entry or chat-start reference, matching-session host-rule evidence, the exact question/options in order, and observed waiting. Additional confirmation, Yes-only conditions, multiple explanations, unrelated source links and unrecognised clauses do not automatically pass. Source-path text is not mistaken for visible instructions. Deterministic positive/negative and appended-condition cases live in `tests/test_opening_v4.py`; they are grading tests, not new model accuracy evidence.

`workflow-audit-v2` accepts presentation-only Markdown and static, combined PowerShell reads of installed skill instructions. It requires both exact choices and one exact question. Historical opening scores remain unchanged. The helper `eval/tools/review_openings.py` can write separate v2 diagnostics for an older public-repeat batch.

V5 retains v4's protections and additionally recognises a quoted waiting rule followed by one bounded application clause in the same paragraph. Both clauses must match; extra confirmation, Yes-only conditions, unrelated instructions and a further sentence cannot pass through substring matching. See `tests/test_opening_v5.py` for positive and negative quote/application cases, inherited evidence checks and appended-condition tests. Quotes and application prose are evaluated as visible instructions; a quotation does not exempt a Yes-only requirement from rejection.

The runner records exact session resume, preserves original outputs, checks package/source hashes and collects only the newly created batch manifest. It captures the exact session rollout when available and counts image content returned by a matching image-tool call. This establishes observed tool-returned pixels, not model attention or field accuracy. Missing telemetry remains unavailable. Local host tooling, authentication and global instructions may still be present; this is not a new operating-system installation.

V6 additionally accepts the reverse order: one complete source-linked application, then one quoted waiting rule. Both are independently validated with the preserved recognisers; negative guards still cover the entire visible paragraph. No substring-only acceptance or exemption for conditions inside quotes is introduced. See `tests/test_opening_v6.py` for both-order positive cases, unsafe prefixes/quotes/suffixes and source/host/waiting checks.

V7 accepts `/C:/...` source-link spelling on Windows by removing exactly one slash before an absolute drive prefix, then resolving and matching only the installed SKILL.md or references/chat-start.md. It rejects traversal, foreign chat/drive/file targets, UNC/device paths, drive-relative names, alternate streams, encoded path spellings and symlink/junction escape. Only the target is canonicalised internally; visible prose and original evidence are preserved. See `tests/test_opening_v7.py` for native-path aliases, negative paths, simulated resolved symlink targets and every existing grammar/negative fixture with a slash-drive link.

V8 recognises the two bounded prose variants `require this question and a reply` and `before I can begin/start`. Link labels/targets and double-quoted rules are protected; only those prose fragments are mapped to existing grammar before whole-explanation revalidation. Extra confirmation, Yes-only conditions, another reply, appended requirements and unsafe sources remain reviewable. `tests/test_opening_v8.py` covers new positive and near-negative cases, both link spellings, inherited path/host/waiting protections and rewrite boundaries.

V9 accepts prose `one reply/response` by mapping only that determiner to existing grammar and revalidating the entire explanation through v8. `one more reply`, additional/another replies, only/affirmative restrictions and added actions remain rejected. Links and double-quoted instructions are protected. `tests/test_opening_v9.py` covers the complete inherited language matrix with both path spellings, new near-negative cases, source/host/waiting constraints, simulated source escape and rewrite boundaries.
