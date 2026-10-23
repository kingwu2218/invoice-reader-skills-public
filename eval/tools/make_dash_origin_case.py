"""Printed dash clarification fixture, including a computer handwriting-style font.

All source amounts are computer generated. This is NOT human handwriting evidence.
Refuse to replace sources/answers. References are authored before model execution.
"""
import argparse
import json
from pathlib import Path
import sys

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'core/scripts'))
from buckets import default_text

NAME = 'dash-origin-printed-v1'
FILE = NAME+'.pdf'
IDENTITY = ['File', 'Pages', 'Document type', 'Document occurrence']


def table(rows, labels, identity):
    return dict(identity=identity, columns=[dict(label=k, kind=v) for k, v in labels], rows=rows)


def expected(phase):
    docs, rawdocs, lines, observations, summaries = [], [], [], [], []
    for page, number, amount in [('1', 'SYN-ORIGIN-01', '360'), ('2', 'SYN-ORIGIN-02', '720')]:
        base = dict(zip(IDENTITY, [FILE, page, 'Invoice', '1']))
        value = amount+'-'
        total = amount if page == '1' and phase != 'pending' else (
            '-720' if page == '2' and phase == 'second' else value)
        docs.append({**base, 'Document number': number, 'Total': total,
                     'Arithmetic check': 'Not checkable' if total.endswith('-') else ('Failed' if total.startswith('-') else 'Passed'),
                     'Needs review': 'Yes'})
        rawdocs.append({**base, 'fields.document_number': number, 'fields.total': value,
                        'fields.currency': 'HKD'})
        lines.append({**base, 'Line': '1', 'Quantity': '1', 'Unit price': amount,
                      'Line total': amount, 'Line check': 'Passed'})
        observations.append({**base, 'Field key': 'printed_total', 'Occurrence': '1',
                             'observation.status': 'printed', 'observation.value': value,
                             'observation.unit': 'HKD', 'observation.pages': page})
        summaries.append({**base, 'Printed total': value+' HKD'})
    return {'tables': {
        'Billing documents': table(docs, [(k, 'text') for k in ('Document number', 'Total', 'Arithmetic check')], IDENTITY),
        'Line items': table(lines, [('Quantity','number'), ('Unit price','amount'), ('Line total','amount'), ('Line check','text')], IDENTITY+['Line']),
        'Requested data': table(summaries, [('Printed total','text')], IDENTITY)},
        'raw_tables': {
            'Raw documents': table(rawdocs, [(k,'text') for k in ('fields.document_number','fields.total','fields.currency')], IDENTITY),
            'Raw requested values': table(observations, [(k,'text') for k in ('observation.status','observation.value','observation.unit','observation.pages')], IDENTITY+['Field key','Occurrence'])}}


def build(root, font):
    source = root/'eval/fixtures'/FILE
    folder = root/'eval/scenarios'/NAME
    if source.exists() or folder.exists():
        raise ValueError('Refuse to overwrite a source or frozen scenario.')
    pdfmetrics.registerFont(TTFont('FixturePrint', str(font)))
    source.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(source), pagesize=A4, invariant=1)
    for page, number, amount in [(1, 'SYN-ORIGIN-01', '360'), (2, 'SYN-ORIGIN-02', '720')]:
        pdf.setFont('Helvetica-Bold', 24); pdf.drawString(48, 775, 'INVOICE')
        pdf.setFont('Helvetica', 12)
        for y, text in [(732, 'Invoice No.: '+number), (704, 'Seller: Example Workshop Ltd'),
                        (676, 'Bill to: Tallowmere Consulting Ltd'), (648, 'Date: 9 Oct 2026'), (620, 'Currency: HKD')]:
            pdf.drawString(48, y, text)
        for x, text in [(48,'Description'), (270,'Qty'), (330,'Unit price'), (450,'Amount')]:
            pdf.drawString(x, 558, text)
        pdf.line(48, 547, 547, 547)
        for x, text in [(48,'Inspection service'), (270,'1'), (330,amount+'.00'), (450,amount+'.00')]:
            pdf.drawString(x, 522, text)
        pdf.setFont('Helvetica-Bold', 16); pdf.drawString(330, 453, 'Total (HKD)')
        pdf.setFont('Helvetica' if page == 1 else 'FixturePrint', 22)
        pdf.drawString(450, 453, amount+'-')
        pdf.setFont('Helvetica', 9)
        pdf.drawString(48, 45, f'Public synthetic invoice. Not a real transaction. Page {page} of 2.')
        pdf.showPage()
    pdf.save()
    folder.mkdir(parents=True)
    custom = default_text(confirmed=True).replace('|---|---|---|---|---|',
        '|---|---|---|---|---|\n| printed_total | Printed total | The labelled invoice total exactly as written, with its labelled currency separately | one | yes |', 1)
    (folder/'custom.md').write_text(custom, encoding='utf-8')
    (folder/'case.toml').write_text(f'source = "fixtures/{FILE}"\nmedium = "printed-and-handwriting-style-font"\ncontent_group = "{NAME}"\nexpected_routes = ["A", "A"]\n', encoding='utf-8')
    for phase in ('pending','first','second'):
        name = 'expected.json' if phase == 'pending' else f'expected-{phase}.json'
        (folder/name).write_text(json.dumps(expected(phase), indent=2)+'\n', encoding='utf-8')
    plan = {'version': 1, 'scope': 'public synthetic fixture only', 'phases': [
        {'id': 'first', 'expected': 'expected-first.json', 'output': 'output-first.xlsx',
         'reply': 'For invoice SYN-ORIGIN-01 on page 1 only, the ending dash means positive 360. I have not decided the sign for page 2 yet.'},
        {'id': 'second', 'expected': 'expected-second.json', 'output': 'output-second.xlsx',
         'reply': 'For invoice SYN-ORIGIN-02 on page 2, the ending dash means negative 720. Keep the earlier page 1 decision.'}]}
    (folder/'clarification.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8')


def expected_v2(phase):
    """Reference erratum: include the mandatory Requested values detail table."""
    result = expected(phase)
    rows = [{**{key: row[key] for key in IDENTITY}, 'Field key':'printed_total', 'Occurrence':'1',
             'Status':row['observation.status'], 'Value (as printed)':row['observation.value'],
             'Unit':row['observation.unit']}
            for row in result['raw_tables']['Raw requested values']['rows']]
    result['tables']['Requested values'] = table(rows,
        [(key,'text') for key in ('Status','Value (as printed)','Unit','Pages')], IDENTITY+['Field key','Occurrence'])
    return result


def reference_v2(root):
    import shutil
    source = root/'eval/scenarios'/NAME
    target = root/'eval/scenarios/dash-origin-printed-v2'
    target.mkdir(parents=True, exist_ok=False)
    for name in ('case.toml', 'custom.md', 'clarification.json'):
        shutil.copyfile(source/name, target/name)
    for phase in ('pending', 'first', 'second'):
        name = 'expected.json' if phase == 'pending' else f'expected-{phase}.json'
        (target/name).write_text(json.dumps(expected_v2(phase), indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path, help='Existing licensed handwriting-style font; not copied into the repo.')
    parser.add_argument('--reference-v2', action='store_true', help='Create corrected references over the unchanged v1 PDF.')
    args = parser.parse_args()
    if args.reference_v2:
        reference_v2(ROOT)
    elif args.font:
        build(ROOT, args.font)
    else:
        parser.error('Use --font or --reference-v2.')
