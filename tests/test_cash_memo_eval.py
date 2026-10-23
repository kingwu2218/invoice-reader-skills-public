"""Classification mistakes must remain visible in raw and workbook scoring."""
import copy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'eval/tools'), str(ROOT/'eval/runner')]
from make_cash_memo_case import NAME, FILE, TITLES, expected, control_payload, build
import raw
import score
from test_custom_extraction import process

class CashMemoEvaluation(unittest.TestCase):
    def evaluate(self, data):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp); source=work/'raw.json'; source.write_text(json.dumps(data))
            before=source.read_bytes()
            (work/'manifest.json').write_text(json.dumps({'version':1,'inputs':[{'file':FILE,'extraction':'raw.json'}]}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(process.main(['--manifest',str(work/'manifest.json'),'--custom',str(ROOT/'eval/scenarios'/NAME/'custom.md'),'--out',str(work/'output.xlsx')]),0)
            results=[raw.score(data,expected()['raw_tables'],score.score_table), score.score_workbook(work/'output.xlsx',expected())]
            self.assertEqual(source.read_bytes(),before)
            return results

    def test_correct_paid_cash_memo_receipt_and_combined_title(self):
        a,b=self.evaluate(control_payload())
        self.assertEqual(a['cells']['correct'],9)
        self.assertEqual(b['cells']['correct'],17)
        for r in [a,b]:
            self.assertFalse(r['details']); self.assertFalse(any(r['checks'].values()))
            self.assertFalse(any(t.get('missing') or t.get('extra') for t in r['tables'].values()))

    def test_cash_memo_as_receipt_is_not_silently_corrected(self):
        data=copy.deepcopy(control_payload());data['documents'][0]['document_type']='Receipt'
        a,b=self.evaluate(data)
        self.assertEqual(a['details'][0]['where'],'Raw documents/0/Document type')
        self.assertEqual(a['cells']['silent_error'],1)
        self.assertEqual(b['tables']['Billing documents']['missing'],1)
        self.assertEqual(b['tables']['Reference documents']['extra'],1)

    def test_real_receipt_and_tax_invoice_are_not_overcorrected(self):
        for index,wrong in [(1,'Invoice'),(2,'Receipt')]:
            with self.subTest(index=index):
                data=copy.deepcopy(control_payload());data['documents'][index]['document_type']=wrong
                a,b=self.evaluate(data)
                self.assertEqual(a['cells']['silent_error'],1)
                self.assertTrue(any(t.get('missing') or t.get('extra') for t in b['tables'].values()))

    def test_frozen_fixture_and_reference(self):
        import pypdfium2 as pdfium
        self.assertEqual(json.loads((ROOT/'eval/scenarios'/NAME/'expected.json').read_text()),expected())
        with pdfium.PdfDocument(ROOT/'eval/fixtures'/FILE) as document:
            self.assertEqual(len(document),3)
            for page,title in zip(document,TITLES):
                text=page.get_textpage()
                try:self.assertIn(title,text.get_text_range())
                finally:text.close();page.close()
        with self.assertRaises(ValueError):build()

if __name__=='__main__': unittest.main()
