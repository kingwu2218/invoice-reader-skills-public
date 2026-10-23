"""Prepare a default-positive model case without supplying a sign confirmation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    source = ROOT/'eval/scenarios/amount-dash-model-v1-end-mark'
    target = ROOT/'eval/scenarios/amount-dash-model-v2-default'
    target.mkdir(exist_ok=False)
    for name in ('case.toml', 'expected.json'):
        (target/name).write_bytes((source/name).read_bytes())
    custom = (source/'custom.md').read_text(encoding='utf-8')
    begin = custom.index('## Purpose')
    end = custom.index('## Requested fields', begin)
    custom = custom[:begin] + '## Purpose\n\nExtract the printed amounts for finance review.\n\n' + custom[end:]
    (target/'custom.md').write_text(custom, encoding='utf-8')
    print('Prepared known-source default-dash case; no sign convention supplied by custom.md.')


if __name__ == '__main__':
    main()
