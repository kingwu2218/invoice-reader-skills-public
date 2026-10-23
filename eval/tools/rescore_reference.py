"""Rescore unchanged predictions against a later, separately frozen reference version.

The original batch is never modified. Each run's workbook, raw extraction, metadata and state
are copied unchanged (hashes checked); only expected.json is replaced for mapped cases, from a
reference folder whose lock is verified for the run's package. Unmapped cases keep their
original reference. The original scores remain the record; this is a labelled supplement.
Usage: python eval/tools/rescore_reference.py BATCH --map CASE=REFERENCE_DIR ... --out NEW_BATCH
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runner'))
import holdout
import score

COPIED = ('meta.json', 'state.json', 'output.xlsx', 'raw-extraction.json')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rescore(batch, mapping, out):
    if out.exists():
        raise ValueError('Use a new output folder; never overwrite a rescoring record.')
    record = {'source_batch': batch.name, 'runs': []}
    for run in sorted(batch.glob('*/run-*')):
        if not (run/'meta.json').exists():
            continue
        case = run.parent.name
        target = out/case/run.name
        target.mkdir(parents=True)
        files = {}
        for name in COPIED:
            if (run/name).exists():
                shutil.copyfile(run/name, target/name)
                if digest(run/name) != digest(target/name):
                    raise ValueError('Copied artifact changed.')
                files[name] = digest(run/name)
        entry = {'case': case, 'run': run.name, 'artifacts': files, 'original_reference': digest(run/'expected.json')}
        if case in mapping:
            reference = mapping[case]
            meta = json.loads((run/'meta.json').read_text(encoding='utf-8'))
            lock = holdout.verify(reference, meta['artifact_hash'])
            shutil.copyfile(reference/'expected.json', target/'expected.json')
            entry.update(reference_version=reference.name, new_reference=digest(reference/'expected.json'),
                         lock_sha256=digest(reference/'holdout-lock.json'), reference_status=lock['reference_status'])
        else:
            shutil.copyfile(run/'expected.json', target/'expected.json')
            entry['reference_version'] = 'original'
        record['runs'].append(entry)
    (out/'rescore-record.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    return score.score_batch(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', type=Path)
    parser.add_argument('--map', nargs='+', default=[], help='CASE=REFERENCE_DIR')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    mapping = {}
    for item in args.map:
        case, folder = item.split('=', 1)
        mapping[case] = Path(folder).resolve()
    report = rescore(args.batch.resolve(), mapping, args.out.resolve())
    print(json.dumps(report['summary']))


if __name__ == '__main__':
    main()
