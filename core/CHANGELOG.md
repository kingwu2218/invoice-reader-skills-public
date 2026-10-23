# Core changelog

Every entry is labelled **safety** (reduces silent errors or invented values: goes to every supported and frozen set, each re-evaluated) or **non-safety** (supported sets only). The first version heading is the current core version.

## 0.3.16 — PDF runtime compatibility (non-safety)

- Close PDFium documents explicitly for compatibility with 4.30 as well as 5.x; preserve page cleanup on failed render probes and support both image-bound accessor names.
- Add a single PDF runtime entry for probing, route preparation and recovery rendering under the same dependency environment. Preserve installation-free discovery and report unavailable dependencies without installing them.
- Add OCR-off discovery and align managed rendering dependency requirements. Codex uses the shared runtime prefix for every PDF action.

## 0.3.11 — Quiet wait before the policy reply; one printed Payer form (non-safety)

Until the user replies to the policy question, the agent loads only this skill's instructions. It does not list or search folders or open custom.md, the company profile or documents, because file and folder names can be confidential. When a cheque prints the drawer's name in more than one form, Payer uses the account-holder line exactly as printed (no case change) and quotes the other form in a note. Raw strings are never re-cased. The 0.3.10 PDF digit-boundary recovery paragraph is included unchanged; it had no core changelog entry of its own. Both family packages change and remain experimental; only the Anthropic package is evaluated in this change.

## 0.3.9 — Distinguish handwritten and computer-generated amount endings (safety)

Supersedes the 0.3.8 global positive default. Auto mode treats a readable terminal dash as positive only for a field identified as handwritten. Computer-generated and unknown origins preserve text pending a scoped user reply. Optional per-field amount_notation supports mixed pages, including user-confirmed positive/negative interpretations without affecting neighbouring values. Document-wide handwriting flags never establish field origin. Raw/custom strings, unclear values and quantity rules are unchanged. Both family packages remain experimental; historical 0.3.8 scores do not evaluate these bytes.

## 0.3.8 — Default terminal amount dash to positive (safety)

Owner-directed numeric-default change: a readable single terminal ASCII dash is a positive end mark by default, without a confirmation gate. User/document-specific negative interpretation and explicit unresolved-text mode remain available. Raw and custom values stay unchanged; conversion notes retain original notation, and Run info distinguishes default assumption from an explicit batch option. Malformed signs, quantities and unclear fields are not repaired. Evidence-based format exceptions take precedence over the default; no country handwriting rule is invented. Both family packages remain experimental pending evaluation of these changed bytes.

## 0.3.7 — Cheque parties and cash-sale classification (non-safety)

Read both Payee and Payer on every cheque, preserving source names and identifying missing/unclear parties without substituting the bank, profile or neighbouring invoice. The existing payment fields and workbook columns are unchanged. A Cash Memo recording a sale is classified as Invoice with its printed title retained; Billing documents remains a bucket for invoices, credit notes and debit notes. Same-page invoices remain separate records. Evaluation now supports source-order document occurrences on workbook sheets and joins them to custom/line rows by unique source/Document ID. Packages remain experimental pending live evaluation.

## 0.3.6 — Accept any policy-question reply (non-safety)

Offer the owner's "No, but I will read it before I upload any confidential data" reply alongside Yes. Any user reply completes this chat-local workflow step; no affirmative-only gate or repeated confirmation. Silence still waits. Record response received without asserting verified reading, a promise or consent. Provider/account guidance and extraction rules are unchanged. Older evaluation contracts/results remain historical; the changed packages are experimental and not yet live-evaluated.

## 0.3.5 (non-safety)

Owner decision A permits a brief skill-use announcement before the exact policy-reading question. The question and real affirmative wait still precede all document work. Both family prompts share this clarification; extraction, parsing and OCR behaviour are unchanged. The evaluator separates the historical literal-first-message diagnostic from the new announcement-tolerant opening check, conservatively referring unrecognised prose or commands for trace review. Older scores remain frozen and packages remain experimental pending evaluation.

## 0.3.4 (safety and non-safety)

Distinguish a readable terminal amount dash with ambiguous meaning from unreadable digits. Default processing preserves the printed text, flags the possible negative/end-mark meanings and excludes unresolved values from arithmetic. A user-confirmed batch option may interpret a single terminal ASCII dash as a positive end mark or negative sign. Converted amounts remain flagged with their original notation, and Run info records the option. Mixed/conflicting signs and malformed numbers remain unreadable; quantities, custom observations and fields marked unclear cannot be overridden. Raw extraction files remain unchanged.

New invented deterministic processor cases cover unknown, positive and negative conventions with fixed workbook expectations, raw-input preservation and separate result metadata. They are not model/handwriting evaluations; historical 0.3.3 references and scores remain frozen. Both rebuilt family packages remain experimental pending fresh model evaluation. The per-chat policy workflow is unchanged.

## 0.3.3 (non-safety)

Owner-requested workflow change: replace the non-blocking policy reminder with the exact per-chat README question. Wait for affirmative acknowledgement before document work; do not persist it across chats or confuse custom-field confirmation with policy acknowledgement. Both family prompts share the chat-state rules. Historical extraction evals remain unchanged; the current one-turn runner can prepare cases but cannot conduct the required question/answer exchange, so live launches are temporarily rejected rather than fabricating acknowledgement or attaching pages first.

## 0.3.2 (non-safety)

Clarify custom value/unit/context separation and the existing summary display without changing processor behaviour. New versioned scenarios explicitly score associated currency, absent units and requested context; historical references remain frozen. The optional Codex evaluation image-attachment mode records page hashes and invocation evidence independently of agent-authored reading claims. It measures supplied image inputs, not attention or autonomous visual inspection; retain experimental status.

## 0.3.1 (safety and non-safety)

Keep model transcription separate from deterministic normalisation and evaluation. Shared payment instructions preserve identifiers, source notation and bounded visual recovery. Cheque amount fields may normalise one terminal slash; other amount/quantity contexts and internal slashes remain unchanged. Space-separated numeric dates use the existing ambiguity and calendar checks. Raw extraction files remain unchanged.

Eval adds hash-checked manifest extraction capture and optional raw-text expectations alongside workbook scores. Two invented format/purpose scenarios cover the normalisation boundary and missing summary labels. Missing raw evidence remains unavailable, and multiple workbook candidates are not silently scored. These changes require fresh model evaluation; previous private scores are not carried forward.

## 0.3.0 (safety and non-safety)

Family prompts and tool adapters replace model-version prompt forks. Custom fields retain printed values, units, evidence and repeated observations. Extraction validation rejects malformed envelopes; run manifests isolate inputs. Unclear arithmetic inputs cannot silently become zero. Evals separate correct blanks and check extra documents. New packages require fresh model evaluations.

PDF routing adds execution-environment capability probes, per-page A/B/C hints, text positions, rendered images and optional local Tesseract candidates. Preparation and visual verification remain separate. Missing OCR and page/file failures retain fallback or partial status. Recovery supports rotation, cropping and selected-page OCR. Scan, incorrect-hidden-OCR and mixed-format custom scenarios extend the fixed-answer eval corpus; live model and real OCR-engine accuracy remain unmeasured.

## 0.2.0 (non-safety)

Every document is extracted and sorted onto a sheet by type: Billing documents, Reference documents, Payments, Other. The user can move types between sheets of the same shape in `custom.md`, confirmed on the first run. New fields: document title, Invoice No., balance due; statement lines; payment and other-document fields. Tax rate is the percentage only.

## 0.1.0 (non-safety)

First slice: printed English invoices. Field rules, document types, arithmetic checks, company profile, workbook writer.
