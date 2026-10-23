# OpenAI policy reference

Source checked: 2026-10-08. The model recommendation is in `scripts/data/set.toml`; it is a recommendation for testing, not a claim of validated accuracy.

The opening question and waiting behaviour are defined in [chat response rules](chat-start.md). If the user has not read the guidance, point to the repository README's **Data policy** section (local checkout when available; otherwise the [repository README](https://github.com/kingwu2218/invoice-reader-skills#data-policy)). The following dated reference can help explain the scope; it does not establish that the user has read it:

> Data reminder for our recommended OpenAI model: document content read by the agent is processed by the model service. OpenAI API data is not used for model training by default unless you opt in; storage depends on the feature and account settings. See [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data). This API policy does not establish the settings of a ChatGPT subscription or a third-party tool. If you use another model, look up its applicable policy yourself.

Do not imply that the API policy applies to every route to this model. Do not promise a fixed retention period, zero retention or the user's actual training setting. Any reply to the current chat's policy question allows document work; do not require an affirmative answer. No live policy lookup is required during extraction; maintainers refresh this dated reference.
