"""Two bounded explanatory variants, retaining v7 source and negative guards."""
import re

import opening_v3
import opening_v7
import workflow_audit

VERSION = 'codex-opening-v8'
host_evidence = opening_v7.host_evidence
source_target = opening_v7.source_target


def disclosure(line, work):
    accepted, reason = opening_v7.disclosure(line, work)
    if accepted or reason not in ('unsupported_explanation', 'unsupported_application_clause', 'unsupported_leading_application'):
        return accepted, reason
    # Keep link labels/targets and double-quoted rules byte-identical. Expand
    # only these two prose variants, then revalidate the entire explanation.
    protected = r'(\[[^\]\n]+\]\([^)\n]+\)|"[^"\n]*"|“[^”\n]*”)'
    parts = re.split(protected, line)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'\b(requires?) this question and (?=(?:a|your|any) (?:reply|response) before\b)',
                          r'\1 ', parts[i], flags=re.IGNORECASE)
        parts[i] = re.sub(r'\bbefore I can (begin|start)\b', r'before I \1', parts[i], flags=re.IGNORECASE)
    canonical = ''.join(parts)
    if canonical == line:
        return False, reason
    accepted, detail = opening_v7.disclosure(canonical, work)
    return accepted, 'recognised_question_reply_or_can_begin' if accepted else detail


def audit(info, before, after, work, host):
    previous = opening_v7.audit(info, before, after, work, host)
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
    return {**previous, 'version': VERSION, 'v7_format_status': previous['format_status'],
            'format_status': status, 'allowed_disclosure': allowed, 'disclosure_diagnostic': reason,
            'automatic_pass': previous['observed_pause'] and status in ('host_disclosure', 'concise_opening')}
