# CLI integration handoff

MVP scope (2026-10-11): finish ChatGPT / OpenAI through Codex CLI first. Gemini and Grok integration is the next phase; their pending checks below do not block the OpenAI experimental MVP.

The OpenAI/Codex package has a staged evaluator. Google/Gemini CLI and xAI/Grok Build 0.1.0 are locally buildable previews; their model execution and accuracy are not validated. A preparation-only adapter always returns completed=false. No recommendations or model overrides are embedded in these new skills.

## Local work already available

- One family source each in skills/google, skills/xai and skills/openai, with shared scripts and contracts bundled by tools/build.py.
- Explicit-only delivery: Codex invocation metadata, Grok disable-model-invocation, and Gemini manual file-path loading outside discovery directories.
- Dated Google/xAI policy references linked to actual CLI/account routes.
- The shared preparer can create identical public payment/energy scenarios for either preview without credentials or model traffic.
- tools/cli_readiness.py discovers executables on the current PATH. --versions optionally runs bounded version commands. It does not install, authenticate, call models or inspect account settings; a missing PATH entry does not prove absence.

```text
python tools/cli_readiness.py --versions
python tools/build.py
python tools/check.py
python eval/runner/run.py --package invoice-reader-google --prepare-only --runs 1 --cases coal-ocr-payment coal-ocr-energy --python PYTHON
python eval/runner/run.py --package invoice-reader-xai --prepare-only --runs 1 --cases coal-ocr-payment coal-ocr-energy --python PYTHON
```

PYTHON is an existing interpreter. Follow README installation instructions for the complete generated package. Prepared workspaces are not model runs; expected answers remain outside them. Do not copy references into the tested chat.

## Verification on the target CLI

Use a public prepared workspace and the model/account chosen by the user. Record CLI version, requested and CLI-reported model separately, provider/authentication route, package/dataset hashes and any pre-existing context. Tool names do not determine active model identity. Consult [Gemini CLI headless output](https://geminicli.com/docs/cli/headless/) or [Grok Build sessions and scripting](https://docs.x.ai/build/cli/headless-scripting) for current interfaces; documentation alone does not pass a smoke test.

1. Start a fresh chat and explicitly load the prepared package. Check that the policy question and exact choices appear once before workspace/document access. Capture the trace. For a public automated test, label a read-later response as scripted test data. Private documents always require a real reply in that chat and destination authorization.
2. Resume the exact session ID with the reply. Confirm no repeated question, and prove that a subsequent turn stays in the same session. Never substitute the latest session.
3. Verify a shell command, a file write and actual image content returned by the exposed visual tool. PDF rendering or OCR output alone cannot establish visual reading. Record unavailable features instead of guessing them.
4. Process the public scenario with unchanged packaged scripts and save extraction JSON, manifest, reading review and workbook. Run the existing scorer outside the model workspace. Save tool events, completion/failure and usage if exposed.
5. Test the same source with the second custom purpose in a fresh chat. Then run three fresh chats per frozen case once the staged adapter is validated. Keep failed attempts and correct blanks separate from accuracy denominators.

Gemini/Grok executables were not found on the current PATH; their authentication was not inspected. Usable CLI access and the user's selected model/account remain to be supplied or verified. No third-party CLI was installed and no private files were sent to those providers. Recommended models can be chosen after evidence from the user's accessible models.

## Cursor experimental package

`invoice-reader-xai-cursor` is a second tool package for `skills/xai/`, not a Grok 4.7 prompt fork and not a claim that `dist/grok-build/` runs in Cursor. Cursor docs reviewed on 2026-10-11 put explicit skills at `.cursor/skills/<name>/` with `disable-model-invocation: true`. Rules can also load manually with `alwaysApply: false` and no description or globs, but this package is a skill so it is not included in every chat. Slash invocation attaches to one message; Custom Mode (Alt+Enter on Windows, Option+Enter on macOS) is the documented way to keep it for the session.

The CLI docs also describe `agent create-chat` and `--resume [chatId]` for a fresh chat and exact continuation. That method is usable only when `agent` is installed. `tools/cli_readiness.py` probes `agent --version` and does not install it. If the executable is absent, prepare workspaces with `eval/runner/cursor_session.py` and do not treat the maintainer chat as a blind extraction. The adapter never passes `--model` or an effort flag. Score completed workbooks with `eval/runner/score.py`; do not grade the opening with Codex v9.

## Repeatable OpenAI public evaluation

```text
python eval/runner/public_repeats.py plan eval/runs/MY_BATCH --cases digit-boundary-v1 cash-memo-classification-v1 coal-ocr-payment coal-ocr-energy --repeats 3 --model YOUR_SELECTED_MODEL --provider ACTUAL_ACCOUNT_ROUTE --python PYTHON
python eval/runner/public_repeats.py run eval/runs/MY_BATCH --trial 1
python eval/runner/public_repeats.py report eval/runs/MY_BATCH
```

Run each numbered trial once. The plan freezes package and public source/custom/reference hashes. Each trial opens a fresh chat and replies with the explicitly labelled public read-later fixture. It rejects private paths, modified plans/packages/fixtures and overwriting attempts. It does not attach page images before the reply or pass expected answers to the model.

An opening with commands requiring inspection stops before the scripted reply. A maintainer can inspect its trace, then save trace-review.json in the opening turn folder with reviewer, reason, no_document_work_observed=true, stream_sha256 and snapshots_sha256. Only after that review use `resume-reviewed BATCH --trial N`. This continues the exact waiting session, preserves the original failure and automatic opening score, and records the continuation separately. It cannot rerun a completed extraction or replace an inaccurate prediction. Missing results remain visible in the planned-trial count. These hashes bind a review to evidence; they do not authenticate the reviewer or turn model statements into verified facts.
