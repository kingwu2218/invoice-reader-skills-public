"""Validate the common extraction envelope and source identities before processing."""
import json
import re
from pathlib import Path
from amounts import AMOUNT_ORIGINS


class ExtractionError(ValueError):
    pass


def page_numbers(text):
    """Physical source pages, one-based; bounded to avoid expanding malformed ranges."""
    result = set()
    for part in text.split(','):
        match = re.fullmatch(r'\s*([1-9]\d*)(?:\s*-\s*([1-9]\d*))?\s*', part)
        if not match:
            raise ExtractionError('Pages must be one-based numbers or ranges, such as 1 or 2-3.')
        first, last = int(match[1]), int(match[2] or match[1])
        if last < first or last > 100000:
            raise ExtractionError('Invalid page range.')
        result.update(range(first, last + 1))
    return result


def validate(part):
    if not isinstance(part, dict) or 'documents' not in part:
        raise ExtractionError('Expected an object containing a documents array; do not save a bare document.')
    if set(part) - {'schema_version', 'documents', 'set_aside'}:
        raise ExtractionError('Unknown extraction envelope keys.')
    if part.get('schema_version', 1) != 1:
        raise ExtractionError('Unsupported extraction schema_version.')
    if part.get('set_aside'):
        raise ExtractionError('set_aside is no longer used; retain every document.')
    docs = part['documents']
    if not isinstance(docs, list) or not docs:
        raise ExtractionError('documents must be a non-empty array.')
    allowed = {'file', 'pages', 'document_id', 'document_type', 'type_evidence', 'fields', 'unclear',
               'handwritten', 'line_items', 'statement_lines', 'notes', 'description', 'custom_fields', 'amount_notation'}
    for doc in docs:
        if not isinstance(doc, dict) or set(doc) - allowed:
            raise ExtractionError('Unknown document keys or invalid document object.')
        for key in ('file', 'document_type'):
            if not isinstance(doc.get(key), str) or not doc[key].strip():
                raise ExtractionError(f'Document {key} must be a non-empty string.')
        for key in ('pages', 'document_id', 'type_evidence', 'description'):
            if key in doc and not isinstance(doc[key], str):
                raise ExtractionError(f'{key} must be a string.')
        if doc.get('pages'):
            page_numbers(doc['pages'])
        if 'handwritten' in doc and not isinstance(doc['handwritten'], bool):
            raise ExtractionError('handwritten must be a boolean.')
        fields = doc.get('fields', {})
        if not isinstance(fields, dict) or any(not isinstance(v, str) for v in fields.values()):
            raise ExtractionError('fields must contain printed strings only.')
        _unclear(doc.get('unclear', []))
        validate_amount_notation(doc.get('amount_notation', {}), fields)
        for key in ('line_items', 'statement_lines'):
            items = doc.get(key, [])
            if not isinstance(items, list):
                raise ExtractionError(f'{key} must be an array.')
            for item in items:
                if not isinstance(item, dict) or any(not isinstance(v, str) for k, v in item.items() if k not in {'unclear', 'amount_notation'}):
                    raise ExtractionError(f'{key} values must be printed strings.')
                _unclear(item.get('unclear', []))
                validate_amount_notation(item.get('amount_notation', {}), item)
        notes = doc.get('notes', [])
        if not isinstance(notes, list):
            raise ExtractionError('notes must be an array.')
        for note in notes:
            if not isinstance(note, dict) or set(note) - {'text', 'columns'} or not isinstance(note.get('text'), str):
                raise ExtractionError('Each note needs text and optional columns.')
            _unclear(note.get('columns', []))
    return docs


def validate_amount_notation(notation, fields, specs=None):
    """Optional field-level provenance and a recorded, scoped user interpretation."""
    if not isinstance(notation, dict):
        raise ExtractionError('amount_notation must be a field-keyed object.')
    for key, entry in notation.items():
        if key not in fields or not isinstance(fields[key], str) or not fields[key].strip():
            raise ExtractionError('amount_notation must refer to a captured field.')
        if specs is not None and (key not in specs or specs[key]['kind'] != 'amount'):
            raise ExtractionError('amount_notation is only allowed on amount fields.')
        if not isinstance(entry, dict) or set(entry) - {'origin', 'confirmed_as', 'confirmation'}:
            raise ExtractionError('Invalid amount_notation entry.')
        if entry.get('origin') not in AMOUNT_ORIGINS:
            raise ExtractionError('amount_notation requires handwritten, computer-generated or unknown origin.')
        if 'confirmed_as' in entry or 'confirmation' in entry:
            if (entry.get('confirmed_as') not in ('end-mark', 'negative') or
                    not isinstance(entry.get('confirmation'), str) or not entry['confirmation'].strip()):
                raise ExtractionError('A confirmed amount notation needs end-mark/negative and the scoped user reply.')


def _unclear(value):
    if not isinstance(value, list) or any(not isinstance(key, str) for key in value):
        raise ExtractionError('unclear/columns must be arrays of field names.')


def read(path):
    files = sorted(path.glob('*.json')) if path.is_dir() else [path]
    if not files:
        raise ExtractionError(f'No JSON extraction files in {path}.')
    docs, identities = [], set()
    for file in files:
        for original in validate(json.loads(file.read_text(encoding='utf-8'))):
            doc = dict(original)
            identity = doc.get('document_id') or f"{doc['file']}#pages={doc.get('pages', '')}"
            if identity in identities:
                raise ExtractionError(f'Duplicate document identity: {identity}. Use distinct page ranges or document_id values.')
            identities.add(identity)
            doc['document_id'] = identity
            docs.append(doc)
    return {'documents': docs}


def read_manifest(path):
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict) or set(manifest) != {'version', 'inputs'} or manifest['version'] != 1:
        raise ExtractionError('Manifest requires version 1 and inputs.')
    if not isinstance(manifest['inputs'], list) or not manifest['inputs']:
        raise ExtractionError('Manifest inputs must be a non-empty array.')
    docs, coverage, sources, outputs = [], [], set(), set()
    for item in manifest['inputs']:
        if not isinstance(item, dict) or set(item) - {'file', 'extraction', 'reason'}:
            raise ExtractionError('Invalid manifest input.')
        source = item.get('file')
        if not isinstance(source, str) or not source.strip() or source in sources:
            raise ExtractionError('Manifest source names must be unique non-empty strings.')
        sources.add(source)
        output = item.get('extraction')
        if output is None:
            reason = item.get('reason')
            if not isinstance(reason, str) or not reason.strip():
                raise ExtractionError('An unprocessed input needs a reason.')
            coverage.append(dict(file=source, status='Unprocessed', reason=reason))
            continue
        if not isinstance(output, str) or item.get('reason'):
            raise ExtractionError('Processed inputs need an extraction path, not a failure reason.')
        candidate = (path.parent / output).resolve()
        if not candidate.is_relative_to(path.parent.resolve()) or candidate in outputs or candidate == path.resolve() or not candidate.is_file():
            raise ExtractionError('Extraction paths must be unique files inside this run directory.')
        outputs.add(candidate)
        part = read(candidate)
        if any(doc['file'] != source for doc in part['documents']):
            raise ExtractionError('Extraction source does not match its manifest input.')
        if any(not doc.get('pages') for doc in part['documents']):
            raise ExtractionError('Manifest extractions require a page range for every document.')
        docs.extend(part['documents'])
        coverage.append(dict(file=source, status='Processed', reason=''))
    ids = [doc['document_id'] for doc in docs]
    if len(set(ids)) != len(ids):
        raise ExtractionError('Duplicate document identities across manifest inputs.')
    return {'documents': docs}, coverage
