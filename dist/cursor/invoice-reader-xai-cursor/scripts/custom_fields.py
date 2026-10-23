"""Read the agent-maintained requested-field table; preserve all printed observations."""
import re
from pathlib import Path

from buckets import CustomError
from extraction import page_numbers, ExtractionError

HEADER = ['Key', 'Column', 'Find', 'Values', 'Required']
SECTION = '## Requested fields'
RESERVED = {'file', 'pages', 'document_id', 'document_number', 'needs_review', 'review_reasons'}


def read_fields(path):
    """Missing section means a legacy bucket-only configuration."""
    text = Path(path).read_text(encoding='utf-8')
    if SECTION not in text:
        return []
    if text.count(SECTION) != 1:
        raise CustomError('custom.md contains more than one Requested fields section.')
    section = text.split(SECTION, 1)[1].split('\n## ', 1)[0]
    fields, keys, labels, header_seen = [], set(), set(), False
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if cells == HEADER:
            header_seen = True
            continue
        if all(re.fullmatch(r':?-+:?', c) for c in cells):
            continue
        if not header_seen or len(cells) != 5:
            raise CustomError('Requested fields needs the table: Key | Column | Find | Values | Required.')
        key, label, find, values, required = cells
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', key) or key in RESERVED or key in keys:
            raise CustomError(f"Requested field key '{key}' must be unique, lowercase and not reserved.")
        if not label or label.casefold() in labels or label.casefold() in {'file', 'pages', 'document id', 'needs review', 'review reasons'}:
            raise CustomError(f"Requested column '{label}' must be unique and not a source/review column.")
        if not find or values not in ('one', 'many') or required not in ('yes', 'no'):
            raise CustomError(f"{label}: describe what to find, use one/many for Values and yes/no for Required.")
        fields.append(dict(key=key, label=label, find=find, values=values, required=required == 'yes'))
        keys.add(key)
        labels.add(label.casefold())
    if not header_seen:
        raise CustomError('Requested fields has no field table.')
    return fields


def observations(doc, fields):
    """Validate requested facts; never infer a value from another field."""
    supplied = doc.get('custom_fields', {})
    if not isinstance(supplied, dict):
        raise CustomError('custom_fields must be an object keyed by requested field key.')
    expected = {field['key'] for field in fields}
    if set(supplied) != expected:
        raise CustomError(f"custom_fields must match custom.md: missing {sorted(expected-set(supplied))}; "
                          f"unknown {sorted(set(supplied)-expected)}.")
    wide, detail, reasons = {}, [], []
    for field in fields:
        key, label = field['key'], field['label']
        values = supplied[key]
        if not isinstance(values, list) or not values or (field['values'] == 'one' and len(values) != 1):
            raise CustomError(f'{label}: provide one observation, or multiple when Values is many.')
        shown = []
        for index, item in enumerate(values, 1):
            allowed = {'status', 'value', 'unit', 'pages', 'evidence', 'context'}
            if not isinstance(item, dict) or set(item) - allowed:
                raise CustomError(f'{label}: unknown observation keys or invalid object.')
            if any(not isinstance(v, str) for v in item.values()):
                raise CustomError(f'{label}: observation values must be strings copied from the document.')
            status = item.get('status')
            if status not in ('printed', 'absent', 'unclear'):
                raise CustomError(f'{label}: status must be printed, absent or unclear.')
            value, pages, evidence = item.get('value', ''), item.get('pages', ''), item.get('evidence', '')
            if status == 'printed' and not all(s.strip() for s in (value, pages, evidence)):
                raise CustomError(f'{label}: printed values need a value, page reference and printed evidence.')
            if status != 'printed' and value:
                raise CustomError(f'{label}: absent or unclear values must stay blank.')
            if status == 'unclear' and not pages.strip():
                raise CustomError(f'{label}: unclear observations need a page reference.')
            if pages:
                try:
                    if not page_numbers(pages).issubset(page_numbers(doc.get('pages', ''))):
                        raise CustomError(f'{label}: evidence pages must belong to this document.')
                except ExtractionError as error:
                    raise CustomError(f'{label}: {error}') from error
            if status == 'absent' and len(values) != 1:
                raise CustomError(f'{label}: absent cannot be mixed with other observations.')
            reason = ''
            if status == 'unclear':
                reason = 'unclear on the page; check the original'
            elif status == 'absent' and field['required']:
                reason = 'requested information is not printed; check the original'
            if reason:
                reasons.append(f'{label}: {reason}')
            if status == 'printed':
                display = ' '.join(s for s in (value, item.get('unit', '')) if s)
                if item.get('context'):
                    display = f"{item['context']}: {display}"
                shown.append(display)
            detail.append(dict(field_key=key, field=label, occurrence=str(index), value=value,
                               unit=item.get('unit', ''), pages=pages, evidence=evidence,
                               context=item.get('context', ''), status=status, review_reasons=reason))
        wide[key] = '\n'.join(shown) or None
    return wide, detail, reasons
