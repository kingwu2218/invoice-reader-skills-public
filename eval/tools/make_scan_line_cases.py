"""Versioned image-only cases with raw line and custom-field references; no overwrites."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IDENTITY = ['File', 'Pages', 'Document type', 'Document occurrence']


def definition(rows, labels, identity):
    return {'identity': list(identity), 'columns': [{'label': k, 'kind': 'text'} for k in labels], 'rows': rows}


def build(purpose, version=2):
    previous = ROOT/'eval/scenarios'/('coal-scan-'+purpose)
    expected = json.loads((previous/'expected.json').read_text(encoding='utf-8'))
    invoice = {'File': 'coal-scan.pdf', 'Pages': '1', 'Document type': 'Invoice', 'Document occurrence': '1'}
    certificate = {**invoice, 'Pages': '2', 'Document type': 'Other'}
    # Explicit reference literals, specified from reviewed source pages before execution.
    expected['raw_tables'] = {
        'Raw documents': definition([
            {**invoice, 'fields.document_number': 'COAL-001', 'fields.total': '105.00',
             'fields.subtotal': '100.00', 'fields.tax_amount': '0.00'},
            {**certificate, 'fields.document_title': 'LAB CERTIFICATE'}],
            ['fields.document_number', 'fields.total', 'fields.subtotal', 'fields.tax_amount', 'fields.document_title'], IDENTITY),
        'Raw line items': definition([{**invoice, 'Line': '1', 'item.quantity': '1',
            'item.unit_price': '100.00', 'item.line_total': '100.00'}],
            ['item.quantity', 'item.unit_price', 'item.line_total'], IDENTITY+['Line'])}
    expected['raw_tables']['Raw documents']['rows'][0]['fields.document_title'] = 'INVOICE'
    values = []
    mapping = {'Status': 'status', 'Value (as printed)': 'value', 'Unit': 'unit', 'Context': 'context', 'Pages': 'pages'}
    for original in expected['tables']['Requested values']['rows']:
        base = invoice if original['Document pages'] == '1' else certificate
        row = {**base, 'Field key': original['Field key'], 'Occurrence': original['Occurrence']}
        row.update({'observation.'+key: original[label] for label, key in mapping.items() if label in original})
        values.append(row)
    expected['raw_tables']['Raw requested values'] = definition(values,
        ['observation.'+key for key in mapping.values()], IDENTITY+['Field key', 'Occurrence'])
    if version == 2:
        # This fixture has exactly one document per page. Non-standard type names
        # are open vocabulary, not the destination sheet label "Other".
        for title in ('Raw documents', 'Raw requested values'):
            table = expected['raw_tables'][title]
            table['identity'].remove('Document type')
            for row in table['rows']:
                row.pop('Document type')
    return expected, (previous/'custom.md').read_text(encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', type=int, choices=(1, 2), default=2)
    version = parser.parse_args().version
    folders = [ROOT/'eval/scenarios'/f'coal-scan-{p}-lines-v{version}' for p in ('payment', 'energy')]
    if any(p.exists() for p in folders):
        raise ValueError('Do not overwrite frozen scenarios.')
    for purpose, folder in zip(('payment', 'energy'), folders):
        expected, custom = build(purpose, version)
        folder.mkdir()
        (folder/'expected.json').write_text(json.dumps(expected, indent=2)+'\n', encoding='utf-8')
        (folder/'custom.md').write_text(custom, encoding='utf-8')
        (folder/'case.toml').write_text('source = "fixtures/coal-scan.pdf"\nmedium = "image-only-lines"\n'
            'content_group = "coal-pack"\nexpected_routes = ["B", "B"]\n', encoding='utf-8')


if __name__ == '__main__':
    main()
