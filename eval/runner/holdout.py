"""Freeze independently reviewed private holdouts before tested-model execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tomllib


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_expectations(expected):
    """Reject impossible fixed-sheet keys before exposing a holdout to the model."""
    import raw
    raw.validate_line_definitions(expected.get('raw_tables', {}))
    schema = Path(__file__).resolve().parents[2]/'core/scripts/data/columns.toml'
    with schema.open('rb') as stream:
        columns = tomllib.load(stream)
    for title, section in (('Line items', 'line_items'), ('Statement lines', 'statement_lines')):
        definition = expected.get('tables', {}).get(title)
        if definition is None:
            continue
        supported = {column['label'] for column in columns[section]} | {'Document ID', 'Document type', 'Document occurrence'}
        if title in ('Line items', 'Statement lines'):
            supported.add('Pages')
        requested = set(definition.get('identity', [])) | {c['label'] for c in definition.get('columns', [])}
        if requested - supported:
            raise ValueError(f'Unsupported {title} reference columns: {sorted(requested - supported)}')


def freeze(folder, *, source_id, original_source_hash, excluded_source_ids, excluded_source_hashes,
           artifact_hash, reference_status='agent-reviewed-provisional'):
    folder = Path(folder)
    target = folder/'holdout-lock.json'
    if target.exists():
        raise ValueError('Holdout already frozen; preserve the original lock and answers.')
    if source_id in excluded_source_ids or original_source_hash in excluded_source_hashes:
        raise ValueError('This source already participated in prompt development or evaluation.')
    if reference_status not in ('agent-reviewed-provisional','owner-verified'):
        raise ValueError('Record the actual reference review status.')
    with (folder/'case.toml').open('rb') as stream:
        config = tomllib.load(stream)
    source = Path(config['source'])
    if not source.is_absolute():
        raise ValueError('Private holdout source must have an explicit absolute path in its ignored config.')
    paths = [source, folder/'case.toml', folder/'custom.md', folder/'expected.json']
    expected = json.loads((folder/'expected.json').read_text(encoding='utf-8'))
    if not expected.get('tables') or not expected.get('raw_tables'):
        raise ValueError('Freeze both workbook and raw expectations before running.')
    validate_expectations(expected)
    lock = {'schema_version':1,'frozen_at':datetime.now(timezone.utc).isoformat(),
            'source_id':source_id,'original_source_hash':original_source_hash,
            'excluded_source_ids':sorted(excluded_source_ids),'excluded_source_hashes':sorted(excluded_source_hashes),
            'artifact_hash':artifact_hash,'reference_status':reference_status,
            'files':{str(p.resolve()):fingerprint(p) for p in paths},
            'use':'First-use holdout relative to the frozen package; do not tune prompts on its answers before scoring.'}
    target.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
    return lock


def verify(folder, artifact_hash):
    lock = json.loads((Path(folder)/'holdout-lock.json').read_text(encoding='utf-8'))
    if lock['artifact_hash'] != artifact_hash:
        raise ValueError('Package differs from the one the holdout was frozen for.')
    if any(fingerprint(p) != expected for p,expected in lock['files'].items()):
        raise ValueError('Holdout source, configuration or reference changed after freeze.')
    validate_expectations(json.loads((Path(folder)/'expected.json').read_text(encoding='utf-8')))
    return lock


def freeze_regression(folder, *, previous_case, artifact_hash, reference_status, review_files=()):
    """Lock reused private sources honestly; never relabel them as fresh holdouts."""
    folder, previous_case = Path(folder), Path(previous_case)
    target = folder/'holdout-lock.json'
    if target.exists():
        raise ValueError('Regression already frozen; preserve its answers and lock.')
    previous_path = previous_case/'holdout-lock.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8'))
    verify(previous_case, previous['artifact_hash'])
    if reference_status not in ('owner-verified', 'mixed-owner-and-provisional'):
        raise ValueError('Record the regression reference scope.')
    with (folder/'case.toml').open('rb') as stream:
        source = Path(tomllib.load(stream)['source'])
    with (previous_case/'case.toml').open('rb') as stream:
        prior_source = Path(tomllib.load(stream)['source'])
    if not source.is_absolute() or fingerprint(source) != fingerprint(prior_source):
        raise ValueError('Regression must reuse the exact previously frozen source bytes.')
    expected = json.loads((folder/'expected.json').read_text(encoding='utf-8'))
    if not expected.get('tables') or not expected.get('raw_tables'):
        raise ValueError('Regression requires raw and workbook expectations.')
    validate_expectations(expected)
    paths = [source, folder/'case.toml', folder/'custom.md', folder/'expected.json', previous_path,
             *map(Path, review_files)]
    lock = {'schema_version':1, 'evaluation_kind':'known-source-regression',
            'frozen_at':datetime.now(timezone.utc).isoformat(),
            'source_id':previous['source_id'], 'original_source_hash':previous['original_source_hash'],
            'artifact_hash':artifact_hash, 'reference_status':reference_status,
            'files':{**previous['files'], **{str(p.resolve()):fingerprint(p) for p in paths}},
            'use':'Reused source with versioned references; not a fresh holdout or independent document.'}
    target.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
    return lock


def abstention(payload, expected):
    """Report guessing on predeclared unclear custom observations, outside field accuracy."""
    import raw
    actual = raw.tables(payload)['Raw requested values']
    spec = expected.get('raw_tables',{}).get('Raw requested values',{})
    keys = spec.get('identity',[])
    total = kept_unclear = filled = missing = 0
    for wanted in spec.get('rows',[]):
        if wanted.get('observation.status') != 'unclear':
            continue
        total += 1
        matches = [r for r in actual if all(str(r.get(k,'')) == str(wanted.get(k,'')) for k in keys)]
        if len(matches) != 1:
            missing += 1
            continue
        got = matches[0]
        supplied = bool(str(got.get('observation.value','')).strip())
        filled += supplied
        kept_unclear += not supplied and got.get('observation.status') == 'unclear'
    return {'unclear_fields':total,'kept_unclear_and_blank':kept_unclear,'unsupported_filled':filled,
            'missing_or_ambiguous_observation':missing,'abstention_rate':kept_unclear/total if total else None}
