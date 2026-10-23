# Cursor xAI execution scoring, 2026-10-12

Artifact scores for IDE chats that wrote into the 2026-10-11 Cursor preparation. This is not a verified fresh-chat baseline. The preparation record stays [prepared only](2026-10-11-cursor-xai-baseline.md): its `meta.json` files remain `prepared_only: true` and `valid: false`. No prompt, frozen answer, OpenAI 0.3.16 package, or Codex opening v9 file was edited. Digit-boundary was not rerun.

The scorer is `eval/runner/score.py`. It ran on `eval/runs/2026-10-12-cursor-xai-execution` after the frozen package hash and dataset hash were checked. `valid: true` in that batch means those hashes matched and the linked workbook plus raw extraction were admitted. It does not mean a CLI session completed, and it does not mean a blind fresh chat.

On 2026-10-13 the same scorer was run again. The summary stayed 6 runs, 5 admitted, 0 cells differing between the two coal-energy executions, exit code 1. Package, xAI source, Cursor adapter, OpenAI 0.3.16, and opening v9 hashes were recomputed and matched the preparation lock. Each case digest was recomputed from the current PDF, custom settings, and locked reference and matched that lock. Each admitted workbook and raw file is byte-identical to the transcript-linked source. Baseline `meta.json` files remain `prepared_only: true` and `valid: false`.

No execution is selected as the best score. Repeats stay separate. Scored cells do not differ between the two coal-energy executions (`cells_differing_between_runs: 0`).

## Scores

Correct blanks are excluded from the accuracy denominator. Missed values are `miss`. Guessed values are `invented`. Wrong filled values are `wrong_flagged` or `silent_error`. Classification uses the reference identity and, where present, the Document type column. Coal raw accuracy is **not configured**.

| Execution | Evidence | Workbook | Correct blanks excluded | Raw | Miss | Guessed | Wrong filled | Classification |
|---|---|---|---|---|---|---|---|---|
| digit-boundary `run-1` | Linked, answer generator read before extraction | 15 / 15 | 3 | 13 / 13, blanks excluded 2 | 0 | 0 | 0 | 0; 3 / 3 document rows matched |
| coal-ocr-payment `run-1` | Linked, shared chat; opening reply not in the transcript | 21 / 21 | 14 | not configured | 0 | 0 | 0 | 0; billing 1 / 1 and other 1 / 1 |
| coal-ocr-energy `run-1` | Same shared chat as payment | 25 / 25 | 15 | not configured | 0 | 0 | 0 | 0; billing 1 / 1 and other 1 / 1 |
| coal-ocr-energy `run-2` | Linked repeat; saved beside the existing workbook. Folder-choice selection is not in the transcript | 25 / 25 | 15 | not configured | 0 | 0 | 0 | 0; billing 1 / 1 and other 1 / 1 |
| cash-memo designated workspace | No workbook in that workspace | not run | not run | not run | not run | not run | not run | not run |
| cash-memo repo-root `run-2` | Provisional; `expected.json` was read before extraction | 17 / 17 | 0 | 9 / 9, blanks excluded 0 | 0 | 0 | 0 | 0; Document type is inside the 17 / 17 |

Coal references include Needs review. Both payment and both energy executions have review true positives 2, false positives 0, and false negatives 0. The digit-boundary and cash-memo references do not score that flag, so their zero flag counts are not a review test. Unprocessed inputs on every scored workbook: 0. No missing or extra scored rows.

The scorer exit code is 1 because the designated cash-memo run stays invalid. That failure is kept.

## Evidence links

Pairing comes from the stored chat transcripts and the `process.py --out` commands in those transcripts. File names and modification times were not the pairing rule.

For publication, chat identifiers are replaced with `chat-01` through `chat-04`, and manifest folder identifiers with `run-01` through `run-05`. These aliases are consistent within this report and its JSON companion. Workstation paths are omitted; local evidence paths containing aliases are illustrative repository- or workspace-relative paths, not literal locations. Original identifiers remain only in local evidence.

| Workbook | Chat | Manifest | Raw extraction | Package | Runtime |
|---|---|---|---|---|---|
| `digit-boundary-v1/workspace/output.xlsx` | `chat-01` | `invoice-reader-work/run-01/manifest.json` | `digit-boundary-v1.json` in that run | Installed workspace package, hash matches frozen `ba89c435…` | Existing Python interpreter, pypdfium2 4.30.0 |
| `coal-ocr-payment/workspace/output.xlsx` | `chat-02` | `invoice-reader-work/run-02/manifest.json` | `coal-ocr.json` | Same frozen package hash | Same interpreter |
| `coal-ocr-energy/workspace/output.xlsx` | Same chat `chat-02` | `invoice-reader-work/run-03/manifest.json` | `coal-ocr.json` | Same frozen package hash | Same interpreter |
| `coal-ocr-energy/workspace/output (2).xlsx` | `chat-03` | `invoice-reader-work/run-04/manifest.json` | `coal-ocr.json` | Same frozen package hash | Same interpreter. The command argument was `--out output.xlsx` in that workspace. The chat then identified this run's saved file as `output (2).xlsx` because `output.xlsx` was already there |
| `output.xlsx` (repository root) | `chat-04` | `invoice-reader-work/run-05/manifest.json` (repository root) | `cash-memo-classification-v1.json` | `dist/cursor/invoice-reader-xai-cursor`, same frozen hash | Same interpreter. This is not the designated workspace |

