"""Author public synthetic PDFs and references, before any model trial.

No model output is consumed. Refuses to overwrite the frozen dataset.
"""
from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'eval/runner'))
import raw
import buckets

VERSION = 'varied-use-v1'
FILES = ('batch-invoices.pdf', 'batch-support.pdf')
IDENTITY = ['File', 'Pages', 'Document type', 'Document occurrence']
SPECS = {
    'payment': [('invoice_number', 'Invoice number', 'one'), ('payment_due', 'Payment due date', 'one')],
    'quality': [('energy', 'Energy Level of Coal', 'many'), ('sulphur', 'Sulphur', 'many'), ('ash', 'Ash content', 'one')],
}


def documents():
    result = []
    for i, (file, title, number, date, due, subtotal, tax, total, desc, qty, price) in enumerate([
        (FILES[0], 'INVOICE', 'RT-2048', '01 Nov 2026', '12 Nov 2026', '230.00', '18.40', '248.40', 'Filter cartridges', '2', '115.00'),
        (FILES[0], 'CASH MEMO', 'CM-083', '02 Nov 2026', '', '70.00', '0.00', '70.00', 'Packing sleeves', '2', '35.00'),
        (FILES[1], 'INVOICE', 'SR-0912', '03 Nov 2026', '', '120.00', '5.00', '125.75', 'Sample analysis', '3', '40.00'),
    ], 1):
        fields = dict(document_title=title, document_number=number, issue_date=date,
                      seller_name='North Vale Supplies', buyer_name='Cedar Workshop', currency='HKD',
                      subtotal=subtotal, tax_amount=tax, total=total)
        if due: fields['due_date'] = due
        result.append(dict(file=file, pages='1', document_id=f'public-{i}', document_type='Invoice',
                           type_evidence=title, fields=fields,
                           line_items=[dict(description=desc, quantity=qty, unit_price=price, line_total=subtotal)]))
    result.append(dict(file=FILES[1], pages='2', document_id='public-4', document_type='Other',
                       type_evidence='LAB CERTIFICATE', fields={'document_title': 'LAB CERTIFICATE'}))
    return result


def payload(purpose):
    docs = documents()
    for doc in docs:
        doc['custom_fields'] = {key: [{'status': 'absent'}] for key, _, _ in SPECS[purpose]}
        if purpose == 'payment' and doc['document_type'] == 'Invoice':
            for key, field in [('invoice_number', 'document_number'), ('payment_due', 'due_date')]:
                if field in doc['fields']:
                    value = doc['fields'][field]
                    doc['custom_fields'][key] = [dict(status='printed', value=value, pages=doc['pages'], evidence=value)]
        if purpose == 'quality' and doc['document_type'] == 'Other':
            for key, values in [('energy', [('5,870', 'kcal/kg'), ('24.8', 'MJ/kg')]),
                                ('sulphur', [('0.42', '%'), ('0.35', '%')])]:
                doc['custom_fields'][key] = [dict(status='printed', value=value, unit=unit,
                    context=f'Sample Q-{17+i}', pages='2', evidence=f'Sample Q-{17+i}: {value} {unit}')
                    for i, (value, unit) in enumerate(values)]
    return {'schema_version': 1, 'documents': docs}


def custom(purpose):
    text = buckets.default_text(confirmed=True)
    rows = '\n'.join(f'| {key} | {label} | Printed {label}; preserve sample labels and units | {many} | no |'
                     for key, label, many in SPECS[purpose])
    return text.replace('|---|---|---|---|---|', '|---|---|---|---|---|\n'+rows)


def definition(identity, labels, rows, numeric=()):
    return dict(identity=identity, columns=[dict(label=label, kind='amount' if label in numeric else 'text')
                                           for label in labels], rows=rows)


