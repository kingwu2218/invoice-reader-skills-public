"""Two public holdouts that were not used to draft the xAI prompt.

harbour-meter-v1 is a native-text utility invoice with a clear total, a kWh
line and a meter reading. northwharf-receipt-v1 is a raster receipt: one clear
fee and one covered total. The generator refuses to overwrite frozen bytes.
"""
from io import BytesIO
import json
from pathlib import Path
import sys

import pypdfium2 as pdfium
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'core' / 'scripts'))
from buckets import default_text

MARKER = '|---|---|---|---|---|'
IDENTITY = ['File', 'Pages', 'Document type', 'Document occurrence']


def table(rows, labels, identity):
    return {'identity': list(identity),
            'columns': [{'label': label, 'kind': kind} for label, kind in labels],
            'rows': rows}


def _custom(rows):
    text = default_text(confirmed=True)
    if MARKER not in text:
        raise ValueError('custom.md template marker changed')
    body = '\n'.join('| ' + ' | '.join(cells) + ' |' for cells in rows)
    return text.replace(MARKER, MARKER + '\n' + body, 1)


def harbour_expected():
    file = 'harbour-meter-v1.pdf'
    base = dict(zip(IDENTITY, [file, '1', 'Invoice', '1']))
    obs = {**base, 'Field key': 'meter_reading', 'Occurrence': '1'}
    return {'tables': {
        'Billing documents': table(
            [{**base, 'Document number': 'HM-7781', 'Total': '180.00'}],
            [('Document number', 'text'), ('Total', 'amount')], IDENTITY),
        'Line items': table(
            [{'File': file, 'Pages': '1', 'Line': '1', 'Description': 'Site electricity',
              'Quantity': '120', 'Unit': 'kWh', 'Unit price': '1.50', 'Line total': '180.00'}],
            [('Description', 'text'), ('Quantity', 'number'), ('Unit', 'text'),
             ('Unit price', 'amount'), ('Line total', 'amount')],
            ['File', 'Pages', 'Line']),
        'Requested data': table(
            [{**base, 'Meter reading': '45012 kWh'}],
            [('Meter reading', 'text')], IDENTITY),
        'Requested values': table(
            [{**obs, 'Status': 'printed', 'Value (as printed)': '45012', 'Unit': 'kWh', 'Pages': '1'}],
            [('Status', 'text'), ('Value (as printed)', 'text'), ('Unit', 'text'), ('Pages', 'text')],
            IDENTITY + ['Field key', 'Occurrence'])},
        'raw_tables': {
            'Raw documents': table(
                [{**base, 'fields.document_number': 'HM-7781', 'fields.total': '180.00'}],
                [('fields.document_number', 'text'), ('fields.total', 'text')], IDENTITY),
            'Raw line items': table(
                [{'File': file, 'Pages': '1', 'Document type': 'Invoice', 'Document occurrence': '1',
                  'Line': '1', 'item.description': 'Site electricity', 'item.quantity': '120',
                  'item.unit': 'kWh', 'item.unit_price': '1.50', 'item.line_total': '180.00'}],
                [('item.description', 'text'), ('item.quantity', 'text'), ('item.unit', 'text'),
                 ('item.unit_price', 'text'), ('item.line_total', 'text')],
                ['File', 'Pages', 'Document type', 'Document occurrence', 'Line']),
            'Raw requested values': table(
                [{**obs, 'observation.status': 'printed', 'observation.value': '45012',
                  'observation.unit': 'kWh', 'observation.pages': '1'}],
                [('observation.status', 'text'), ('observation.value', 'text'),
                 ('observation.unit', 'text'), ('observation.pages', 'text')],
                IDENTITY + ['Field key', 'Occurrence'])}}


def northwharf_expected():
    file = 'northwharf-receipt-v1.pdf'
    base = dict(zip(IDENTITY, [file, '1', 'Receipt', '1']))
    fee = {**base, 'Field key': 'storage_fee', 'Occurrence': '1'}
    bay = {**base, 'Field key': 'bay', 'Occurrence': '1'}
    return {'tables': {
        'Reference documents': table(
            [{**base, 'Document title': 'RECEIPT', 'Document number': 'NW-204', 'Total': None}],
            [('Document title', 'text'), ('Document number', 'text'), ('Total', 'amount')], IDENTITY),
        'Requested data': table(
            [{**base, 'Storage fee': '80.00', 'Bay': 'B12'}],
            [('Storage fee', 'text'), ('Bay', 'text')], IDENTITY),
        'Requested values': table(
            [{**fee, 'Status': 'printed', 'Value (as printed)': '80.00', 'Pages': '1'},
             {**bay, 'Status': 'printed', 'Value (as printed)': 'B12', 'Pages': '1'}],
            [('Status', 'text'), ('Value (as printed)', 'text'), ('Pages', 'text')],
            IDENTITY + ['Field key', 'Occurrence'])},
        'raw_tables': {
            'Raw documents': table(
                [{**base, 'fields.document_title': 'RECEIPT', 'fields.document_number': 'NW-204',
                  'fields.total': None}],
                [('fields.document_title', 'text'), ('fields.document_number', 'text'),
                 ('fields.total', 'text')], IDENTITY),
            'Raw requested values': table(
                [{**fee, 'observation.status': 'printed', 'observation.value': '80.00', 'observation.pages': '1'},
                 {**bay, 'observation.status': 'printed', 'observation.value': 'B12', 'observation.pages': '1'}],
                [('observation.status', 'text'), ('observation.value', 'text'), ('observation.pages', 'text')],
                IDENTITY + ['Field key', 'Occurrence'])}}


