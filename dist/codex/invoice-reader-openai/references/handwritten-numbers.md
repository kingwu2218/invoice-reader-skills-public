# Verify handwritten number boundaries

Apply this to handwritten amounts and requested handwritten numeric measurements before saving them. Use the adapter's existing image-reading tools; do not change the source or install another reader for this check.

First locate the field and its label on an upright page. Then inspect one local enlarged view of the relevant amount block, retaining the label, currency/unit, complete token, surrounding rules and adjacent rows. Several nearby fields can share this view. Correcting page rotation is preparation, not a substitute for local inspection. Do not crop away the context needed to distinguish a digit from a line.

Read the local token afresh before comparing it with the first reading. Check its left and right boundaries: which strokes form each character, and which continue above or below the writing into a rule, crease, adjacent cell or other mark? Trace a questionable stroke through that surrounding space. A separate leading digit needs visible character evidence; a tall stroke is not automatically a digit. Equally, retain a genuine digit beside a rule rather than preferring the shorter number. Do not erase, mask or redraw lines to create cleaner-looking evidence.

Record the field/page, the local-view artifact, both readings and the visible reason for resolving any boundary question in `reading-review.json`. These are two views read by the same model, not independent verification. Agreement, a repeated amount elsewhere, a paid stamp or a balancing calculation cannot establish the token's characters. Read each labelled amount from its own source position.

If the complete token still has more than one plausible reading after this local check, leave that field blank and mark it unclear, with a field-specific reason describing the unresolved character position. Preserve candidate readings only in the reading-review evidence, not as a guessed raw value or workbook amount. Continue the other fields. A generic handwriting warning does not justify entering an unresolved number. Preserve readable currency symbols, signs and units; apply the existing amount-notation rules only after transcription.