def expected(purpose):
    # Transcribe authored facts into both layers. No workbook/model output supplies answers.
    data = payload(purpose)
    tables = raw.tables(data, {k: label for k, label, _ in SPECS[purpose]})
    rawdefs = {
        'Raw documents': definition(IDENTITY, ['fields.'+k for k in
            ('document_title', 'document_number', 'due_date', 'subtotal', 'tax_amount', 'total')], tables['Raw documents']),
        'Raw line items': definition(IDENTITY+['Line'], ['item.'+k for k in
            ('description', 'quantity', 'unit_price', 'line_total')], tables['Raw line items']),
        'Raw requested values': definition(IDENTITY+['Field', 'Occurrence'], ['observation.'+k for k in
            ('value', 'unit', 'context', 'pages', 'status')], tables['Raw requested values']),
    }
    base = [{key: row[key] for key in IDENTITY} for row in tables['Raw documents']]
    billing = []
    for i, doc in enumerate(data['documents'][:3]):
        f = doc['fields']
        billing.append(dict(base[i], **{'Document title': f['document_title'], 'Document number': f['document_number'],
            'Subtotal': f['subtotal'], 'Tax amount': f['tax_amount'], 'Total': f['total'],
            'Arithmetic check': 'Failed' if i == 2 else 'Passed', 'Needs review': 'Yes'}))
    wb = {
        'Billing documents': definition(IDENTITY, ['Document title', 'Document number', 'Subtotal', 'Tax amount',
            'Total', 'Arithmetic check', 'Needs review'], billing, ('Subtotal', 'Tax amount', 'Total')),
        'Other': definition(IDENTITY, ['Document title', 'Needs review'],
                            [dict(base[3], **{'Document title': 'LAB CERTIFICATE', 'Needs review': 'Yes'})]),
        'Line items': definition(IDENTITY+['Line'], ['Description', 'Quantity', 'Unit price', 'Line total'],
            [dict(base[i], Line='1', **{'Description': doc['line_items'][0]['description'],
                'Quantity': doc['line_items'][0]['quantity'], 'Unit price': doc['line_items'][0]['unit_price'],
                'Line total': doc['line_items'][0]['line_total']}) for i, doc in enumerate(data['documents'][:3])],
            ('Quantity', 'Unit price', 'Line total')),
    }
    wide, long = [], []
    for i, doc in enumerate(data['documents']):
        row = dict(base[i])
        for key, label, _ in SPECS[purpose]:
            observations = doc['custom_fields'][key]
            parts = []
            for n, obs in enumerate(observations, 1):
                item = {k: v for k, v in base[i].items() if k != 'Pages'}
                item.update({'Document pages': doc['pages'], 'Field': label, 'Occurrence': str(n), 'Status': obs['status']})
                for field, col in [('value', 'Value (as printed)'), ('unit', 'Unit'), ('context', 'Context'), ('pages', 'Pages')]:
                    if field in obs: item[col] = obs[field]
                long.append(item)
                if obs['status'] == 'printed':
                    parts.append((obs.get('context', '')+': ' if obs.get('context') else '')+
                                 obs['value']+(' '+obs['unit'] if obs.get('unit') else ''))
            if parts: row[label] = '\n'.join(parts)
        wide.append(row)
    labels = [label for _, label, _ in SPECS[purpose]]
    wb['Requested data'] = definition(IDENTITY, labels, wide)
    wb['Requested data']['exact_columns'] = ['Document ID', 'File', 'Pages', *labels, 'Needs review', 'Review reasons']
    wb['Requested values'] = definition(['File', 'Document pages', 'Document type', 'Document occurrence', 'Field', 'Occurrence'],
                                        ['Value (as printed)', 'Unit', 'Context', 'Pages', 'Status'], long)
    return dict(tables=wb, raw_tables=rawdefs)


def invoice(canvas, doc, top, height):
    f, line = doc['fields'], doc['line_items'][0]
    canvas.setStrokeColorRGB(.18, .3, .38); canvas.rect(38, top-height, 519, height)
    canvas.setFont('Helvetica-Bold', 18); canvas.drawString(54, top-29, f['document_title'])
    canvas.setFont('Helvetica', 11)
    lines = [f"Number: {f['document_number']}     Date: {f['issue_date']}",
             'Seller: North Vale Supplies', 'Buyer: Cedar Workshop', 'Currency: HKD']
    if f.get('due_date'): lines.append('Payment due date: '+f['due_date'])
    lines += ['', 'Description                         Qty     Unit price     Line total',
              f"{line['description']:<35} {line['quantity']:<7} {line['unit_price']:<14} {line['line_total']}", '',
              'Subtotal: '+f['subtotal'], 'Tax amount: '+f['tax_amount'], 'Total: '+f['total']]
    y = top-52
    for text in lines:
        canvas.setFont('Courier' if 'Unit price' in text or text.startswith(line['description']) else 'Helvetica', 10)
        canvas.drawString(54, y, text); y -= 18


def build():
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import pypdfium2 as pdfium
    destination = ROOT/'eval/workflows'/VERSION
    fixtures = ROOT/'eval/fixtures'
    if destination.exists() or any((fixtures/name).exists() for name in FILES):
        raise ValueError('Frozen dataset exists; create a new version instead of overwriting.')
    destination.mkdir(parents=True)
    docs = documents()
    c = canvas.Canvas(str(fixtures/FILES[0]), pagesize=(595, 842), invariant=1)
    invoice(c, docs[0], 804, 360); invoice(c, docs[1], 424, 360)
    c.setFont('Helvetica', 8); c.drawString(38, 35, 'Public synthetic test fixture - fictional organisations and transactions.')
    c.showPage(); c.save()
    buffer = BytesIO(); scan = canvas.Canvas(buffer, pagesize=(595, 842), invariant=1)
    invoice(scan, docs[2], 785, 400)
    scan.setFont('Helvetica', 9); scan.drawString(38, 45, 'Public synthetic test fixture - fictional transaction.')
    scan.showPage(); scan.save()
    c = canvas.Canvas(str(fixtures/FILES[1]), pagesize=(595, 842), invariant=1)
    with closing(pdfium.PdfDocument(buffer.getvalue())) as pdf, closing(pdf[0]) as page, closing(page.render(scale=2)) as bitmap:
        with bitmap.to_pil() as picture:
            c.drawImage(ImageReader(picture), 0, 0, width=595, height=842)
    c.showPage(); c.setFont('Helvetica-Bold', 22); c.drawString(48, 780, 'LAB CERTIFICATE')
    c.setFont('Helvetica', 12)
    lines = ['Certificate: QC-711', 'Invoice reference: SR-0912', '', 'Sample Q-17',
             'Energy Level of Coal: 5,870 kcal/kg', 'Sulphur: 0.42 %', '', 'Sample Q-18',
             'Energy Level of Coal: 24.8 MJ/kg', 'Sulphur: 0.35 %', '', 'End of reported results.']
    for i, text in enumerate(lines): c.drawString(48, 732-i*32, text)
    c.setFont('Helvetica', 9); c.drawString(48, 45, 'Public synthetic test fixture - fictional laboratory results.')
    c.showPage(); c.save()
    for purpose in SPECS:
        (destination/(purpose+'.json')).write_text(json.dumps(expected(purpose), indent=2)+'\n', encoding='utf-8')
    print(destination)


if __name__ == '__main__': build()
