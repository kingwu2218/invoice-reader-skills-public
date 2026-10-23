"""Public classification controls; freeze answers before running a model."""
import json
from pathlib import Path
import sys
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'core/scripts'))
from buckets import default_text

NAME = 'cash-memo-classification-v1'
FILE = NAME + '.pdf'
TITLES = ['CASH MEMO', 'OFFICIAL RECEIPT', 'TAX INVOICE / RECEIPT']
TYPES = ['Invoice', 'Receipt', 'Invoice']
TOTALS = ['58', '58', '93']

def table(rows, columns, identity=('File', 'Pages')):
    return {'identity': list(identity), 'columns': [{'label': k, 'kind': kind} for k, kind in columns], 'rows': rows}

def expected():
    docs = [{'File': FILE, 'Pages': str(i+1), 'Document type': TYPES[i],
             'Document title': TITLES[i], 'Total': TOTALS[i]} for i in range(3)]
    rawdocs = [{'File': FILE, 'Pages': str(i+1), 'Document type': TYPES[i],
                'fields.document_title': TITLES[i], 'fields.total': TOTALS[i]} for i in range(3)]
    lines = [{'File': FILE, 'Pages': str(i+1), 'Line': '1', 'Description': label,
              'Quantity': '1', 'Unit price': TOTALS[i], 'Line total': TOTALS[i]}
             for i, label in [(0, 'Repair kit'), (2, 'Adapter kit')]]
    columns = [('Document type', 'text'), ('Document title', 'text'), ('Total', 'amount')]
    return {'tables': {
        'Billing documents': table([docs[0], docs[2]], columns),
        'Reference documents': table([docs[1]], columns),
        'Line items': table(lines, [('Description','text'),('Quantity','number'),('Unit price','amount'),('Line total','amount')], ('File','Pages','Line'))},
        'raw_tables': {'Raw documents': table(rawdocs, [('Document type','text'),('fields.document_title','text'),('fields.total','text')])}}

def control_payload():
    docs = []
    for i in range(3):
        d = {'document_id': f'classification-{i+1}', 'file': FILE, 'pages': str(i+1),
             'document_type': TYPES[i], 'fields': {'document_title': TITLES[i], 'total': TOTALS[i]}}
        if i != 1:
            d['line_items'] = [{'description': 'Repair kit' if i == 0 else 'Adapter kit',
                                'quantity': '1', 'unit_price': TOTALS[i], 'line_total': TOTALS[i]}]
        docs.append(d)
    return {'schema_version': 1, 'documents': docs}

def build(root=ROOT):
    source = root / 'eval/fixtures' / FILE
    folder = root / 'eval/scenarios' / NAME
    if source.exists() or folder.exists():
        raise ValueError('Refuse to overwrite frozen source or references.')
    source.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(source), pagesize=A4, invariant=1)
    for i, title in enumerate(TITLES):
        pdf.setFont('Helvetica-Bold', 22); pdf.drawString(48, 770, title)
        pdf.setFont('Helvetica', 12)
        common = ['Example Workshop Ltd', 'Customer: Tallowmere Consulting Ltd', 'Date: 11 Oct 2026']
        for n, text in enumerate(common): pdf.drawString(48, 724-n*25, text)
        if i == 1:
            body = ['Receipt No.: RC-0312', 'Received with thanks: HKD 58',
                    'Payment for invoice CM-0312', 'This acknowledges payment of that invoice.', 'TOTAL RECEIVED: HKD 58']
            for n, text in enumerate(body): pdf.drawString(48, 608-n*35, text)
        else:
            pdf.drawString(48, 608, 'No.: CM-0312' if i == 0 else 'No.: TI-0312')
            pdf.setFont('Helvetica-Bold', 12)
            for x, text in [(48,'Description'), (300,'Qty'), (370,'Unit price'), (470,'Amount')]: pdf.drawString(x,552,text)
            pdf.line(48,543,545,543); pdf.setFont('Helvetica',12)
            for x, text in [(48,'Repair kit' if i == 0 else 'Adapter kit'), (300,'1'), (370,TOTALS[i]), (470,TOTALS[i])]: pdf.drawString(x,520,text)
            pdf.drawString(48,460,'TOTAL: HKD ' + TOTALS[i])
            pdf.drawString(48,420,'PAID IN FULL - CASH')
            pdf.drawString(48,390,'Goods supplied at the counter.')
        pdf.setFont('Helvetica',9); pdf.drawString(48,45,'Public synthetic document. Not a real transaction.')
        pdf.showPage()
    pdf.save()
    folder.mkdir(parents=True)
    (folder/'custom.md').write_text(default_text(confirmed=True),encoding='utf-8')
    (folder/'case.toml').write_text(f'source = "fixtures/{FILE}"\nmedium = "synthetic-native-print"\ncontent_group = "{NAME}"\nexpected_routes = ["A", "A", "A"]\n',encoding='utf-8')
    (folder/'expected.json').write_text(json.dumps(expected(),indent=2)+'\n',encoding='utf-8')

if __name__ == '__main__':
    build()
