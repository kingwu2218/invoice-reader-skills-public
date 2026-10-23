"""Owner-approved Codex opening format, separate from historical v2 scores."""
import hashlib
import json
from pathlib import Path
import re

import workflow_audit

VERSION = 'codex-opening-v3'
ANNOUNCEMENT = "I'm using the invoice-reader-openai skill."
HOST_RULE = 'If a skill causes you to ask for permission or confirmation, pause, or leave requested work unfinished, name and link to the exact SKILL.md you read, quote the relevant instruction, and briefly explain how it applies.'


def host_evidence(trace, session_id):
    """Read only the exact session's captured base instructions, never model claims."""
    try:
        with trace.open(encoding='utf-8') as stream:
            meta=json.loads(stream.readline())
        payload=meta.get('payload',{})
        base=payload.get('base_instructions',{})
        text=base if isinstance(base,str) else base.get('text','')
        found=bool(session_id) and meta.get('type')=='session_meta' and payload.get('id')==session_id and HOST_RULE in text
        return {'disclosure_required':found,'source':'session_meta.base_instructions',
                'rule_sha256':hashlib.sha256(HOST_RULE.encode()).hexdigest() if found else None}
    except (OSError,ValueError,TypeError,AttributeError):
        return {'disclosure_required':False,'source':'unavailable','rule_sha256':None}


def disclosure(line, work):
    """Conservative, anchored English forms; other wording remains reviewable."""
    match=re.fullmatch(r'The (?:skill[\u2019\x27]s )?\[([^\]\n]+)\]\(([^)\n]+)\) (.+)',line)
    if not match:return False
    label,target,reason=match.groups()
    if not re.fullmatch(r"(?:skill(?:[\u2019\x27]s)? instructions|chat response rules|invoice-reader-openai(?: skill)?)",label):
        return False
    target=target.strip('<>').split('#',1)[0].replace('\\','/')
    if '://' in target:return False
    path=Path(target)
    path=(path if path.is_absolute() else Path(work)/path).resolve()
    root=(Path(work)/'.agents/skills/invoice-reader-openai').resolve()
    if path not in (root/'SKILL.md',root/'references/chat-start.md'):return False
    prose=r'requires? (?:a|your) reply before (?:setup or )?(?:document )?processing\.'
    quote=r'requires?: [\u201c\"]End the response and wait for a reply before document work\.[\u201d\"]'
    return bool(re.fullmatch(prose,reason) or re.fullmatch(quote,reason))


def audit(info, before, after, work, host):
    strict=workflow_audit.onboarding(info,before,after,work)
    lines=[workflow_audit.visible_line(s) for m in info.get('agent_messages',[]) for s in m.splitlines() if s.strip()]
    if lines and lines[0]==ANNOUNCEMENT:lines=lines[1:]
    expected=[workflow_audit.QUESTION,*workflow_audit.CHOICES]
    ordered=lines[:3]==expected
    suffix=lines[3:] if ordered else []
    allowed=ordered and len(suffix)==1 and host['disclosure_required'] and disclosure(suffix[0],work)
    clean=ordered and not suffix
    status=('invalid' if not strict['exact_question_once'] or not strict['both_exact_choices_once'] else
            'host_disclosure' if allowed else 'concise_opening' if clean else 'requires_review')
    return {'version':VERSION,'strict_v2_format':strict['format_status'],
            'exact_question_once':strict['exact_question_once'],'both_exact_choices_once':strict['both_exact_choices_once'],
            'observed_pause':strict['observed_pause'],'ordered_question_and_choices':ordered,
            'format_status':status,'allowed_disclosure':allowed,
            'automatic_pass':strict['observed_pause'] and status in ('host_disclosure','concise_opening'),
            'host_evidence':host,
            'scope':'Opening format and observed pause only; not full host-instruction compliance, consent or extraction accuracy.'}
