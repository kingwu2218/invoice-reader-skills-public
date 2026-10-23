"""Raw transcription evaluation: no amount/date normalisation or model grading."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'core/scripts'))
from extraction import read_manifest, validate

LINE_TABLES = {'Raw line items': 'line_items', 'Raw statement lines': 'statement_lines'}
LINE_IDENTITY = ('File', 'Pages', 'Document type', 'Document occurrence', 'Line')


def validate_line_definitions(definitions):
    """Keep new line references keyed by source order, never by the answer being graded."""
    for title in LINE_TABLES.keys() & definitions.keys():
        definition = definitions[title]
        identity = definition.get('identity', [])
        if len(identity) != len(LINE_IDENTITY) or set(identity) != set(LINE_IDENTITY):
            raise ValueError(f'{title} identity must contain exactly {list(LINE_IDENTITY)}.')
        labels = [spec['label'] for spec in definition['columns']]
        if not labels or len(set(labels)) != len(labels) or any(
                not label.startswith('item.') or not label[5:] or label in {'item.unclear', 'item.amount_notation'} for label in labels):
            raise ValueError(f'{title} columns must be unique item.FIELD strings (excluding unclear).')
        if any(spec.get('kind', 'text') != 'text' for spec in definition['columns']):
            raise ValueError('Raw references must compare text without amount/date normalisation.')
        seen = set()
        for row in definition['rows']:
            if any(not isinstance(row.get(key), str) or not row[key].strip() for key in LINE_IDENTITY):
                raise ValueError(f'{title} reference rows require every source identity as text.')
            for key in ('Document occurrence', 'Line'):
                value = row[key]
                if not value.isascii() or not value.isdecimal() or str(int(value)) != value or int(value) < 1:
                    raise ValueError(f'{title} {key} must be a canonical one-based ordinal.')
            key = tuple(' '.join(row[key].split()) for key in LINE_IDENTITY)
            if key in seen:
                raise ValueError(f'{title} contains duplicate reference identities.')
            seen.add(key)
            if any(label in row and not isinstance(row[label], str) for label in labels):
                raise ValueError(f'{title} reference values must be printed strings; omit absent values.')


def collect(work, destination):
    """Use exactly one run manifest; never guess between attempts or collect arbitrary JSON."""
    manifests = list((work/'invoice-reader-work').glob('*/manifest.json'))
    if len(manifests) != 1:
        raise ValueError('Raw evaluation requires exactly one run manifest; preserve and adjudicate multiple attempts.')
    manifest = manifests[0]
    if not manifest.resolve().is_relative_to(work.resolve()):
        raise ValueError('Manifest is outside the evaluation workspace.')
    payload, coverage = read_manifest(manifest)
    payload = {'schema_version': 1, **payload}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (destination/'raw-extraction.json').write_bytes(text.encode('utf-8'))
    return {'raw_extraction_hash': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'raw_manifest': manifest.relative_to(work).as_posix(), 'raw_coverage': coverage}


def tables(payload, field_labels=None):
    documents, observations, occurrences = [], [], Counter()
    lines = {title: [] for title in LINE_TABLES}
    for doc in validate(payload):
        identity = (doc['file'], doc.get('pages', ''), doc['document_type'])
        occurrences[identity] += 1
        base = dict(zip(('File', 'Pages', 'Document type'), identity))
        base['Document occurrence'] = str(occurrences[identity])
        # Keep supplied values even if marked unclear: invented strings must remain visible.
        documents.append({**base, **{'fields.'+key:value for key,value in doc.get('fields', {}).items()}})
        for title, collection in LINE_TABLES.items():
            for number, item in enumerate(doc.get(collection, []), 1):
                # An unclear flag must not erase a supplied guess before grading it.
                lines[title].append({**base, 'Line': str(number),
                    **{'item.'+key: value for key, value in item.items() if key not in {'unclear', 'amount_notation'}}})
        custom = doc.get('custom_fields', {})
        if not isinstance(custom, dict):
            raise ValueError('Raw custom_fields must be an object.')
        for key, items in custom.items():
            if not isinstance(items, list) or not items:
                raise ValueError('Raw observations must be non-empty arrays.')
            for number, item in enumerate(items, 1):
                if not isinstance(item, dict) or any(not isinstance(v,str) for v in item.values()):
                    raise ValueError('Raw observation values must be strings.')
                observations.append({**base, 'Field key':key, 'Occurrence':str(number),
                    **({'Field':field_labels.get(key, key)} if field_labels is not None else {}),
                    **{'observation.'+key:value for key,value in item.items()}})
    return {'Raw documents':documents, 'Raw requested values':observations, **lines}


def score(payload, definitions, score_table, field_labels=None):
    validate_line_definitions(definitions)
    result = dict(cells=Counter(), flags=Counter(), checks=Counter(), tables={}, values={}, details=[])
    actual = tables(payload, field_labels=field_labels)
    for title, definition in definitions.items():
        if title not in actual:
            raise ValueError('Unknown raw table: '+title)
        if any(spec.get('kind', 'text') != 'text' for spec in definition['columns']):
            raise ValueError('Raw references must compare text without amount/date normalisation.')
        score_table(title, definition, actual[title], result)
    return result
