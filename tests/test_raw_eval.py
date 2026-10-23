"""Independent raw/workbook signals, including boundaries against convenient scoring."""
import copy
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import unittest
import tempfile

from test_custom_extraction import ROOT, process
sys.path.insert(0,str(ROOT/'eval/runner'))
import raw
import score


def payload(purpose='payment'):
    docs=[{'document_id':'invoice','file':'format-pack.pdf','pages':'1','document_type':'Invoice',
        'fields':{'document_title':'INVOICE','document_number':'SYN-842'},
        'line_items':[{'description':'Inspection service','line_total':'8,750.00'}],'custom_fields':{}},
        {'document_id':'cheque','file':'format-pack.pdf','pages':'2','document_type':'Cheque',
        'fields':{'document_title':'CHEQUE - SYNTHETIC SAMPLE','cheque_number':'006204',
                  'amount':'8,750/','payment_date':'24 11 2026'},'custom_fields':{}}]
    for doc in docs:
        key='payment_amount' if purpose=='payment' else 'project_ref'
        item=({'status':'absent'} if doc['pages']=='1' and purpose=='payment' else
              {'status':'printed','value':'8,750/' if purpose=='payment' else 'Lobby hinge inspection',
               'pages':doc['pages'],'evidence':'Amount (HKD): 8,750/' if purpose=='payment' else 'Re: Lobby hinge inspection'})
        doc['custom_fields']={key:[item]}
    return {'schema_version':1,'documents':docs}


class RawEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)

    def prepare(self,purpose='payment'):
        work=self.folder/purpose
        source=work/'invoice-reader-work/run/extraction.json'
        source.parent.mkdir(parents=True)
        data=payload(purpose);source.write_text(json.dumps(data))
        manifest=source.with_name('manifest.json')
        manifest.write_text(json.dumps({'version':1,'inputs':[{'file':'format-pack.pdf','extraction':source.name}]}))
        case=ROOT/'eval/scenarios'/('format-'+purpose)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(process.main(['--manifest',str(manifest),'--out',str(work/'output.xlsx'),
                '--custom',str(case/'custom.md')]),0)
        return work,source,json.loads((case/'expected.json').read_text())

    def test_both_purposes_raw_and_workbook_and_source_preservation(self):
        for purpose in ('payment','project'):
            work,source,expected=self.prepare(purpose)
            original=source.read_bytes()
            info=raw.collect(work,work)
            result=raw.score(json.loads((work/'raw-extraction.json').read_text()),expected['raw_tables'],score.score_table)
            self.assertFalse(result['details'])
            self.assertEqual(score.metrics(result)['field_accuracy']['rate'],1)
            workbook=score.score_workbook(work/'output.xlsx',expected)
            self.assertFalse(workbook['details'])
            self.assertFalse(any(workbook['checks'].values()))
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(info['raw_extraction_hash'],hashlib.sha256((work/'raw-extraction.json').read_bytes()).hexdigest())

    def test_raw_is_not_normalised_to_hide_changed_printing(self):
        _,_,expected=self.prepare()
        data=payload();data['documents'][1]['fields']['amount']='8750'
        result=raw.score(data,expected['raw_tables'],score.score_table)
        self.assertEqual(result['cells']['silent_error'],1)

    def test_leading_zero_missing_document_and_extra_document(self):
        _,_,expected=self.prepare()
        data=payload();data['documents'][1]['fields']['cheque_number']='6204'
        self.assertEqual(raw.score(data,expected['raw_tables'],score.score_table)['cells']['silent_error'],1)
        data=payload();data['documents'].pop()
        result=raw.score(data,expected['raw_tables'],score.score_table)
        self.assertEqual(result['tables']['Raw documents']['missing'],1)
        data=payload();data['documents'].append(copy.deepcopy(data['documents'][1]))
        result=raw.score(data,expected['raw_tables'],score.score_table)
        self.assertEqual(result['tables']['Raw documents']['extra'],1)

    def test_multiple_manifests_are_not_cherry_picked(self):
        work,_,_=self.prepare()
        second=work/'invoice-reader-work/second';second.mkdir();(second/'manifest.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'exactly one'):
            raw.collect(work,work)

    def test_batch_missing_or_changed_raw_artifact_is_not_zero_accuracy(self):
        work,_,expected=self.prepare()
        run=self.folder/'batch/case/run-1';run.mkdir(parents=True)
        (run/'output.xlsx').write_bytes((work/'output.xlsx').read_bytes())
        (run/'expected.json').write_text(json.dumps(expected))
        meta={'valid':True};(run/'meta.json').write_text(json.dumps(meta))
        result=score.score_batch(self.folder/'batch')['runs'][0]
        self.assertEqual(result['raw_status'],'unavailable');self.assertNotIn('raw_metrics',result)
        meta.update(raw.collect(work,run));(run/'meta.json').write_text(json.dumps(meta))
        result=score.score_batch(self.folder/'batch')['runs'][0]
        self.assertEqual(result['raw_status'],'scored')
        self.assertEqual(result['raw_metrics']['field_accuracy']['rate'],1)
        (run/'raw-extraction.json').write_text('{}')
        result=score.score_batch(self.folder/'batch')['runs'][0]
        self.assertEqual(result['raw_status'],'unavailable')
