"""Bounded paraphrase recognition for one source-linked waiting explanation."""
from pathlib import Path
import re

import opening_v3
import workflow_audit

VERSION = 'codex-opening-v4'
host_evidence = opening_v3.host_evidence


def normal(text):
    return ' '.join(text.translate(str.maketrans({'’':"'",'‘':"'",'“':'"','”':'"'})).lower().split())


def disclosure(line, work):
    # Blocking words are an additional guard, never sufficient for acceptance.
    links=list(re.finditer(r'\[([^\]\n]+)\]\(([^)\n]+)\)',line))
    if len(links)!=1:return False,'expected_one_source_link'
    match=links[0];label,target=match.groups()
    visible=line[:match.start()]+label+line[match.end():]
    if re.search(r'\b(?:yes|affirmative|confirm\w*|approv\w*|consent|permission)\b|\?',normal(visible)):
        return False,'extra_confirmation_or_yes_condition'
    label=normal(label)
    label_pattern=r"(?:the )?(?:skill(?:'s)?(?: (?:first-response|first response|chat-start|chat start|chat response|policy|opening|response))?(?: (?:instructions?|rules?|requirements?))?|(?:chat response |first-response |chat-start |policy |opening )?(?:instructions?|rules?|requirements?)|invoice-reader-openai(?: skill)?|skill\.md|chat-start\.md)"
    if not re.fullmatch(label_pattern,label):return False,'unsupported_source_label'
    target=target.strip('<>').split('#',1)[0].replace('\\','/')
    if '://' in target:return False,'unrelated_source'
    path=Path(target)
    path=(path if path.is_absolute() else Path(work)/path).resolve()
    root=(Path(work)/'.agents/skills/invoice-reader-openai').resolve()
    if path not in (root/'SKILL.md',root/'references/chat-start.md'):return False,'unrelated_source'
    text=normal(line[:match.start()]+' source '+line[match.end():])
    # Remove quote/presentation punctuation. Whole-clause matching below still
    # rejects appended sentences, conditions and additional requested actions.
    text=re.sub(r'[".,:]', '', text)
    text=re.sub(r"(?<!\w)'|'(?!\w)", '', text)
    text=' '.join(text.split())
    source=r"(?:the )?(?:skill(?:'s)? )?source(?: (?:instructions?|rules?))?"
    reply=r'(?:a|your|any) (?:reply|response)'
    work_boundary=r'(?:(?:setup|set-up|document reading|document rendering|extraction)(?: or | and ))?(?:document work|document processing|processing(?: the documents)?|setup|extraction|reading (?:the )?documents|proceeding)'
    wait=r'(?:wait|pause)(?: for '+reply+r')?(?: before '+work_boundary+r')?'
    action=r'(?:end (?:the|this) response and )?'+wait
    commands=r'(?:requires?(?: me| us)? to|says? to|instructs?(?: me| us)? to|requires?|says?|states?)'
    patterns=(
        source+r' requires? '+reply+r' before '+work_boundary,
        source+r' '+commands+r' '+action,
        source+r' (?:requires?|says?|states?) (?:that )?i (?:must|should|need to) '+action,
        source+r' requires? waiting for '+reply+r'(?: before '+work_boundary+r')?',
        r'(?:under|per|according to|as required by) '+source+r' i (?:must|need to) '+action,
        r'i (?:must|need to) '+action+r' (?:as required by|under|per) '+source,
    )
    accepted=any(re.fullmatch(pattern,text) for pattern in patterns)
    return accepted,'recognised_wait_explanation' if accepted else 'unsupported_explanation'


def audit(info, before, after, work, host):
    previous=opening_v3.audit(info,before,after,work,host)
    lines=[workflow_audit.visible_line(s) for m in info.get('agent_messages',[]) for s in m.splitlines() if s.strip()]
    if lines and lines[0]==opening_v3.ANNOUNCEMENT:lines=lines[1:]
    ordered=lines[:3]==[workflow_audit.QUESTION,*workflow_audit.CHOICES]
    suffix=lines[3:] if ordered else []
    recognised,reason=(disclosure(suffix[0],work) if ordered and len(suffix)==1 else
                       (False,'no_explanation' if ordered and not suffix else 'unexpected_opening_structure'))
    allowed=recognised and host['disclosure_required']
    if recognised and not host['disclosure_required']:reason='host_evidence_unavailable'
    status=('invalid' if not previous['exact_question_once'] or not previous['both_exact_choices_once'] else
            'host_disclosure' if allowed else 'concise_opening' if ordered and not suffix else 'requires_review')
    return {**previous,'version':VERSION,'v3_format_status':previous['format_status'],
            'format_status':status,'allowed_disclosure':allowed,'disclosure_diagnostic':reason,
            'automatic_pass':previous['observed_pause'] and status in ('host_disclosure','concise_opening')}
