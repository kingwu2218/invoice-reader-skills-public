"""Add cheque-party checks over a known public PDF; never overwrite old references."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def expected(version=1):
    if version not in (1, 2):
        raise ValueError('Supported reference versions: 1, 2')
    result = json.loads((ROOT/'eval/scenarios/format-payment/expected.json').read_text(encoding='utf-8'))
    parties = {'Payee': 'Example Workshop Ltd', 'Payer': 'Tallowmere Consulting Ltd'}
    payments = result['tables']['Payments']
    payments['columns'].extend({'label': key, 'kind': 'text'} for key in parties)
    payments['rows'][0].update(parties)
    documents = result['raw_tables']['Raw documents']
    documents['columns'].extend({'label': 'fields.'+key.lower(), 'kind': 'text'} for key in parties)
    documents['rows'][1].update({'fields.'+key.lower(): value for key, value in parties.items()})
    if version == 2:
        # Source label is Amount (HKD); current extraction rules keep that unit
        # in the long observation and compose value + unit in Requested data.
        result['tables']['Requested data']['rows'][1]['Payment amount'] = '8,750/ HKD'
        values = result['tables']['Requested values']
        values['columns'].append({'label':'Unit', 'kind':'text'})
        values['rows'][1]['Unit'] = 'HKD'
        values = result['raw_tables']['Raw requested values']
        values['columns'].append({'label':'observation.unit', 'kind':'text'})
        values['rows'][1]['observation.unit'] = 'HKD'
    return result


def main(version=1):
    reference = expected(version)
    target = ROOT/'eval/scenarios'/f'format-parties-v{version}'
    target.mkdir(exist_ok=False)
    source = ROOT/'eval/scenarios/format-payment'
    (target/'custom.md').write_bytes((source/'custom.md').read_bytes())
    (target/'case.toml').write_text(
        'source = "fixtures/format-pack.pdf"\nmedium = "printed-format-parties"\n'
        'content_group = "format-pack"\nexpected_routes = ["A", "A"]\n', encoding='utf-8')
    (target/'expected.json').write_text(json.dumps(reference, indent=2)+'\n', encoding='utf-8')
    print(f'Created format-parties-v{version}; prior references unchanged. Known public source, not a new holdout.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', type=int, choices=(1, 2), default=1)
    main(parser.parse_args().version)