def _save(folder, name, source_name, medium, routes, expected, custom):
    folder.mkdir(parents=True)
    (folder / 'custom.md').write_text(custom, encoding='utf-8')
    (folder / 'case.toml').write_text(
        f'source = "fixtures/{source_name}"\nmedium = "{medium}"\ncontent_group = "{name}"\n'
        f'expected_routes = {json.dumps(routes)}\n', encoding='utf-8')
    (folder / 'expected.json').write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')


def _harbour_pdf(path):
    pdf = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    pdf.setFont('Helvetica-Bold', 22)
    pdf.drawString(48, 780, 'TAX INVOICE')
    pdf.setFont('Helvetica', 12)
    for y, text in ((748, 'Harbour Metering Ltd'), (726, 'Bill to: Tallowmere Consulting Ltd'),
                    (704, 'Invoice No. HM-7781'), (682, 'Date: 2 Mar 2026'),
                    (650, 'Meter reading: 45012 kWh')):
        pdf.drawString(48, y, text)
    pdf.setFont('Helvetica-Bold', 11)
    for x, text in ((48, 'Description'), (250, 'Qty'), (310, 'Unit'), (380, 'Unit price'), (490, 'Amount')):
        pdf.drawString(x, 600, text)
    pdf.line(48, 592, 548, 592)
    pdf.setFont('Helvetica', 12)
    for x, text in ((48, 'Site electricity'), (250, '120'), (310, 'kWh'), (380, '1.50'), (490, '180.00')):
        pdf.drawString(x, 570, text)
    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(360, 520, 'TOTAL 180.00')
    pdf.setFont('Helvetica', 9)
    pdf.drawString(48, 45, 'Public synthetic invoice. Not a real transaction.')
    pdf.showPage()
    pdf.save()


def _rasterise(vector_bytes, path):
    raster = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    document = pdfium.PdfDocument(vector_bytes)
    try:
        for page in document:
            bitmap = page.render(scale=3)
            try:
                raster.drawImage(ImageReader(bitmap.to_pil()), 0, 0, width=A4[0], height=A4[1])
                raster.showPage()
            finally:
                bitmap.close()
                page.close()
    finally:
        document.close()
    raster.save()


def _northwharf_pdf(path):
    vector = BytesIO()
    pdf = canvas.Canvas(vector, pagesize=A4, invariant=1)
    pdf.setFont('Helvetica-Bold', 26)
    pdf.drawString(48, 770, 'RECEIPT')
    pdf.setFont('Helvetica', 12)
    for y, text in ((730, 'Northwharf Storage Ltd'), (708, 'Received from: Tallowmere Consulting Ltd'),
                    (686, 'Receipt No. NW-204'), (664, 'Date: 4 Apr 2026'), (642, 'Bay: B12'),
                    (590, 'Storage fee'), (590, '')):
        if text:
            pdf.drawString(48, y, text)
    pdf.setFont('Courier-Bold', 18)
    pdf.drawString(180, 586, '80.00')
    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(48, 470, 'TOTAL RECEIVED')
    pdf.setFont('Courier-Bold', 28)
    pdf.drawString(250, 462, '640.00')
    pdf.setFillColorRGB(0.35, 0.35, 0.35)
    pdf.rect(292, 458, 78, 36, stroke=0, fill=1)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont('Helvetica', 9)
    pdf.drawString(48, 45, 'Public synthetic receipt. Not a real transaction.')
    pdf.showPage()
    pdf.save()
    _rasterise(vector.getvalue(), path)


def build(root=ROOT):
    jobs = (
        ('harbour-meter-v1', 'synthetic-native-print', ['A'], harbour_expected(),
         _custom([('meter_reading', 'Meter reading',
                   'The number labelled Meter reading, with its printed unit', 'one', 'yes')]),
         _harbour_pdf),
        ('northwharf-receipt-v1', 'synthetic-raster-print', ['B'], northwharf_expected(),
         _custom([('storage_fee', 'Storage fee', 'The amount labelled Storage fee', 'one', 'yes'),
                  ('bay', 'Bay', 'The bay code labelled Bay', 'one', 'no')]),
         _northwharf_pdf),
    )
    for name, medium, routes, expected, custom, draw in jobs:
        source = root / 'eval' / 'fixtures' / (name + '.pdf')
        folder = root / 'eval' / 'scenarios' / name
        if source.exists() or folder.exists():
            raise ValueError('Refuse to overwrite frozen source or references.')
        source.parent.mkdir(parents=True, exist_ok=True)
        draw(source)
        _save(folder, name, source.name, medium, routes, expected, custom)


if __name__ == '__main__':
    build()
