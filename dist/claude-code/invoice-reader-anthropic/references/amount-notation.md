# Terminal amount dashes

Identify the amount and its terminal ASCII dash at field level. A handwritten amount ending is positive by default (`360-` becomes numeric `360`); no confirmation is needed. Computer-generated endings require a user interpretation before numeric conversion. Unknown origin also stays as text pending confirmation. A scan or OCR output can contain either kind, and a page may mix them. The document-level `handwritten` flag is not sufficient.

Ask in finance language, naming the affected source/page/field: “On page 2, does the computer-printed Total `360-` mean positive 360, with a dash ending the amount, or negative 360?” Group equivalent cases only when the scope is clear. Until answered, preserve source strings, flag affected fields, skip their arithmetic and continue other work. An existing scoped reply need not be asked again. Record field-specific replies as described in [the extraction contract](extraction.md). A user can override the handwritten default; conflicting source evidence remains visible for review. Parentheses, a leading minus and CR retain existing rules.

Software examples explain why confirmation is needed; they do not supply the user's answer:

Primary documentation checked 2026-10-09:

- [Oracle Data Management: nonstandard numeric sign conventions](https://docs.oracle.com/en/cloud/saas/enterprise-performance-management-common/erpia/nonstandard_numeric_sign_conventions.html) interprets a trailing minus as negative in its input formats.
- [SAP Group Reporting: handling negative amount formatting](https://help.sap.com/docs/SAP_Group_Reporting_Data_Collection/64dc0138def94c6696ee1ed4701d53f7/dbca9299d79541e6aef6a390bacce25d.html) describes source systems that place the negative sign after the amount.
- [Microsoft NumberNegativePattern](https://learn.microsoft.com/en-us/dotnet/api/system.globalization.numberformatinfo.numbernegativepattern) supports `n-` and `n -` among configurable negative-number patterns.

These are software-format examples, not a verified country-by-country guide to handwriting. No such reliable handwriting list was established in this review. Country, language, currency, a vendor logo or the mere possibility of a trailing-minus format is insufficient to establish a field's origin or replace user confirmation. The parser still supports comma thousands and dot decimals only; do not silently reinterpret other separators or malformed/multiple signs.
