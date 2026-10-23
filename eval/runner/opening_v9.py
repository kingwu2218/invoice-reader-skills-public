"""Bounded one-reply wording with preserved source and confirmation checks."""
import re

import opening_v3
import opening_v8
import workflow_audit

VERSION = 'codex-opening-v9'
host_evidence = opening_v8.host_evidence
source_target = opening_v8.source_target


def disclosure(line, work):
    accepted, reason = opening_v8.disclosure(line, work)
    if accepted or reason not in ('unsupported_explanation', 'unsupported_application_clause', 'unsupported_leading_application'):
        return accepted, reason
    # Protect source labels/targets and double-quoted rules; do not erase words
    # such as more, another, only, affirmative or any appended requirement.
    protected = r'(\[[^\]\n]+\]\([^)\n]+\)|"[^"\n]*"|“[^”\n]*”)'
    parts = re.split(protected, line)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'\bone (reply|response)\b', r'a \1', parts[i], flags=re.IGNORECASE)
    canonical = ''.join(parts)
    if canonical == line:
        return False, reason
    accepted, detail = opening_v8.disclosure(canonical, work)
    return accepted, 'recognised_one_reply' if accepted else detail


def audit(info, before, after, work, host):
    previous = opening_v8.audit(info, before, after, work, host)
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
    return {**previous, 'version': VERSION, 'v8_format_status': previous['format_status'],
            'format_status': status, 'allowed_disclosure': allowed, 'disclosure_diagnostic': reason,
            'automatic_pass': previous['observed_pause'] and status in ('host_disclosure', 'concise_opening')}
