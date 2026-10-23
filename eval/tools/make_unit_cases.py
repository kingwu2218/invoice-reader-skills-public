"""Author new unit/context references; never rewrite historical format answers or PDFs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'core/scripts'))
from buckets import default_text
from make_format_cases import expected


def specification(purpose):
    result = expected(purpose)
    payment = purpose == 'payment'
    label = 'Payment amount' if payment else 'Project reference'
    for row in result['tables']['Requested values']['rows']:
        present = row['Status'] == 'printed'
        row['Unit'] = 'HKD' if present and payment else None
        row['Context'] = 'Lobby hinge inspection' if present and payment else None
    result['tables']['Requested values']['columns'] += [
        {'label': k, 'kind': 'text'} for k in ('Unit', 'Context')]
    for row in result['raw_tables']['Raw requested values']['rows']:
        present = row['observation.status'] == 'printed'
        row['observation.unit'] = 'HKD' if present and payment else None
        row['observation.context'] = 'Lobby hinge inspection' if present and payment else None
    result['raw_tables']['Raw requested values']['columns'] += [
        {'label': k, 'kind': 'text'} for k in ('observation.unit', 'observation.context')]
    if payment:
        result['tables']['Requested data']['rows'][1][label] = 'Lobby hinge inspection: 8,750/ HKD'
    return result


def main():
    folders = [ROOT/'eval/scenarios'/f'format-{p}-units-v1' for p in ('payment', 'project')]
    if any(p.exists() for p in folders):
        raise ValueError('Do not overwrite frozen unit/context references')
    for purpose, folder in zip(('payment', 'project'), folders):
        folder.mkdir(parents=True)
        row = ('payment_amount | Payment amount | The amount in figures on a cheque, retaining its printed notation and associated currency; include the description labelled Re: as context; absent on other documents'
               if purpose == 'payment' else
               'project_ref | Project reference | Only the description explicitly labelled Re: on each document; this text reference has no unit or additional context')
        custom = default_text(confirmed=True).replace('|---|---|---|---|---|', f'|---|---|---|---|---|\n| {row} | one | no |', 1)
        (folder/'custom.md').write_text(custom, encoding='utf-8')
        (folder/'expected.json').write_text(json.dumps(specification(purpose), indent=2)+'\n', encoding='utf-8')
        (folder/'case.toml').write_text('source = "fixtures/format-pack.pdf"\nmedium = "printed-format"\ncontent_group = "format-pack"\nexpected_routes = ["A"]\n', encoding='utf-8')


if __name__ == '__main__':
    main()
