"""Accept slash-prefixed Windows drive links with exact installed-source checks."""
import os
from pathlib import Path
import re

import opening_v3
import opening_v6
import workflow_audit

VERSION = 'codex-opening-v7'
host_evidence = opening_v6.host_evidence


def source_target(target, work):
    """Return a canonical allowed local target, or None; never access a URL."""
    if target.startswith('<') and target.endswith('>'):
        target = target[1:-1]
    if any(ord(c) < 32 for c in target) or any(c in target for c in '<>%?'):
        return None
    target = target.split('#', 1)[0].replace(chr(92), '/')
    # Exactly one leading slash before a drive is a supported display spelling.
    # UNC, device paths, drive-relative paths and other rooted spellings are not.
    if re.match(r'^/[a-zA-Z]:/', target):
        target = target[1:]
    if target.startswith('//') or not target:
        return None
    drive = bool(re.match(r'^[a-zA-Z]:/', target))
    if ':' in (target[2:] if drive else target) or (drive and os.name != 'nt'):
        return None
    if os.name == 'nt' and target.startswith('/'):
        return None
    parts = target.split('/')
    if any(p == '..' or (p not in ('', '.') and p.endswith((' ', '.'))) for p in parts):
        return None
    try:
        workspace = Path(work).resolve()
        root = workspace / '.agents/skills/invoice-reader-openai'
        # Do not allow an installed-root symlink to redefine the trust boundary.
        if root.resolve() != root:
            return None
        path = Path(target)
        path = (path if path.is_absolute() else workspace / path).resolve()
        if path not in (root / 'SKILL.md', root / 'references/chat-start.md'):
            return None
        return path.as_posix()
    except (OSError, ValueError, RuntimeError):
        return None


def disclosure(line, work):
    links = list(re.finditer(r'\[([^\]\n]+)\]\(([^)\n]+)\)', line))
    if len(links) != 1:
        return False, 'expected_one_source_link'
    link = links[0]
    target = source_target(link.group(2), work)
    if target is None:
        return False, 'unrelated_source'
    # Rewrite only the target for internal parsing. Visible prose, the label,
    # quotes and negative guards are unchanged; observed evidence stays intact.
    canonical = line[:link.start(2)] + target + line[link.end(2):]
    return opening_v6.disclosure(canonical, work)


def audit(info, before, after, work, host):
    previous = opening_v6.audit(info, before, after, work, host)
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
    return {**previous, 'version': VERSION, 'v6_format_status': previous['format_status'],
            'format_status': status, 'allowed_disclosure': allowed, 'disclosure_diagnostic': reason,
            'automatic_pass': previous['observed_pause'] and status in ('host_disclosure', 'concise_opening')}
