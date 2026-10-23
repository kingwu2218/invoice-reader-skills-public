"""Explicit retrospective reference review; never changes the original batch.

The varied-use-v1 reference confused an Other worksheet with document_type.
v2 corrects that authoring error to the existing contract's Lab certificate.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'eval/runner'))
import varied_use
import first_use
import raw
import score
from custom_fields import read_fields


def corrected(reference):
    result = json.loads(json.dumps(reference))
    for section in ('tables', 'raw_tables'):
        for table in result[section].values():
            for row in table['rows']:
                if row.get('File') == 'batch-support.pdf' and row.get('Document pages', row.get('Pages')) == '2':
                    if row.get('Document type') != 'Other': raise ValueError('Unexpected v1 certificate identity.')
                    row['Document type'] = 'Lab certificate'
    return result


def make_references():
    destination = ROOT/'eval/workflows/varied-use-v2'
    destination.mkdir(exist_ok=False)
    for purpose in varied_use.PURPOSES:
        first_use.save_new(destination/(purpose+'.json'), corrected(varied_use.read(ROOT/'eval/workflows/varied-use-v1'/(purpose+'.json'))))


def review(batch, destination):
    if destination.suffix != '.json' or destination.exists() or destination.with_suffix('.csv').exists():
        raise ValueError('Use new JSON and CSV destinations.')
    plan = varied_use.read(batch/'plan.json'); rows = []; reference_hashes = {}
    for trial in plan['trials']:
        _, _, folder = varied_use.load(batch, trial['id'])
        result = varied_use.read(folder/'reply-result.json'); extraction = result['extraction']
        artifacts = folder/'reply-artifacts'
        reference = ROOT/'eval/workflows/varied-use-v2'/(trial['purpose']+'.json')
        expected = varied_use.read(reference)
        if expected != corrected(varied_use.read(folder/'expected.json')): raise ValueError('v2 contains changes beyond the declared erratum.')
        reference_hashes[reference.relative_to(ROOT).as_posix()] = first_use.digest(reference)
        if first_use.digest(artifacts/'output.xlsx') != extraction['workbook_sha256']: raise ValueError('Archived workbook changed.')
        original, coverage = raw.read_manifest(Path(trial['workspace'])/extraction['raw_manifest'])
        payload = varied_use.read(artifacts/'raw-extraction.json')
        if payload != dict(schema_version=1, **original) or coverage != extraction['raw_coverage']:
            raise ValueError('Archived raw extraction/coverage differs from original manifest.')
        fields = read_fields(artifacts/'custom.md'); labels = {f['key']: f['label'] for f in fields}
        for layer, scored in [('raw', raw.score(payload, expected['raw_tables'], score.score_table, labels)),
                              ('workbook', score.score_workbook(artifacts/'output.xlsx', expected))]:
            old = varied_use.read(artifacts/(layer+'-score.json'))
            # Verify saved old scoring before issuing a supplementary score.
            old_reference = varied_use.read(folder/'expected.json')
            recomputed = raw.score(payload, old_reference['raw_tables'], score.score_table, labels) if layer == 'raw' else score.score_workbook(artifacts/'output.xlsx', old_reference)
            if old != recomputed: raise ValueError('Original score no longer reproducible.')
            counts = first_use.counts(scored); old_counts = first_use.counts(recomputed)
            rows.append(dict(trial=trial['id'], purpose=trial['purpose'], layer=layer,
                original_correct=old_counts['correct'], original_denominator=old_counts['denominator'],
                **counts, details=scored['details'], metrics=score.metrics(scored),
                raw_sha256=first_use.digest(artifacts/'raw-extraction.json'), workbook_sha256=extraction['workbook_sha256'],
                original_score_sha256=first_use.digest(artifacts/(layer+'-score.json'))))
    totals = {}
    for layer in ('raw', 'workbook'):
        selected = [r for r in rows if r['layer'] == layer]; cells = Counter()
        for r in selected: cells.update(r['cells'])
        totals[layer] = dict(cells=dict(cells), **{key: sum(r[key] for r in selected) for key in ('correct', 'denominator', 'correct_blank')})
    report = dict(reference_version='varied-use-v2', timing='Retrospective reference erratum after observing both model outputs; not a prospectively frozen pass or a new model execution.',
        change='Only certificate Document type changes from Other (worksheet bucket) to Lab certificate (existing extraction contract). Printed answers, identity columns and scorer are unchanged.',
        package_version=plan['package_version'], package_sha256=plan['artifact_hash'],
        requested_model=plan['model_requested'], provider=plan['provider'], model_reported='Unknown',
        plan_sha256=first_use.digest(batch/'plan.json'), reference_hashes=reference_hashes,
        reviewer_sha256=first_use.digest(Path(__file__)), rows=rows, totals=totals)
    first_use.save_new(destination, report)
    columns = ['trial', 'purpose', 'layer', 'original_correct', 'original_denominator', 'correct', 'denominator', 'correct_blank']
    with destination.with_suffix('.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
    return totals


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('references')
    s = sub.add_parser('review'); s.add_argument('batch', type=Path); s.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.action == 'references': make_references()
    else: print(json.dumps(review(a.batch, a.out), indent=2))
