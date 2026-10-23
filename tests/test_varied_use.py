import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'eval/runner'))
sys.path.insert(0, str(ROOT/'eval/tools'))
import build_varied_use as fixture
import varied_use
import first_use
import process
import raw
import score
import review_varied_use
from contextlib import closing
import pypdfium2 as pdfium


class VariedReferences(unittest.TestCase):
    def test_sources_have_three_pages_with_image_only_middle_page(self):
        with closing(pdfium.PdfDocument(str(ROOT/'eval/fixtures'/fixture.FILES[0]))) as pdf:
            self.assertEqual(len(pdf), 1)
            with closing(pdf[0]) as page, closing(page.get_textpage()) as text:
                self.assertIn('RT-2048', text.get_text_range()); self.assertIn('CASH MEMO', text.get_text_range())
        with closing(pdfium.PdfDocument(str(ROOT/'eval/fixtures'/fixture.FILES[1]))) as pdf:
            self.assertEqual(len(pdf), 2)
            with closing(pdf[0]) as page, closing(page.get_textpage()) as text:
                self.assertEqual(text.count_chars(), 0)
            with closing(pdf[1]) as page, closing(page.get_textpage()) as text:
                self.assertIn('24.8 MJ/kg', text.get_text_range())

    def score_raw(self, purpose, payload=None):
        return raw.score(payload or fixture.payload(purpose), fixture.expected(purpose)['raw_tables'], score.score_table,
                         {k: label for k, label, _ in fixture.SPECS[purpose]})

    def test_authored_references_match_frozen_files(self):
        for purpose in fixture.SPECS:
            self.assertEqual(fixture.expected(purpose), varied_use.read(ROOT/'eval/workflows/varied-use-v1'/f'{purpose}.json'))

    def test_v2_changes_only_certificate_type_not_values_or_scorer(self):
        for purpose in fixture.SPECS:
            old = fixture.expected(purpose)
            corrected = review_varied_use.corrected(old)
            self.assertEqual(corrected, varied_use.read(ROOT/'eval/workflows/varied-use-v2'/f'{purpose}.json'))
            original_text = json.dumps(old)
            self.assertEqual(json.dumps(corrected).replace('"Document type": "Lab certificate"', '"Document type": "Other"'), original_text)

    def test_existing_contract_certificate_passes_v2_but_v1_mismatches(self):
        data = fixture.payload('quality'); data['documents'][3]['document_type'] = 'Lab certificate'
        self.assertGreater(self.score_raw('quality', data)['cells']['miss'], 0)
        reference = review_varied_use.corrected(fixture.expected('quality'))
        labels = {k: label for k, label, _ in fixture.SPECS['quality']}
        result = raw.score(data, reference['raw_tables'], score.score_table, labels)
        self.assertFalse(result['details'])
        data['documents'][3]['custom_fields']['energy'][1]['unit'] = 'kcal/kg'
        self.assertEqual(raw.score(data, reference['raw_tables'], score.score_table, labels)['cells']['silent_error'], 1)

    def test_positive_raw_and_real_workbook_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for purpose in fixture.SPECS:
                result = self.score_raw(purpose)
                self.assertFalse(result['details'])
                self.assertGreater(result['cells']['correct_blank'], 0)
                extraction = folder/f'{purpose}.json'; custom = folder/f'{purpose}.md'; book = folder/f'{purpose}.xlsx'
                extraction.write_text(json.dumps(fixture.payload(purpose)), encoding='utf-8')
                custom.write_text(fixture.custom(purpose), encoding='utf-8')
                self.assertEqual(process.main(['--extraction', str(extraction), '--custom', str(custom), '--out', str(book)]), 0)
                result = score.score_workbook(book, fixture.expected(purpose))
                self.assertFalse(result['details'], result['details'])
                self.assertFalse(sum(result['checks'].values()), result['checks'])

    def test_missing_file_and_same_page_order_fail(self):
        missing = fixture.payload('payment'); missing['documents'] = missing['documents'][:2]
        self.assertEqual(self.score_raw('payment', missing)['tables']['Raw documents']['missing'], 2)
        swapped = fixture.payload('payment'); swapped['documents'][:2] = swapped['documents'][1::-1]
        result = self.score_raw('payment', swapped)
        self.assertEqual(result['tables']['Raw documents']['matched'], 4)
        self.assertGreater(result['cells']['silent_error'], 0)

    def test_silent_correction_and_missing_date_guess_fail(self):
        data = fixture.payload('payment'); data['documents'][2]['fields']['total'] = '125.00'
        self.assertEqual(self.score_raw('payment', data)['cells']['silent_error'], 1)
        data = fixture.payload('payment'); data['documents'][1]['custom_fields']['payment_due'] = [dict(status='printed', value='12 Nov 2026', pages='1', evidence='invented')]
        self.assertGreater(self.score_raw('payment', data)['cells']['invented'], 0)

    def test_converted_units_and_wrong_purpose_fail(self):
        data = fixture.payload('quality'); obs = data['documents'][3]['custom_fields']['energy'][1]
        obs.update(value='5,922', unit='kcal/kg')
        self.assertEqual(self.score_raw('quality', data)['cells']['silent_error'], 2)
        result = self.score_raw('quality', fixture.payload('payment'))
        self.assertGreater(result['tables']['Raw requested values']['missing'], 0)
        self.assertGreater(result['cells']['miss'], 0)


