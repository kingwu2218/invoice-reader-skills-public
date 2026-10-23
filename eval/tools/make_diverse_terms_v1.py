"""Public synthetic credit/proforma pair with different labelled amounts."""
import json
from pathlib import Path
import sys

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'core/scripts'))
from buckets import default_text

NAME='diverse-terms-v1'
FILE=NAME+'.pdf'
IDENTITY=['File','Pages','Document type','Document occurrence']

def table(rows,columns,identity=IDENTITY):
    return {'identity':list(identity),'columns':[{'label':label,'kind':kind} for label,kind in columns],
            'rows':rows}

def expected():
    credit=dict(zip(IDENTITY,[FILE,'1','Credit note','1']))
    proforma=dict(zip(IDENTITY,[FILE,'1','Proforma invoice','1']))
    observations=[{**base,'Field key':'balance_due','Occurrence':'1',
                   'Status':'printed','Value (as printed)':value,'Pages':'1'}
                  for base,value in [(credit,'0.00'),(proforma,'180.00')]]
    return {'tables':{
        'Billing documents':table([{**credit,'Document number':'CN-041','Currency':'USD','Total':'125.50'}],
                                  [('Document number','text'),('Currency','text'),('Total','amount')]),
        'Reference documents':table([{**proforma,'Document number':'PF-019','Currency':'EUR','Total':'240.00'}],
                                    [('Document number','text'),('Currency','text'),('Total','amount')]),
        'Requested data':table([{**credit,'Balance payable':'0.00'},{**proforma,'Balance payable':'180.00'}],
                               [('Balance payable','text')]),
        'Requested values':table(observations,[('Status','text'),('Value (as printed)','text'),('Pages','text')],
                                IDENTITY+['Field key','Occurrence'])},
        'raw_tables':{
        'Raw documents':table([{**credit,'fields.document_number':'CN-041','fields.currency':'USD','fields.total':'125.50'},
                               {**proforma,'fields.document_number':'PF-019','fields.currency':'EUR','fields.total':'240.00'}],
                              [('fields.document_number','text'),('fields.currency','text'),('fields.total','text')]),
        'Raw requested values':table([{**base,'Field key':'balance_due','Occurrence':'1',
                                      'observation.status':'printed','observation.value':value,'observation.pages':'1'}
                                     for base,value in [(credit,'0.00'),(proforma,'180.00')]],
                                     [('observation.status','text'),('observation.value','text'),('observation.pages','text')],
                                     IDENTITY+['Field key','Occurrence'])}}

def build():
    source=ROOT/'eval/fixtures'/FILE
    case=ROOT/'eval/scenarios'/NAME
    if source.exists() or case.exists():
        raise ValueError('Preserve frozen fixtures and answers; choose a new version.')
    source.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(source),pagesize=A4,invariant=1)
    c.setAuthor('Synthetic evaluation fixture')
    c.setTitle('Two independent synthetic documents')
    c.setFont('Helvetica',9)
    c.drawString(45,810,'PUBLIC SYNTHETIC FIXTURE - NOT A REAL TRANSACTION')
    c.setFont('Helvetica-Bold',18)
    c.drawString(45,770,'CREDIT NOTE')
    c.setFont('Helvetica',12)
    for y,text in [(739,'Document number: CN-041'),(717,'Issued: 21 October 2026'),
                   (695,'Seller: Cedar Stage Supplies'),(673,'Original invoice reference: INV-0037'),
                   (645,'Returned display panels - credit summary only'),
                   (613,'TOTAL CREDIT: USD 125.50'),(585,'Balance due: USD 0.00')]:
        c.drawString(45,y,text)
    c.setFont('Helvetica',9)
    c.drawString(45,555,'The credit is printed as a positive amount. No line-item table is supplied.')
    c.line(40,520,550,520)
    c.setFont('Helvetica-Bold',18)
    c.drawString(45,477,'PROFORMA INVOICE')
    c.setFont('Helvetica',12)
    for y,text in [(445,'Document number: PF-019'),(423,'Issued: 22 October 2026'),
                   (401,'Seller: Willow Exhibition Hire'),(379,'Project reference: JOB-048'),
                   (347,'TOTAL: EUR 240.00'),(319,'Deposit received: EUR 60.00'),
                   (291,'Amount due: EUR 180.00'),(263,'Payment due date: 30 October 2026')]:
        c.drawString(45,y,text)
    c.setFont('Helvetica',9)
    c.drawString(45,225,'Summary only. This proforma is a separate document from the credit note above.')
    c.showPage();c.save()
    case.mkdir(parents=True)
    (case/'case.toml').write_text('source = "fixtures/'+FILE+'"\nmedium = "synthetic-native"\ncontent_group = "'+NAME+'"\nexpected_routes = ["A"]\n',encoding='utf-8')
    custom=default_text(confirmed=True).replace('|---|---|---|---|---|',
        '|---|---|---|---|---|\n| balance_due | Balance payable | Numeric token labelled Balance due or Amount due on each document; copy only the numeric token without a currency unit. Do not substitute a total or deposit. | one | no |',1)
    (case/'custom.md').write_text(custom,encoding='utf-8')
    (case/'expected.json').write_text(json.dumps(expected(),indent=2)+'\n',encoding='utf-8')
    print('Created '+FILE+' and frozen raw/workbook expectations.')

if __name__=='__main__':
    build()
