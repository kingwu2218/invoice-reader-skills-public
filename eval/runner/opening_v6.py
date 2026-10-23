"""Versioned recognition of a waiting explanation preceding its quoted rule."""
import re

import opening_v3
import opening_v4
import opening_v5
import workflow_audit

VERSION = 'codex-opening-v6'
host_evidence = opening_v5.host_evidence


def disclosure(line, work):
    accepted, reason = opening_v5.disclosure(line, work)
    if accepted or reason != 'unsupported_explanation':
        return accepted, reason
    # V5/V4 have already validated one source link, its target, and visible
    # negative guards. Keep punctuation boundaries instead of substring search.
    text = opening_v4.normal(line)
    match = re.fullmatch(r'([^\"]+?)[.:;] \"([^\"]+)\"[.]?', text)
    if not match:
        return False, 'unsupported_explanation'
    application, rule = match.groups()
    # Independently validate the complete source-linked application. Preserve
    # the original target's case for case-sensitive filesystem platforms.
    original_link = re.search(r'\[([^\]\n]+)\]\(([^)\n]+)\)', line)
    application = re.sub(r'\[[^\]\n]+\]\([^)\n]+\)', lambda _: original_link.group(0), application)
    allowed, _ = opening_v4.disclosure(application, work)
    if not allowed:
        return False, 'unsupported_leading_application'
    target = original_link.group(2)
    # Reuse the frozen quoted-rule grammar; the synthetic connector is local
    # parsing only, never passed to the model or saved as its observed prose.
    allowed, _ = opening_v5.disclosure(f'The [skill instructions]({target}) require: "{rule}"', work)
    return allowed, 'recognised_application_then_quote' if allowed else 'unsupported_quoted_rule'


def audit(info, before, after, work, host):
    previous = opening_v5.audit(info, before, after, work, host)
    lines = [workflow_audit.visible_line(s) for m in info.get('agent_messages', []) for s in m.splitlines() if s.strip()]
    if lines and lines[0] == opening_v3.ANNOUNCEMENT:
        lines = lines[1:]
    ordered = lines[:3] == [workflow_audit.QUESTION, *workflow_audit.CHOICES]
    suffix = lines[3:] if ordered else []
    recognised, reason = (disclosure(suffix[0], work) if ordered and len(suffix) == 1 else
                          (False, 'no_explanation' if ordered and not suffix else 'unexpected_opening_structure'))
    allowed = recognised and host['disclosure_required']
    if recognised and not host['disclosure_required']:
        reason = 'host_evidence_unavailable'
    status = ('invalid' if not previous['exact_question_once'] or not previous['both_exact_choices_once'] else
              'host_disclosure' if allowed else 'concise_opening' if ordered and not suffix else 'requires_review')
    return {**previous, 'version': VERSION, 'v5_format_status': previous['format_status'],
            'format_status': status, 'allowed_disclosure': allowed, 'disclosure_diagnostic': reason,
            'automatic_pass': previous['observed_pause'] and status in ('host_disclosure', 'concise_opening')}