class VariedPlan(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name); self.repo = root/'repo'; self.work = root/'external'; self.batch = self.repo/'eval/runs/test'
        (self.repo/'eval/fixtures').mkdir(parents=True)
        for name in fixture.FILES: shutil.copyfile(ROOT/'eval/fixtures'/name, self.repo/'eval/fixtures'/name)
        shutil.copytree(ROOT/'eval/workflows/varied-use-v1', self.repo/'eval/workflows/varied-use-v1')
        for name in ['eval/runner/varied_use.py', 'adapters/codex/eval_adapter.py', 'tools/skillsets.py', 'eval/tools/build_varied_use.py']:
            dest = self.repo/name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT/name, dest)
        self.package = self.repo/'package'; self.package.mkdir(); (self.package/'SKILL.md').write_text('test skill')
        for context in [patch.object(varied_use, 'REPO', self.repo),
                        patch.object(first_use, 'package', return_value=({'version': 'test'}, self.package)),
                        patch.object(varied_use.subprocess, 'run', return_value=SimpleNamespace(stdout='test-cli'))]:
            context.start(); self.addCleanup(context.stop)

    def plan(self): varied_use.plan(self.batch, self.work, 'selected', 'provider', 'https')

    def test_clean_workspaces_no_answers_and_same_sources(self):
        self.plan()
        data = varied_use.read(self.batch/'plan.json')
        self.assertEqual(len(data['trials']), 2)
        for trial in data['trials']:
            self.assertEqual({p.name for p in Path(trial['workspace']).iterdir()}, {'.agents', *fixture.FILES})
            for answer in ('RT-2048', '125.75', '5,870', 'expected.json'): self.assertNotIn(answer, trial['prompt'])
        self.assertEqual(data['opening_contract'], 'codex-opening-v9')

    def test_harness_reference_and_workspace_drift_rejected(self):
        self.plan(); path = self.repo/'eval/runner/varied_use.py'; original = path.read_bytes()
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'harness_hashes'): varied_use.load(self.batch, 1)
        path.write_bytes(original)
        (self.work/'chat-1/answers.txt').write_text('leaked')
        with patch.object(first_use.conversation, 'invoke') as invoke:
            self.assertIn('Initial workspace changed', varied_use.execute(self.batch, 1, 'start')['error']); invoke.assert_not_called()
        (self.batch/'trial-2/expected.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'reference changed'): varied_use.load(self.batch, 2)

    def test_attempt_reserved_and_unexecuted_report_not_success(self):
        self.plan()
        with patch.object(first_use.conversation, 'invoke', side_effect=RuntimeError('transport failed')) as invoke:
            self.assertEqual(varied_use.execute(self.batch, 1, 'start')['status'], 'incomplete')
            with self.assertRaises(FileExistsError): varied_use.execute(self.batch, 1, 'start')
            self.assertEqual(invoke.call_count, 1)
        result = varied_use.report(self.batch, self.batch/'report.json')
        self.assertEqual(result['completed_chats'], 0)
        self.assertIsNone(result['totals']['raw']['denominator'])
        self.assertNotIn(str(self.work), (self.batch/'report.json').read_text())
        with self.assertRaises(ValueError): varied_use.report(self.batch, self.batch/'report.json')


if __name__ == '__main__': unittest.main()
