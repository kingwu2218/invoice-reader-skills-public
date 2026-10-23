"""Create public raster-only digit-boundary controls, not human handwriting.

The fixed expectations test a nearby rule, a real leading digit and a covered
prefix. Never replace an existing source/reference after a model has seen it.
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
sys.path.insert(0, str(ROOT/'core/scripts'))
from buckets import default_text

NAME = 'digit-boundary-v1'
FILE = NAME+'.pdf'
IDENTITY = ['File', 'Pages', 'Document type', 'Document occurrence']


def table(rows, labels, identity=IDENTITY):
    return {'identity':identity, 'columns':[{'label':label,'kind':kind} for label,kind in labels], 'rows':rows}


def expected():
    docs, rawdocs, summaries, details, rawdetails = [], [], [], [], []
    for page, value in [('1','684'), ('2','1684'), ('3',None)]:
        base = dict(zip(IDENTITY, [FILE, page, 'Invoice', '1']))
        number = 'SYN-BOUNDARY-0'+page
        status = 'printed' if value is not None else 'unclear'
        docs.append({**base, 'Document number':number, 'Total':value})
        rawdocs.append({**base, 'fields.document_number':number, 'fields.total':value})
        summaries.append({**base, 'Labelled total':value})
        key = {**base, 'Field key':'labelled_total', 'Occurrence':'1'}
        details.append({**key, 'Status':status, 'Value (as printed)':value})
        rawdetails.append({**key, 'observation.status':status, 'observation.value':value, 'observation.pages':page})
    return {'tables':{
        'Billing documents':table(docs, [('Document number','text'),('Total','amount')]),
        'Requested data':table(summaries, [('Labelled total','text')]),
        'Requested values':table(details, [(k,'text') for k in ('Status','Value (as printed)','Pages')], IDENTITY+['Field key','Occurrence'])},
        'raw_tables':{
            'Raw documents':table(rawdocs, [(k,'text') for k in ('fields.document_number','fields.total')]),
            'Raw requested values':table(rawdetails, [(k,'text') for k in ('observation.status','observation.value','observation.pages')], IDENTITY+['Field key','Occurrence'])}}


def control_payload():
    """Supplied transcription for scorer/processor tests; never model evidence."""
    docs=[]
    for page,value in [('1','684'),('2','1684'),('3',None)]:
        fields={'document_number':'SYN-BOUNDARY-0'+page}
        observation={'status':'printed' if value is not None else 'unclear',
                     'pages':page, 'evidence':'Labelled TOTAL; prefix covered on page 3.'}
        if value is not None:
            fields['total']=value; observation['value']=value
        docs.append({'document_id':'boundary-'+page,'file':FILE,'pages':page,
                     'document_type':'Invoice','fields':fields,
                     'unclear':[] if value is not None else ['total'],
                     'custom_fields':{'labelled_total':[observation]}})
    return {'schema_version':1,'documents':docs}


def build(root=ROOT):
    source=root/'eval/fixtures'/FILE
    folder=root/'eval/scenarios'/NAME
    if source.exists() or folder.exists():
        raise ValueError('Refuse to overwrite frozen source or references.')
    vector=BytesIO(); pdf=canvas.Canvas(vector,pagesize=A4,invariant=1)
    for page in range(1,4):
        pdf.setFont('Helvetica-Bold',24);pdf.drawString(48,770,'INVOICE')
        pdf.setFont('Helvetica',12)
        for y,text in [(730,'Invoice No.: SYN-BOUNDARY-0'+str(page)),
                       (702,'Seller: Example Maintenance Ltd'),
                       (674,'Bill to: Tallowmere Consulting Ltd'),(646,'Date: 10 Oct 2026')]:
            pdf.drawString(48,y,text)
        pdf.setFont('Helvetica-Bold',18);pdf.drawString(250,450,'TOTAL')
        pdf.setFont('Courier-Bold',24)
        if page==1:
            pdf.setLineWidth(1.2);pdf.line(373,420,373,530)
            pdf.line(245,530,475,530);pdf.line(245,420,475,420)
            pdf.drawString(380,450,'684')
        elif page==2:
            pdf.drawString(368,450,'1684')
        else:
            pdf.drawString(368,450,'8684')
            pdf.setFillColorRGB(.55,.55,.55)
            pdf.rect(367,445,14.5,33,stroke=0,fill=1)
            pdf.setFillColorRGB(0,0,0)
        pdf.setFont('Helvetica',9)
        pdf.drawString(48,45,'Public synthetic invoice. Not a real transaction.')
        pdf.showPage()
    pdf.save()
    source.parent.mkdir(parents=True,exist_ok=True)
    raster=canvas.Canvas(str(source),pagesize=A4,invariant=1)
    with pdfium.PdfDocument(vector.getvalue()) as document:
        for page in document:
            bitmap=page.render(scale=3)
            try:
                raster.drawImage(ImageReader(bitmap.to_pil()),0,0,width=A4[0],height=A4[1])
                raster.showPage()
            finally:
                bitmap.close();page.close()
    raster.save()
    folder.mkdir(parents=True)
    custom=default_text(confirmed=True).replace('|---|---|---|---|---|',
        '|---|---|---|---|---|\n| labelled_total | Labelled total | The complete amount beside TOTAL as printed; leave unreadable amounts unclear | one | yes |',1)
    (folder/'custom.md').write_text(custom,encoding='utf-8')
    (folder/'case.toml').write_text(f'source = "fixtures/{FILE}"\nmedium = "synthetic-raster-print"\ncontent_group = "{NAME}"\nexpected_routes = ["B", "B", "B"]\n',encoding='utf-8')
    (folder/'expected.json').write_text(json.dumps(expected(),indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    build()
