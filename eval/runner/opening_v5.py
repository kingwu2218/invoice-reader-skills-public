"""One linked waiting explanation, optionally quoting a rule then applying it.

Whole-clause parsing is intentional: unknown additions are referred, never
accepted just because the paragraph includes a recognised waiting phrase.
"""
import re

import opening_v3
import opening_v4
import workflow_audit

VERSION = 'codex-opening-v5'
host_evidence = opening_v4.host_evidence


def disclosure(line, work):
    accepted, reason = opening_v4.disclosure(line, work)
    if accepted or reason != 'unsupported_explanation':
        return accepted, reason
    # V4 has already validated visible blocking words, source label and target.
    text = opening_v4.normal(re.sub(r'\[[^\]\n]+\]\([^)\n]+\)', 'source', line))
    source = r"(?:the )?(?:skill(?:'s)? )?source(?: (?:instructions?|rules?))?"
    commands = r'(?:requires?(?:(?: me| us)? to)?|says?(?: to)?|states?|instructs?(?: me| us)? to|requires? this pause)'
    # Preserve sentence/quote boundaries; accept exactly one quoted rule.
    match = re.fullmatch(source + r' ' + commands + r':? "([^"]+)"[.,;:]?(?: (.+))?', text)
    if not match:
        return False, 'unsupported_explanation'
    rule, application = match.groups()
    rule = re.sub(r'^after asking,? ', '', rule).rstrip('.')
    reply = r'(?:a|your|any) (?:reply|response)'
    work_boundary = r'(?:setup(?: and (?:document )?processing)?|document work|document processing|processing(?: the documents)?|extraction|reading (?:the )?documents|proceeding)'
    wait = r'(?:wait|pause)(?: for ' + reply + r')?(?: before ' + work_boundary + r')?'
    if not re.fullmatch(r'(?:end (?:the|this) response and )?' + wait, rule):
        return False, 'unsupported_quoted_rule'
    if application is not None:
        application = application.rstrip('.')
        forms = (
            r'(?:this|that|the rule|this rule) requires? ' + reply + r' before i (?:begin|start) ' + work_boundary,
            r'(?:this|that|the rule|this rule) requires? ' + reply + r' before ' + work_boundary,
            r'(?:so |therefore |this means )?i (?:must|need to|will|have to) ' + wait,
            r'(?:this|that|the rule|this rule) means i (?:must|need to) ' + wait,
            r'(?:so |therefore )?i (?:cannot|can\'t) (?:begin|start) ' + work_boundary + r' until (?:you (?:reply|respond)|i receive ' + reply + r')',
        )
        if not any(re.fullmatch(form, application) for form in forms):
            return False, 'unsupported_application_clause'
    return True, 'recognised_quoted_wait_explanation'


def audit(info, before, after, work, host):
    previous = opening_v4.audit(info, before, after, work, host)
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
    return {**previous, 'version': VERSION, 'v4_format_status': previous['format_status'],
            'format_status': status, 'allowed_disclosure': allowed, 'disclosure_diagnostic': reason,
            'automatic_pass': previous['observed_pause'] and status in ('host_disclosure', 'concise_opening')}
