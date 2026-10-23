# Corrected detail-table reference, v2

Reuses the unchanged two-page PDF, settings and staged replies from [v1](../dash-origin-printed-v1/README.md). All amounts are computer generated, including the handwriting-style font. This is not an unseen-source or real-handwriting benchmark.

Erratum: v1 omitted the mandatory Requested values worksheet from its workbook reference, so correct output caused two structural unexpected-row failures in each stage. Preserve v1 references and results. Version 2 adds explicit Status, source Value, Unit and Pages checks for that detail table; no expected amount, raw transcription or reply scope changes. These corrected answers were frozen before a fresh model conversation.

The first execution also exposed a scorer gap: line worksheets have Document ID but no Pages column. The scorer now joins parent document Pages through a unique File/Document ID mapping for line/statement rows only. It never overwrites observation evidence pages. The original pre-fix score is preserved; v1 is rescored on unchanged outputs, with the remaining reference defect still visible. Regression tests cover page joins, swapped values, duplicate IDs and observation pages.
