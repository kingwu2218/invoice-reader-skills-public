"""Fixed image-only references support arbitrary certificate names, not only Other."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from test_custom_extraction import ROOT, coal_documents, process
sys.path.insert(0, str(ROOT/'eval/runner'))
import raw
import score


class ScanLineCases(unittest.TestCase):
    def test_generator_is_reentrant_and_keeps_both_frozen_versions(self):
        spec = importlib.util.spec_from_file_location('scan_cases', ROOT/'eval/tools/make_scan_line_cases.py')
        generator = importlib.util.module_from_spec(spec); spec.loader.exec_module(generator)
        for version in (2, 1, 2):
            for purpose in ('payment', 'energy'):
                folder = ROOT/'eval/scenarios'/f'coal-scan-{purpose}-lines-v{version}'
                expected, custom = generator.build(purpose, version)
                self.assertEqual(expected, json.loads((folder/'expected.json').read_text()))
                self.assertEqual(custom, (folder/'custom.md').read_text())

    def test_both_purposes_through_raw_and_workbook(self):
        for purpose in ('payment', 'energy'):
            folder = ROOT/'eval/scenarios'/f'coal-scan-{purpose}-lines-v2'
            expected = json.loads((folder/'expected.json').read_text())
            data = coal_documents('coal-'+purpose)
            for doc in data['documents']:
                doc['file'] = 'coal-scan.pdf'
            for label in ('Lab certificate', 'Laboratory certificate', 'Other'):
                with self.subTest(purpose=purpose, label=label):
                    data['documents'][1]['document_type'] = label
                    result = raw.score(data, expected['raw_tables'], score.score_table)
                    self.assertEqual(result['details'], [])
                    self.assertEqual(result['tables']['Raw line items']['matched'], 1)
            with tempfile.TemporaryDirectory() as scratch:
                inp = Path(scratch)/'input.json'; inp.write_text(json.dumps(data))
                out = Path(scratch)/'out.xlsx'
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(process.main(['--extraction', str(inp), '--custom', str(folder/'custom.md'),
                                                  '--out', str(out)]), 0)
                result = score.score_workbook(out, expected)
                self.assertEqual(result['details'], [])
                self.assertFalse(any(result['checks'].values()))
            data['documents'][0]['line_items'][0]['line_total'] = '105.00'
            self.assertEqual(raw.score(data, expected['raw_tables'], score.score_table)['cells']['silent_error'], 1)

    def test_old_reference_defect_remains_reproducible(self):
        folder = ROOT/'eval/scenarios/coal-scan-energy-lines-v1'
        expected = json.loads((folder/'expected.json').read_text())
        data = coal_documents()
        for doc in data['documents']: doc['file'] = 'coal-scan.pdf'
        result = raw.score(data, expected['raw_tables'], score.score_table)
        self.assertEqual(result['tables']['Raw documents']['missing'], 1)
        self.assertEqual(result['tables']['Raw documents']['extra'], 1)
