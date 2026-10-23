"""Raw line coverage and transcription must fail independently of numeric usability."""
from contextlib import redirect_stdout
from copy import deepcopy
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'eval/runner'))
sys.path.insert(0, str(ROOT/'core/scripts'))
import holdout
import raw
import run
import score

CASE = ROOT/'eval/scorer-cases/raw-lines-v1'


class RawLines(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((CASE/'extraction.json').read_text())
        self.definitions = json.loads((CASE/'expected.json').read_text())['raw_tables']

    def grade(self, payload=None):
        return raw.score(self.payload if payload is None else payload, self.definitions, score.score_table)

    def batch(self, folder, payload, definitions=None):
        dest = folder/'case/run-1'
        dest.mkdir(parents=True)
        book = Workbook(); book.save(dest/'output.xlsx'); book.close()
        # Empty workbook used only to exercise the batch raw scoring and CSV path.
        (dest/'expected.json').write_text(json.dumps({'tables': {}, 'raw_tables':
            self.definitions if definitions is None else definitions}))
        content = json.dumps(payload).encode()
        (dest/'raw-extraction.json').write_bytes(content)
        (dest/'meta.json').write_text(json.dumps({'valid': True,
            'evaluation_type': 'deterministic-scorer-regression',
            'raw_extraction_hash': hashlib.sha256(content).hexdigest()}))
        return score.score_batch(folder)['runs'][0]

    def test_fixed_baseline_and_document_local_ordinals(self):
        before = deepcopy(self.payload)
        result = self.grade()
        self.assertEqual(result['details'], [])
        self.assertEqual(result['cells'], {'correct': 25, 'correct_blank': 7})
        self.assertEqual(score.metrics(result)['field_accuracy']['denominator'], 25)
        self.assertEqual(result['tables']['Raw line items']['matched'], 4)
        self.assertEqual(result['tables']['Raw statement lines']['matched'], 2)
        rows = raw.tables(self.payload)['Raw line items']
        self.assertEqual([(r['Document occurrence'], r['Line']) for r in rows],
                         [('1','1'), ('1','2'), ('2','1'), ('2','2')])
        self.assertEqual(self.payload, before)
        for number, doc in enumerate(self.payload['documents']):
            doc['document_id'] = 'arbitrary-model-id-'+str(number)
        self.assertEqual(self.grade()['details'], [])

    def test_printed_notation_units_and_inconsistent_total_are_not_repaired(self):
        mutations = [(0, 'line_items', 0, 'line_total', '2,500.00'),
                     (0, 'line_items', 0, 'unit_price', '1250'),
                     (0, 'line_items', 0, 'unit', ''),
                     (0, 'line_items', 1, 'line_total', '310'),
                     (2, 'statement_lines', 0, 'date', '2026-10-04'),
                     (2, 'statement_lines', 1, 'reference', '41')]
        for doc, collection, line, key, value in mutations:
            with self.subTest(key=key, value=value):
                data = deepcopy(self.payload)
                data['documents'][doc][collection][line][key] = value
                result = self.grade(data)
                self.assertEqual(result['cells']['correct'], 24)
                self.assertEqual(result['cells']['miss' if not value else 'silent_error'], 1)
                self.assertEqual(score.metrics(result)['field_accuracy']['denominator'], 25)

    def test_numeric_workbook_equivalence_does_not_hide_raw_format_error(self):
        original = self.payload['documents'][0]['line_items'][0]['unit_price']
        self.assertEqual(score.normalise(original, 'number'), score.normalise('1250', 'number'))
        self.payload['documents'][0]['line_items'][0]['unit_price'] = '1250'
        self.assertEqual(self.grade()['cells']['silent_error'], 1)

    def test_line_order_and_same_page_document_order_are_not_value_matched(self):
        self.payload['documents'][0]['line_items'].reverse()
        result = self.grade()
        self.assertEqual(result['tables']['Raw line items']['matched'], 4)
        self.assertEqual(result['cells']['silent_error'], 10)
        self.payload['documents'][0]['line_items'].reverse()
        self.payload['documents'][0], self.payload['documents'][1] = (
            self.payload['documents'][1], self.payload['documents'][0])
        self.assertTrue(self.grade()['details'])

    def test_missing_and_duplicate_invoice_and_statement_rows(self):
        for doc, collection, title in [(0, 'line_items', 'Raw line items'),
                                       (2, 'statement_lines', 'Raw statement lines')]:
            with self.subTest(collection=collection):
                data = deepcopy(self.payload)
                data['documents'][doc][collection].pop()
                result = self.grade(data)
                self.assertEqual(result['tables'][title]['missing'], 1)
                self.assertEqual(result['cells']['miss'], 5)
                data = deepcopy(self.payload)
                data['documents'][doc][collection].append(deepcopy(data['documents'][doc][collection][0]))
                result = self.grade(data)
                self.assertEqual(result['tables'][title]['extra'], 1)
                self.assertEqual(result['cells']['invented'], 5)

    def test_unclear_flag_does_not_hide_an_invented_value(self):
        self.payload['documents'][1]['line_items'][1]['line_total'] = '90.00'
        self.assertEqual(self.grade()['cells']['invented'], 1)

    def test_extra_blank_row_and_wrong_source_are_structural_errors(self):
        self.payload['documents'][1]['line_items'].append({})
        result = self.grade()
        self.assertEqual(result['tables']['Raw line items']['extra'], 1)
        self.assertEqual(result['cells']['invented'], 0)
        self.assertEqual(result['details'][0]['outcome'], 'extra_row')
        self.payload['documents'][1]['line_items'].pop()
        self.payload['documents'][2]['pages'] = '3'
        result = self.grade()
        self.assertEqual(result['tables']['Raw statement lines']['missing'], 2)
        self.assertEqual(result['tables']['Raw statement lines']['extra'], 2)

    def test_debit_credit_swap_is_miss_and_invention(self):
        item = self.payload['documents'][2]['statement_lines'][0]
        item['credit'] = item.pop('debit')
        result = self.grade()
        self.assertEqual(result['cells']['miss'], 1)
        self.assertEqual(result['cells']['invented'], 1)
        self.assertEqual(score.metrics(result)['field_accuracy']['denominator'], 26)

    def test_missing_blank_row_still_fails_cli_and_csv_counts(self):
        self.payload['documents'][1]['line_items'].pop()
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch)
            result = self.batch(folder, self.payload)
            self.assertEqual(result['raw_metrics']['field_accuracy']['rate'], 1)
            self.assertEqual(result['raw_metrics']['line_item_recall'],
                             {'numerator': 3, 'denominator': 4, 'rate': .75})
            with (folder/'accuracy-matrix.csv').open(encoding='utf-8-sig') as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row['raw_line_item_recall_denominator'], '4')
            self.assertEqual(row['raw_statement_line_recall_numerator'], '2')
            self.assertEqual(row['raw_structural_failures'], '1')
            with patch.object(sys, 'argv', ['score.py', str(folder)]), redirect_stdout(io.StringIO()):
                self.assertEqual(score.main(), 1)

    def test_unconfigured_line_coverage_is_undefined_and_old_checks_unchanged(self):
        definitions = {'Raw documents': {'identity': ['File','Pages','Document type','Document occurrence'],
            'columns': [{'label': 'fields.document_number'}],
            'rows': [{'File': 'invented-lines.pdf', 'Pages': '1', 'Document type': 'Invoice',
                      'Document occurrence': '1', 'fields.document_number': 'LINE-001'}]}}
        with tempfile.TemporaryDirectory() as scratch:
            result = self.batch(Path(scratch), self.payload, definitions)
        self.assertIsNone(result['raw_metrics']['line_item_recall']['rate'])
        self.assertIsNone(result['raw_metrics']['statement_line_precision']['rate'])
        self.assertNotIn('Raw line items', result['raw']['tables'])

    def test_reference_keys_cannot_use_values_or_inflate_scores(self):
        for change in ('value_identity', 'missing_identity', 'duplicate_column', 'numeric_comparison',
                       'duplicate_row', 'nontext_value', 'bad_ordinal', 'unscorable_column'):
            with self.subTest(change=change):
                spec = deepcopy(self.definitions)
                table = spec['Raw line items']
                if change == 'value_identity': table['identity'][-1] = 'item.line_total'
                if change == 'missing_identity': table['rows'][0].pop('Document occurrence')
                if change == 'duplicate_column': table['columns'].append(deepcopy(table['columns'][0]))
                if change == 'numeric_comparison': table['columns'][0]['kind'] = 'number'
                if change == 'duplicate_row': table['rows'].append(deepcopy(table['rows'][0]))
                if change == 'nontext_value': table['rows'][0]['item.quantity'] = 2
                if change == 'bad_ordinal': table['rows'][0]['Line'] = '01'
                if change == 'unscorable_column': table['columns'][0]['label'] = 'item.unclear'
                with self.assertRaises(ValueError):
                    raw.score(self.payload, spec, score.score_table)
                with self.assertRaises(ValueError):
                    holdout.validate_expectations({'raw_tables': spec})

    def test_malformed_reference_rejected_during_public_preparation(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            scenario = root/'eval/scenarios/bad'; scenario.mkdir(parents=True)
            (scenario/'case.toml').write_text('source = "not-read.pdf"')
            self.definitions['Raw line items']['identity'] = ['item.line_total']
            (scenario/'expected.json').write_text(json.dumps({'raw_tables': self.definitions}))
            with patch.object(run, 'REPO', root), self.assertRaisesRegex(ValueError, 'identity'):
                run.expectation('bad')


if __name__ == '__main__':
    unittest.main()
