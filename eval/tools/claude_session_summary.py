"""Publish a path-free summary of a scored Claude session batch (JSON + CSV).

Run eval/runner/claude_session.py report BATCH first. This reads score.json and each
run's state/meta; it never re-grades. Unrun or invalid runs stay visible with undefined
rates. Opening layout facts support manual review; they are not an automatic pass.
Usage: python eval/tools/claude_session_summary.py BATCH [BATCH ...] --out docs/evaluations/NAME
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runner'))
import claude_session

PURPOSE = {'payment': 'payment', 'energy': 'coal-energy'}
ERRORS = ('miss', 'wrong_flagged', 'silent_error', 'invented')


def purpose(case):
    for key, name in PURPOSE.items():
        if case.endswith(key):
            return name
    return case


def counts(cells):
    errors = sum(cells.get(k, 0) for k in ERRORS)
    return {'correct': cells.get('correct', 0), 'denominator': cells.get('correct', 0) + errors,
            'correct_blank': cells.get('correct_blank', 0), **{k: cells.get(k, 0) for k in ERRORS}}


def table(tables, *titles):
    total = {'expected': 0, 'actual': 0, 'matched': 0, 'missing': 0, 'extra': 0}
    for title in titles:
        for key in total:
            total[key] += tables.get(title, {}).get(key, 0)
    return total


def page_errors(details):
    return [d for d in details if d['where'].rsplit('/', 1)[-1] in ('Pages', 'observation.pages')]


SCRIPTS = re.compile(r'scripts[/\\]+([a-z_]+\.py)')


def trace(run, state):
    """Path-free digest for manual review: what was read, which scripts ran, what was denied."""
    digest = {'page_image_reads': [], 'pdf_reads': 0, 'scripts': [], 'denied': [], 'turns': []}
    for turn in state['turns']:
        info = json.loads((run/turn['folder']/'turn.json').read_text(encoding='utf-8'))
        digest['turns'].append({'kind': turn['kind'], 'result': info.get('result_subtype'),
                                'agent_turns': info.get('num_turns'), 'elapsed_seconds': info['elapsed_seconds']})
        for use in info['tool_uses']:
            target = str((use.get('input') or {}).get('file_path', ''))
            if use['name'] == 'Read' and target.lower().endswith('.png'):
                digest['page_image_reads'].append('/'.join(Path(target.replace('\\', '/')).parts[-2:]))
            elif use['name'] == 'Read' and target.lower().endswith('.pdf'):
                digest['pdf_reads'] += 1
            elif use['name'] in ('Bash', 'PowerShell'):
                digest['scripts'] += SCRIPTS.findall(str(use['input'].get('command', '')))
        for denial in info['permission_denials']:
            text = json.dumps(denial.get('tool_input'), ensure_ascii=False)
            digest['denied'].append({'tool': denial.get('tool_name'), 'scripts': SCRIPTS.findall(text),
                                     'compound': '&&' in text or ';' in text})
    return digest


def layout(run, start):
    """Literal facts about the first reply; the reviewer still reads the whole message."""
    if not start:
        return {}
    messages = json.loads((run/start['folder']/'turn.json').read_text(encoding='utf-8'))['agent_messages']
    text = '\n'.join(messages)
    question, options = claude_session.conversation.QUESTION, claude_session.conversation.REPLY_OPTIONS
    # Choice wording is compared after removing Markdown bold and an accepted lead-in only.
    plain = '\n'.join(claude_session.presentation(messages)[0])
    after = plain.split(options, 1)[1].strip() if options in plain else None
    return {'question_count': text.count(question), 'both_reply_choices_verbatim': options in plain,
            'question_in_bold': f'**{question}**' in text,
            'announcement_before_question': bool(text.split(question)[0].strip(' *\n')),
            'text_after_choices': after}


def summarise(batch):
    score = json.loads((batch/'score.json').read_text(encoding='utf-8'))
    runs = []
    for result in score['runs']:
        run = batch/result['case']/result['run']
        meta, state = result['meta'], json.loads((run/'state.json').read_text(encoding='utf-8'))
        start = next((t for t in state['turns'] if t['kind'] == 'start'), None)
        audit = {}
        if start:
            # Re-audit saved evidence with the current checker; the state keeps the original result.
            folder = run/start['folder']
            snaps = json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))
            audit = claude_session.opening_audit(json.loads((folder/'turn.json').read_text(encoding='utf-8')),
                                                 snaps['before'], snaps['after'], state['package'])
        reply = next((t for t in state['turns'] if t['kind'] == 'policy_response'), None)
        row = {'case': result['case'], 'format': meta.get('category'), 'purpose': purpose(result['case']),
               'content_group': meta.get('content_group'), 'expected_routes': meta.get('expected_routes'),
               'phase': state['phase'], 'valid': result['valid'], 'completed': meta.get('completed'),
               'timed_out': meta.get('timed_out'), 'error': result.get('error') or meta.get('raw_collection_error'),
               'model_requested': meta.get('model_requested'), 'model_reported': meta.get('model_reported'),
               'tool_version': meta.get('tool_version'), 'package_version': meta.get('set_version'),
               'artifact_hash': meta.get('artifact_hash'), 'dataset_hash': meta.get('dataset_hash'),
               'raw_extraction_hash': meta.get('raw_extraction_hash'),
               'output_sha256': hashlib.sha256((run/'output.xlsx').read_bytes()).hexdigest()
               if (run/'output.xlsx').exists() else None,
               'package_unchanged': meta.get('package_unchanged'), 'dataset_unchanged': meta.get('dataset_unchanged'),
               'elapsed_seconds': meta.get('elapsed_seconds'), 'reported_cost_usd': meta.get('total_cost_usd'),
               'permission_denials': meta.get('permission_denials'),
               'opening_status': audit.get('opening_status'), 'question_occurrences': audit.get('question_occurrences'),
               'opening_tool_uses_requiring_review': len(audit.get('tool_uses_requiring_review', [])),
               'opening_workspace_unchanged': audit.get('workspace_unchanged'),
               'policy_reply_actor': reply and reply['actor'], 'policy_reply': reply and reply['reply'],
               'question_repeated_after_reply': reply and reply['audit']['question_repeated'],
               'raw_status': result.get('raw_status', 'not_run'), 'trace': trace(run, state),
               'opening_layout': layout(run, start), 'batch': batch.name,
               'session_harness': state.get('session_harness', 'claude-session-v1')}
        if result['valid']:
            row['workbook'] = counts(result['cells'])
            row['documents'] = table(result['tables'], 'Billing documents', 'Reference documents', 'Payments', 'Other', 'Documents')
            row['requested_values'] = table(result['tables'], 'Requested values')
            row['workbook_page_errors'] = len(page_errors(result['details']))
            row['review_flags'] = result['flags']
            row['structural_checks'] = result['checks']
            row['workbook_differences'] = result['details']
        if result.get('raw_status') == 'scored':
            row['raw'] = counts(result['raw']['cells'])
            row['raw_documents'] = table(result['raw']['tables'], 'Raw documents')
            row['raw_requested_values'] = table(result['raw']['tables'], 'Raw requested values')
            row['raw_line_items'] = table(result['raw']['tables'], 'Raw line items')
            row['raw_page_errors'] = len(page_errors(result['raw']['details']))
            row['raw_differences'] = result['raw']['details']
        runs.append(row)
    return {'batch': batch.name, 'summary': score['summary'], 'runs': runs}


FLAT = ('batch', 'session_harness', 'case', 'format', 'purpose', 'phase', 'valid', 'model_requested', 'model_reported', 'opening_status',
        'question_occurrences', 'policy_reply_actor', 'raw_status')


def flatten(row):
    flat = {k: row.get(k) for k in FLAT}
    for group in ('raw', 'workbook'):
        for key, value in (row.get(group) or {}).items():
            flat[f'{group}_{key}'] = value
    for group in ('documents', 'requested_values', 'raw_documents', 'raw_requested_values', 'raw_line_items'):
        for key in ('expected', 'matched', 'missing', 'extra'):
            flat[f'{group}_{key}'] = (row.get(group) or {}).get(key)
    for key, value in (row.get('opening_layout') or {}).items():
        flat['opening_' + key] = value
    for key in ('raw_page_errors', 'workbook_page_errors', 'permission_denials', 'elapsed_seconds', 'artifact_hash',
                'dataset_hash'):
        flat[key] = row.get(key)
    return flat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', type=Path, nargs='+')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    batches = [summarise(batch) for batch in args.batch]
    report = {'batches': [{k: b[k] for k in ('batch', 'summary')} for b in batches],
              'runs': [run for b in batches for run in b['runs']]}
    text = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    if ':\\Users\\' in text or ':/Users/' in text:
        raise SystemExit('Refusing to publish a workstation path.')
    (args.out.parent/(args.out.name + '.json')).write_text(text, encoding='utf-8')
    rows = [flatten(r) for r in report['runs']]
    headers = list(dict.fromkeys(k for r in rows for k in r))
    with (args.out.parent/(args.out.name + '.csv')).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps([{k: r.get(k) for k in ('case', 'valid', 'raw_correct', 'raw_denominator', 'workbook_correct',
                                              'workbook_denominator')} for r in rows]))


if __name__ == '__main__':
    main()
