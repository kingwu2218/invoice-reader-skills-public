# AGENTS.md

Public instructions for agents using or modifying a clone of this repository.
These instructions do not invoke the extraction skill by themselves. For document
work, use the selected package's complete SKILL.md and its referenced guidance.

## Repository purpose

This repository exists to create practical, usable skills that help accountants
improve the effectiveness and efficiency of invoice extraction.

## Understand what users need before compliance

Before working on compliance (privacy notices, confidentiality, regulatory requirements), find out as much as possible about what users actually need. Compliance work should serve real use, not a guess about it. When a design choice rests on an assumption about accountants' needs, name the assumption and ask, rather than build on it.

## Respect the user's workspace

- Keep customer documents, custom.md, company profiles, output workbooks and raw
  transcripts in the user's document workspace, outside tracked source files.
  An ignored file is not authorization to upload its contents.
- Ask the user before committing or pushing their changes. Extraction requests
  do not authorize publishing documents, creating releases or changing visibility.
- Before sharing a report, remove actual workstation paths and private chat,
  session and run identifiers. Use consistent aliases and relative public paths;
  keep any original-to-alias mapping local and ignored. Preserve evidence and
  reported results without inventing or silently correcting values.
- For source contributions, follow [the publication review guide](docs/publication-review.md).
  Passing a scan is not permission to publish. The upstream owner's local
  maintenance instructions and machine-specific hooks are not distributed.

## Model families and tools

Maintain one prompt source per model family in `skills/openai/`, `skills/anthropic/`, etc. Recommend one model per family; other models reuse the same prompt. Tool adapters own installation, commands and page-reading details. Shared contracts and processing live in `core/`; generated packages live in `dist/`.

- Users choose a package from the README. Do not create maintained prompt forks per model version.
- Distinguish recommendations from evaluation evidence. Record exact model IDs, providers, tools and artifact versions in results. Changed packages remain experimental until evaluated.
- Named experimental packages use explicit invocation. Only promote an automatic default after evaluation; never install competing automatic packages for a tool.
- Do not add a confirmation gate merely because the model is non-recommended or unknown. Do not invent model identities.
- At the first skill invocation in each new chat, ask exactly "Have you read the Readme about the data policy for your model?" and offer "Yes, I have read it." and "No, but I will read it before I upload any confidential data". Any user reply allows the original task to continue; do not require Yes or repeat confirmation for No/uncertainty. Wait only while no reply has arrived. Record response received, not verified reading or consent. This supersedes the affirmative-only gate. Ask once per chat; do not reuse another chat's response or custom.md. README guidance retains its provider/account scope.
- A brief skill-use announcement may precede the question (owner decision A). Respect task changes or stop requests in the user's reply; a policy response does not authorize unrelated uploads.
- Ask about extraction needs in language finance users understand. `custom.md` may request arbitrary information, including certificate measurements. Invoice fields are defaults, not a limit.
- Preserve printed values, units and source evidence. Custom fields cannot override the rules against guessing or silently correcting values.

## Never force a model on the user

Users choose their model for cost and access reasons. A skill set adapts to the user's choice; it never overrides it.

- A skill set must not switch or pin the model: no `model` field in SKILL.md frontmatter, no forked subagent pinned to a model, and no equivalent setting in any other harness.
- A skill may record its model but never gates work on matching the recommendation.
- The model the agent reports is self-reported. Never describe it to the user as verified.