All four admitted dataset hashes match the preparation lock. Original workbooks and raw files were left in place; the execution batch holds copies named for the scorer.

`結果.md` was written after the digit-boundary workbook. It is not an opening trace and is not used as a pass.

## Opening observation

Grader: cursor opening observation, separate from Codex v9. v9 was not applied. Text in one message cannot time a pause; turn order is recorded where the transcript has it.

| Chat | Exact question | Both choices | Reply in stored user messages | Pause | Extra confirmation | Yes-only gate | Fresh-chat baseline |
|---|---|---|---|---|---|---|---|
| `chat-01` | Once, in the opening message | Present | "Yes, I have read it." | Question turn, then that reply, then document reads | None observed | None observed | Unverified. The same chat read `eval/tools/make_digit_boundary_case.py` before writing the extraction. Later reads of `expected.json` in this transcript are scoring turns after `output.xlsx` existed. The chat root was the repository |
| `chat-03` | Once, in the opening message | Present | "Yes, I have read it." | Question turn, then that reply, then document reads | None observed for the policy question. A later folder question has no stored selection | None observed | Unverified. Repository-root chat. Repeat of coal-energy. File-name globs ran while locating the skill, before the reply; workspace `custom.md` was read after the reply |
| `chat-02` | Present in the message and again in AskQuestion | Present in both | Not stored | Not verified | Two channels | None observed | Unverified. Repository-root chat. One prompt wrote both the payment workbook and the first energy workbook |
| `chat-04` | Present in AskQuestion | Present in AskQuestion | Not stored | Not verified | AskQuestion channel | None observed | Unverified. Also read `eval/scenarios/cash-memo-classification-v1/expected.json` before extraction |

A stored reply records the wording only. It is not verified reading or consent. The prepared scripted fixture was not the reply in these transcripts.

Missing opening records, if a later export exists:

- Chat `chat-02`: the user-role policy reply. AskQuestion was called; its selection is not in the transcript. A later assistant sentence saying the reply was “Yes, I have read it.” is not that user trace.
- Chat `chat-04`: the same missing user-role reply.
- Chat `chat-03`: the policy reply is stored. A later question, “Which folder should I read?”, has no stored selection. Workbook pairing uses the `process.py` command, which names the energy workspace and manifest folder `run-04`.

Workbook pairing for the first two chats does not depend on the missing policy reply. Those openings stay unverified without the export.

## Cash Memo workspace

The designated folder `eval/runs/2026-10-11-cursor-xai-baseline/cash-memo-classification-v1/workspace` has no `output.xlsx` and no `invoice-reader-work`. The repo-root workbook above is a different execution.

A new folder for one new chat was copied from that workspace, containing no `expected.json`, no `output.xlsx`, and no earlier extraction. Its public path alias is:

`eval/runs/cash-memo-new-chat/workspace`

The opening prompt's public path alias is:

`eval/runs/cash-memo-new-chat/PASTE-OPENING.txt`

For a local run, open the actual local workspace as the Cursor root and paste its stored opening prompt. The paste is the original preparation prompt, including the evaluator-supplied Python path. It does not contain answer values. The public aliases above omit the original local folder name.

## Runtime

Recorded runtime: an existing Python interpreter, Python 3.14.5, pypdfium2 4.30.0, Pillow 12.3.0, openpyxl 3.1.5. The scripts declare `pypdfium2>=5.13,<6` for a managed `uv` run. `uv` was not used. The evaluation prompts told the chats to use this interpreter. Its workstation path is omitted from the public report. This is evaluator setup assistance on an existing machine, not a clean install of the declared dependency range.

CLI image attachments were not captured. IDE image reads are not a harness attachment receipt.

## Unchanged controls

| Artifact | Hash |
|---|---|
| Cursor package | `ba89c43560d1cfc8362135ea9465be5f44f4769f338ca6522501df1fa4527657` |
| `skills/xai` | `46dc6e841526797800aaec99b806514055965619ed5598de1615744ef66cb175` |
| `adapters/cursor` | `d965459316b20034521c2ff0e572d7a874106f936fac81dfbea25ec8f64bb588` |
| OpenAI 0.3.16 package | `2f03d23ca01d755c4cf6ed94c752d809ef03df201a94a26d8b8c49dc11bd7743` |
| `eval/runner/opening_v9.py` | `4e4e083323835f3a8579b818a5b64b7af49e03e482aecd420b57a2dbd59a6c16` |

Model requested in the preparation note: Grok 4.7, effort High. No tool init event reported a model ID or effort. Names passed to `--model-reported` are self-reported. Provider and account route: unknown.
