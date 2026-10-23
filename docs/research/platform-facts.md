# Platform facts

Checked 2026-10-06 against the official docs linked in each section. Re-check before relying on any item after a harness update.

## 1. Agent Skills format

Source: [agentskills.io/specification](https://agentskills.io/specification)

- A skill is a folder with a `SKILL.md`; optional `scripts/`, `references/`, `assets/`.
- `name`: 1–64 chars, lowercase `a-z`, `0-9` and hyphens, no leading, trailing or double hyphen. **Must match the parent folder name.**
- `description`: 1–1024 chars, says what the skill does and when to use it.
- Optional: `license`, `compatibility` (≤500 chars), `metadata` (string→string map), `allowed-tools` (experimental).
- Body: under 5000 tokens and 500 lines recommended. Reference files one level deep from `SKILL.md`, loaded only when needed.
- Validator: `skills-ref validate ./my-skill`.

**Consequence:** the default set's folder must be named `invoice-reader`. A model-version set's folder carries the version, e.g. `invoice-reader-claude-sonnet-5-5`. The build step that ships a version set as the default must rename the folder and the `name` field together. Set version and evaluated model ID go in `metadata`, because the spec has no version field.

## 2. Claude Code skill loading

Source: [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)

- Locations: enterprise, personal (`~/.claude/skills/`), project (`.claude/skills/`), nested, plugin, claude.ai account.
- Same name in two places: enterprise beats personal, and **personal beats project**.
- The description, together with `when_to_use`, is truncated at 1,536 characters in the skill listing. Put the key use case first.
- `disable-model-invocation: true` keeps the description **out of context**. The skill runs only when the user types `/name`. This is how specific sets stay manual.
- Claude Code accepts the extra frontmatter fields `model`, `effort`, `context`, `hooks`, `paths` and `shell`. We do not use `model` (see AGENTS.md).
- `${CLAUDE_SKILL_DIR}` resolves to the skill folder. Use it to call bundled scripts from any working directory.
- `AGENTS.md` is read only when there is no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` in the folder or above it ([memory docs](https://code.claude.com/docs/en/memory)).

## 3. Knowing the model

Sources: [model-config](https://code.claude.com/docs/en/model-config), [hooks](https://code.claude.com/docs/en/hooks)

- There is no `$CLAUDE_MODEL` variable. Only `SessionStart` hooks may receive `model`, and the docs say it is not always included.
- Users can see the active model themselves in `/status` and in the status line (`model.id`).
- An alias is not one model. `sonnet` resolves to Sonnet 5.5 on the Anthropic API, to Sonnet 4.6 on Claude Platform on AWS, and to Sonnet 4.5 on Bedrock, Google Cloud and Foundry.
- Inside a session, the only practical source is the model ID in Claude Code's system prompt, as self-reported by the agent. This is observed behaviour, not a documented contract.
- A gateway or proxy can route a configured model name to a different model. Nothing in the session can detect that.

## 4. Headless eval runs

Sources: [headless](https://code.claude.com/docs/en/headless), [cli-reference](https://code.claude.com/docs/en/cli-reference), [env-vars](https://code.claude.com/docs/en/env-vars)

- `claude -p "<prompt>" --model claude-sonnet-5-5` pins the model. Use the full ID, never an alias.
- `--output-format json` includes a per-model cost breakdown, and `stream-json` starts with a `system/init` event that names the model. **The harness rejects any run that used a model other than the pinned one.**
- `--bare` skips personal and project skills, hooks, plugins, MCP and CLAUDE.md. It still loads skills from an `--add-dir` folder, but **Claude is not given the skill listing**, so bare mode cannot test automatic triggering; it can only test `/invoice-reader`. Bare mode needs `ANTHROPIC_API_KEY` (or `apiKeyHelper`) and never uses a subscription login.
- Without `--bare`, a `-p` run loads personal skills. A personal `invoice-reader` would shadow the project one under test. The harness must refuse to run if one exists.
- Useful flags: `--max-turns`, `--max-budget-usd`, `--no-session-persistence`, `--permission-mode dontAsk` with `--allowedTools`, `--setting-sources`.
- `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) lets scripts use a subscription instead of an API key.

## 5. skill-creator eval tooling

Source: the skill-creator skill (Apache-2.0), in the `claude-plugins-official` marketplace.

- `scripts/run_eval.py` tests **triggering only**: it runs `claude -p --model <id>` and checks whether the description caused the skill to load. Reusable for our trigger eval.
- The output eval runs with-skill and baseline (no skill, or the previous version) side by side, grades with a grader agent, and aggregates with `scripts/aggregate_benchmark.py` into pass rate, time and tokens.
- Its runs use subagents, not one fresh pinned headless session per document. Our extraction eval therefore needs its own runner. We reuse the with/without-skill design and the review viewer where they fit.

## 6. Licences (repo licence: Apache-2.0)

| Package | Use | Licence | Fits Apache-2.0? |
|---|---|---|---|
| pypdfium2 5.14.0 (2026-10-04) | Render PDF pages to images | Apache-2.0 or BSD-3-Clause; bundled PDFium is BSD-style | Yes |
| PyMuPDF 1.28.2 | (rejected) | AGPL-3.0 or commercial | No: AGPL would bind users of the scripts |
| openpyxl 3.1.5 (2024-06-28) | Write .xlsx | MIT | Yes; last release 2024 |
| skill-creator scripts | Eval tooling | Apache-2.0 | Yes, with attribution |

Sources: PyPI pages for [pypdfium2](https://pypi.org/project/pypdfium2/), [PyMuPDF](https://pypi.org/project/PyMuPDF/), [openpyxl](https://pypi.org/project/openpyxl/).

## 7. Not yet verified

- Whether Codex CLI and Gemini CLI tell the model its own ID, and their equivalent of `disable-model-invocation`.
- Whether `--setting-sources project` keeps personal skills out of a `-p` run.
- How users without Python get the scripts' dependencies (plain `pip`, `uv`, or something else).
