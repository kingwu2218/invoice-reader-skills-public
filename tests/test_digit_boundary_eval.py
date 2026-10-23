"""The matrix catches added/removed leading digits and guesses under occlusion."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eval/tools'))
sys.path.insert(0,str(ROOT/'eval/runner'))
from make_digit_boundary_case import control_payload, expected, NAME, FILE
import raw
import score
from test_custom_extraction import process


class DigitBoundaryEvaluation(unittest.TestCase):
    def test_supplied_transcription_scores_in_both_layers_without_changing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp);data=control_payload()
            source=work/'extraction.json';source.write_text(json.dumps(data))
            original=source.read_bytes()
            (work/'manifest.json').write_text(json.dumps({'version':1,'inputs':[{'file':FILE,'extraction':'extraction.json'}]}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(process.main(['--manifest',str(work/'manifest.json'),
                    '--custom',str(ROOT/'eval/scenarios'/NAME/'custom.md'),'--out',str(work/'output.xlsx')]),0)
            for result in [raw.score(data,expected()['raw_tables'],score.score_table),
                           score.score_workbook(work/'output.xlsx',expected())]:
                self.assertFalse(result['details'])
                self.assertFalse(any(result['checks'].values()))
                self.assertFalse(any(v.get('extra',0) or v.get('missing',0) for v in result['tables'].values()))
            self.assertEqual(source.read_bytes(),original)

    def test_added_digit_removed_real_digit_and_guessed_prefix_fail(self):
        for index,value,outcome in [(0,'1684','silent_error'),(1,'684','silent_error'),(2,'8684','invented')]:
            with self.subTest(index=index):
                data=copy.deepcopy(control_payload());data['documents'][index]['fields']['total']=value
                result=raw.score(data,expected()['raw_tables'],score.score_table)
                self.assertEqual(result['cells'][outcome],1)
                self.assertEqual(result['details'][0]['where'],f'Raw documents/{index}/fields.total')

    def test_unreadable_custom_value_cannot_hide_a_guess(self):
        data=control_payload()
        data['documents'][2]['custom_fields']['labelled_total'][0]['value']='8684'
        result=raw.score(data,expected()['raw_tables'],score.score_table)
        self.assertEqual(result['cells']['invented'],1)
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp);source=work/'extraction.json';source.write_text(json.dumps(data))
            before=source.read_bytes()
            (work/'manifest.json').write_text(json.dumps({'version':1,'inputs':[{'file':FILE,'extraction':source.name}]}))
            with redirect_stdout(io.StringIO()):
                code=process.main(['--manifest',str(work/'manifest.json'),
                    '--custom',str(ROOT/'eval/scenarios'/NAME/'custom.md'),'--out',str(work/'output.xlsx')])
            self.assertEqual(code,2)
            self.assertFalse((work/'output.xlsx').exists())
            self.assertEqual(source.read_bytes(),before)

    def test_committed_answers_match_controls_and_all_pages_are_image_only(self):
        import pypdfium2 as pdfium
        self.assertEqual(json.loads((ROOT/'eval/scenarios'/NAME/'expected.json').read_text()),expected())
        with pdfium.PdfDocument(ROOT/'eval/fixtures'/FILE) as document:
            self.assertEqual(len(document),3)
            for page in document:
                text=page.get_textpage()
                try:self.assertEqual(text.count_chars(),0)
                finally:text.close();page.close()


if __name__=='__main__':
    unittest.main()
