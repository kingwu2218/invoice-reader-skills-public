# Anthropic policy reference

Policy reference carried forward from the repository's 2026-10-07 research; see the official [Claude Code data usage policy](https://code.claude.com/docs/en/data-usage) for current terms. Recommendation/provider metadata is in `scripts/data/set.toml`.

The opening question and waiting behaviour are defined in [chat response rules](chat-start.md). If the user has not read the guidance, point to the repository README's **Data policy** section (local checkout when available; otherwise the [repository README](https://github.com/kingwu2218/invoice-reader-skills#data-policy)). Explain when needed that document content the agent reads is processed by its model service, and training/retention settings depend on account and provider. Do not invent account settings or retention guarantees. This reference concerns the recommended Anthropic model/provider, not every third-party route. Users of another model look up its applicable policy themselves.

Any reply to the current chat's policy question allows document work; do not require an affirmative answer. Do not switch models or introduce a separate model-mismatch confirmation.
