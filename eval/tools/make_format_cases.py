"""Invented formatting cases, not handwriting benchmarks. Never overwrite frozen answers."""
import json
from pathlib import Path
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'core/scripts'))
from buckets import default_text

IDENTITY = ['File','Pages','Document type','Document occurrence']

def table(rows, keys, identity):
    return {'identity':identity,'columns':[{'label':label,'kind':kind} for label,kind in keys], 'rows':rows}

def expected(purpose):
    base={'File':'format-pack.pdf'}
    invoice={**base,'Pages':'1','Document type':'Invoice','Document occurrence':'1'}
    cheque={**base,'Pages':'2','Document type':'Cheque','Document occurrence':'1'}
    standard = {
        'Line items':table([{**base,'Line':'1','Line total':'8750'}],
            [('Line total','amount')],['File','Line']),
        'Billing documents':table([{**invoice,'Document number':'SYN-842','Total':None}],
            [('Document number','text'),('Total','amount')],['File','Pages']),
        'Payments':table([{**cheque,'Cheque number':'006204','Amount':'8750','Date':'2026-11-24'}],
            [('Cheque number','text'),('Amount','amount'),('Date','date')],['File','Pages'])}
    rawdocs=table([{**invoice,'fields.document_number':'SYN-842'},
                   {**cheque,'fields.cheque_number':'006204','fields.amount':'8,750/','fields.payment_date':'24 11 2026'}],
        [(key,'text') for key in ('fields.document_number','fields.total','fields.cheque_number','fields.amount','fields.payment_date')],IDENTITY)
    key,label,value=('payment_amount','Payment amount','8,750/') if purpose=='payment' else ('project_ref','Project reference','Lobby hinge inspection')
    wide=[{**invoice,label:None if purpose=='payment' else value},{**cheque,label:value}]
    standard['Requested data']=table(wide,[(label,'text')],['File','Pages'])
    observations=[]
    for doc in (invoice,cheque):
        absent=purpose=='payment' and doc['Pages']=='1'
        observations.append({**doc,'Field key':key,'Occurrence':'1','observation.status':'absent' if absent else 'printed',
                             'observation.value':None if absent else value,'observation.pages':None if absent else doc['Pages']})
    rawcustom=table(observations,[(key,'text') for key in ('observation.status','observation.value','observation.pages')],
                    IDENTITY+['Field key','Occurrence'])
    standard['Requested values']=table([
        {'File':o['File'],'Document pages':o['Pages'],'Field key':key,'Occurrence':'1',
         'Status':o['observation.status'],'Value (as printed)':o['observation.value'],'Pages':o['observation.pages']}
        for o in observations], [('Status','text'),('Value (as printed)','text'),('Pages','text')],
        ['File','Document pages','Field key','Occurrence'])
    return {'tables':standard,'raw_tables':{'Raw documents':rawdocs,'Raw requested values':rawcustom}}

def main():
    pdfpath=ROOT/'eval/fixtures/format-pack.pdf'
    cases=[ROOT/'eval/scenarios'/('format-'+p) for p in ('payment','project')]
    if pdfpath.exists() or any(c.exists() for c in cases):
        raise ValueError('Do not overwrite existing fixture or references')
    pdfpath.parent.mkdir(parents=True,exist_ok=True)
    pdf=canvas.Canvas(str(pdfpath),pagesize=A4,invariant=1)
    pages=[['INVOICE','Invoice No.: SYN-842','Seller: Example Workshop Ltd',
            'Bill to: Tallowmere Consulting Ltd','Date: 24 Nov 2026','Re: Lobby hinge inspection',
            'Description                         Amount (HK$)','Inspection service                  8,750.00',
            'No payment deadline is specified.'],
           ['CHEQUE - SYNTHETIC SAMPLE','Example Bank - invalid payment instrument',
            'Cheque serial: 006204','Bank code: 123   Account: 44556677',
            'Pay: Example Workshop Ltd','Payer: Tallowmere Consulting Ltd','Amount (HKD): 8,750/',
            'Date (Day Month Year): 24 11 2026','Re: Lobby hinge inspection']]
    for number,lines in enumerate(pages,1):
        pdf.setFont('Helvetica',9)
        pdf.drawString(42,815,'Invented printed-format fixture. Not a real transaction or handwriting sample.')
        for i,line in enumerate(lines):
            pdf.setFont('Helvetica-Bold' if i==0 else 'Helvetica',18 if i==0 else 12)
            pdf.drawString(42,770-i*42,line)
        pdf.setFont('Helvetica',9);pdf.drawString(42,35,f'Public synthetic fixture | Page {number} of 2')
        pdf.showPage()
    pdf.save()
    for purpose,folder in zip(('payment','project'),cases):
        folder.mkdir(parents=True)
        row=('payment_amount | Payment amount | The amount in figures on a cheque, copied with its printed notation; absent on other documents'
             if purpose=='payment' else 'project_ref | Project reference | The description explicitly labelled Re: on each document')
        custom=default_text(confirmed=True).replace('|---|---|---|---|---|',f'|---|---|---|---|---|\n| {row} | one | no |',1)
        (folder/'custom.md').write_text(custom,encoding='utf-8')
        (folder/'expected.json').write_text(json.dumps(expected(purpose),indent=2),encoding='utf-8')
        (folder/'case.toml').write_text('source = "fixtures/format-pack.pdf"\nmedium = "printed-format"\ncontent_group = "format-pack"\nexpected_routes = ["A"]\n',encoding='utf-8')
    print('Created one invented PDF and two frozen raw/workbook scenarios.')

if __name__=='__main__':
    main()
