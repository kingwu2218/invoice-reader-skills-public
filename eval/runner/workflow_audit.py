"""Versioned workflow diagnostics; old opening grades remain unchanged."""
import json
from pathlib import Path
import re

QUESTION = 'Have you read the Readme about the data policy for your model?'
CHOICES = ('Yes, I have read it.', 'No, but I will read it before I upload any confidential data')
VERSION = 'workflow-audit-v2'


def visible_line(line):
    # Presentation only: never paraphrase the question or offered answers.
    line = re.sub(r'^\s*(?:[-*+] |\d+[.)] )', '', line.strip())
    return line.replace('**', '').replace('__', '').replace('`', '').strip()


def opening(messages):
    lines = [visible_line(s) for m in messages for s in m.splitlines() if s.strip()]
    occurrences = sum(m.count(QUESTION) for m in messages)
    counts = [lines.count(c) for c in CHOICES]
    question_ok = occurrences == 1 and lines.count(QUESTION) == 1
    choices_ok = counts == [1, 1]
    residual = [s for s in lines if s not in (QUESTION, *CHOICES)]
    simple = r"I(?:'m| am|’m| will|'ll|’ll) (?:using|use) (?:the )?\$?invoice-reader-openai(?: skill)?(?: for (?:this task|this request|these documents))?[.!]?"
    if not question_ok or not choices_ok:
        status = 'invalid'
    elif not residual:
        status = 'question_only'
    elif len(residual) == 1 and re.fullmatch(simple, residual[0], re.I):
        status = 'skill_announcement'
    else:
        status = 'requires_review'
    return {'question_occurrences': occurrences, 'exact_question_once': question_ok,
            'both_exact_choices_once': choices_ok, 'format_status': status,
            'additional_text': residual}


def instruction_reads_only(command, work):
    """Accept only static PowerShell reads within the installed skill, not shell code."""
    wrapped = re.search(r'\s-(?:Command|c)\s+(.+)$', command, re.I | re.S)
    if wrapped:
        launcher = command[:wrapped.start()].strip()
        shell = r'(?:"[^"\r\n;&|`$<>]*(?:pwsh|powershell)(?:\.exe)?"|(?:pwsh|powershell)(?:\.exe)?)'
        if not re.fullmatch(shell+r'(?:\s+-(?:NoProfile|NonInteractive|NoLogo))*', launcher, re.I):
            return False
    body = wrapped.group(1).strip() if wrapped else command.strip()
    if body[:1] in ('"', "'") and body[-1:] == body[:1]:
        body = body[1:-1]
    if any(s in body for s in ('$', '`', '|', '&', '\n', '\r', '>', '<', '*', '?')):
        return False
    root = (Path(work)/'.agents/skills/invoice-reader-openai').resolve()
    pieces = body.split(';')
    for piece in pieces:
        match = re.fullmatch(r'''\s*Get-Content\s+(?:(?:-LiteralPath|-Path)\s+)?(?:'([^']+)'|"([^"]+)"|([^\s'";]+))(?:\s+-TotalCount\s+[1-9]\d*)?\s*''', piece, re.I)
        if not match:
            return False
        text = next(x for x in match.groups() if x is not None).replace('\\', '/')
        path = Path(text)
        target = (path if path.is_absolute() else Path(work)/path).resolve()
        if not target.is_relative_to(root):
            return False
        relative = target.relative_to(root)
        if relative.as_posix() != 'SKILL.md' and not (
                len(relative.parts) == 2 and relative.parts[0] == 'references' and relative.suffix == '.md'):
            return False
    return bool(pieces)


def onboarding(info, before, after, work):
    layout = opening(info.get('agent_messages', []))
    commands = info.get('commands', [])
    review = [c for c in commands if not instruction_reads_only(c, work)]
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    pause = bool(info.get('completed')) and not review and not changed
    return {'version': VERSION, **layout, 'workspace_unchanged': not changed,
            'changed_files': changed, 'commands_requiring_review': review,
            'observed_pause': pause,
            'automatic_pass': pause and layout['format_status'] in ('question_only', 'skill_announcement'),
            'scope': 'Observable messages, static instruction reads and file snapshots; extra prose requires review. Not proof of unlogged reads.'}


def image_evidence(lines):
    """Count tool-returned pixels bound to image calls, never model-written ledgers."""
    calls, returned = {}, []
    for line in lines:
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if event.get('type') != 'response_item':
            continue
        payload = event.get('payload', {})
        kind, name = payload.get('type'), payload.get('name', '')
        if kind in ('function_call', 'custom_tool_call'):
            source = str(payload.get('arguments', payload.get('input', '')))
            direct = name in ('view_image', 'functions.view_image', 'tools.view_image')
            wrapped = name in ('exec', 'functions.exec') and re.search(r'\btools\.view_image\s*\(', source)
            if direct or wrapped:
                calls[payload.get('call_id')] = {'call_id': payload.get('call_id'), 'tool': name}
        elif kind in ('function_call_output', 'custom_tool_call_output') and payload.get('call_id') in calls:
            output = payload.get('output')
            count = sum(isinstance(item, dict) and item.get('type') == 'input_image'
                        and bool(item.get('image_url')) for item in output) if isinstance(output, list) else 0
            if count:
                returned.append({**calls[payload['call_id']], 'returned_images': count})
    return {'version': VERSION, 'status': 'tool_returned_images' if returned else 'unavailable',
            'image_calls': len(calls), 'calls_with_returned_images': len(returned),
            'returned_images': sum(item['returned_images'] for item in returned), 'calls': returned,
            'scope': 'Observed image-tool output in the exact session trace; not proof of attention, page coverage or recognition accuracy.'}
