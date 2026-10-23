# User-defined extraction settings

`custom.md` belongs in the user's working folder, outside the installed skill. Read existing settings and explicit user requests first. Explain columns in ordinary finance language; maintain technical keys yourself. Do not ask the user to write this table.

Use `new_custom.py` for a new file. Preserve its Document buckets section. Add rows under Requested fields in the order the user wants:

| Key | Column | Find | Values | Required |
|---|---|---|---|---|
| invoice_ref | Invoice number | The number labelled Invoice No. on the invoice itself | one | yes |
| coal_energy | Energy Level of Coal | Energy Level of Coal on the lab certificate; keep its printed unit and sample identifier | many | no |

The keys are stable lowercase identifiers using letters, digits and underscores. Column is the user-facing name. Find states the meaning and printed evidence to look for. Values is `one` or `many`. Required is `yes` only if absence should be flagged for review. Use semicolons instead of vertical bars inside table cells.

Fields may describe any printed fact, not only finance fields. Do not invent scientific equivalences or measurement bases: if several labels could answer an ambiguous request, ask which is wanted or retain the explicitly requested alternatives with their context. Do not average, sum, convert units or select the highest value unless a separately supported calculation workflow has been requested; this skill records printed information.

An empty Requested fields table uses the standard invoice/payment/other outputs. With requested fields, Requested data is an additional first sheet showing only the requested columns plus source and review columns. Requested values retains each observation's original value, unit, context, page and evidence. Standard sheets remain available for arithmetic and source review. `one` cannot silently discard a second matching value: clarify the requirement or change to `many` with the user's direction.

For an amount or measurement, retain its associated printed unit/currency separately from its numeric notation. The summary includes that unit and any requested printed context; the detailed sheet keeps the parts separate. State which sample/reference context matters in Find when the user requests it. See the [extraction contract](extraction.md) for the display rule.

After the user replies to the chat's policy question, show the proposed columns briefly. Clear user instructions count as confirmation of extraction requirements; set `Confirmed by user: yes` when the settings represent those instructions. This field never records policy acknowledgement. Ask about fields only to resolve missing requirements or ambiguity; do not add a model-mismatch confirmation. Do not overwrite an unrelated existing configuration.

Buckets control standard sheet placement, not eligibility for custom extraction. Apply requested fields to every document; use an absent observation if no matching information is printed. A certificate in a combined file may be a separate Other record; do not copy its facts into an invoice record without a printed link.
