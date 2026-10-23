"""Aggregate-only summary of scored private Claude session batches; never values or paths.

Each difference is labelled by kind without revealing it: casing-only (same text, different
case), spacing/punctuation-only, blank (left empty) or different. Strict scores are unchanged;
the kinds only help a reviewer see whether a difference could be a source-supported variant.
Usage: python eval/tools/claude_private_summary.py LABEL=BATCH [LABEL=BATCH ...] --out FILE.json
"""
import argparse
from collections import Counter
import json
from pathlib import Path

ERRORS = ('miss', 'wrong_flagged', 'silent_error', 'invented')
DOCUMENT_SHEETS = ('Billing documents', 'Reference documents', 'Payments', 'Other')


def kind(expected, got):
    if got in (None, 'None', ''):
        return 'blank'
    if expected in (None, 'None', ''):
        return 'filled_where_blank_expected'
    if expected.casefold() == got.casefold():
        return 'casing_only'
    squash = lambda text: ''.join(ch for ch in text if ch.isalnum()).casefold()
    return 'spacing_or_punctuation_only' if squash(expected) == squash(got) else 'different'


def layer(cells):
    return {'correct': cells.get('correct', 0), 'correct_blank': cells.get('correct_blank', 0),
            'denominator': cells.get('correct', 0) + sum(cells.get(k, 0) for k in ERRORS),
            **{k: cells.get(k, 0) for k in ERRORS}}


def summarise(label, batch):
    score = json.loads((batch/'score.json').read_text(encoding='utf-8'))
    runs = []
    for result in score['runs']:
        meta = result['meta']
        state = json.loads((batch/result['case']/result['run']/'state.json').read_text(encoding='utf-8'))
        row = {'model_family_run': label, 'case': result['case'], 'run': result['run'], 'valid': result['valid'],
               'phase': state['phase'], 'model_requested': meta.get('model_requested'),
               'model_reported': meta.get('model_reported'), 'session_harness': state.get('session_harness'),
               'evaluation_kind': meta.get('evaluation_kind'), 'reference_status': meta.get('reference_status'),
               'policy_reply_actor': next((t.get('actor') for t in state['turns'] if t['kind'] == 'policy_response'), None),
               'permission_denials': meta.get('permission_denials'), 'elapsed_seconds': meta.get('elapsed_seconds')}
        if result['valid']:
            row['workbook'] = layer(result['cells'])
            row['raw'] = layer(result.get('raw', {}).get('cells', {}))
            docs = Counter()
            for title in DOCUMENT_SHEETS:
                docs.update(result['tables'].get(title, {}))
            row['documents'] = {k: docs.get(k, 0) for k in ('expected', 'matched', 'missing', 'extra')}
            row['abstention'] = {k: v for k, v in (meta.get('abstention') or {}).items() if k != 'abstention_rate'}
            row['difference_kinds'] = [{'layer': layer_name, 'field': d['where'].rsplit('/', 1)[-1],
                                        'outcome': d['outcome'], 'kind': kind(d.get('expected'), d.get('got'))}
                                       for layer_name, details in (('workbook', result['details']),
                                                                   ('raw', result.get('raw', {}).get('details', [])))
                                       for d in details if d['outcome'] != 'extra_row']
        runs.append(row)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batches', nargs='+')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    runs = []
    for item in args.batches:
        label, path = item.split('=', 1)
        runs += summarise(label, Path(path))
    text = json.dumps({'runs': runs}, indent=2, ensure_ascii=False)
    if ':\\' in text or ':/' in text:
        raise SystemExit('Refusing to publish a path.')
    args.out.write_text(text, encoding='utf-8')
    print(f'{len(runs)} runs summarised')


if __name__ == '__main__':
    main()
