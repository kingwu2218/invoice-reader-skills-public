"""New frozen unit/context cases exercise real raw and workbook scoring separately."""
import copy
import io
import json
from contextlib import redirect_stdout
import unittest
import tempfile
from pathlib import Path

from test_raw_eval import payload, ROOT, raw, score, process


class UnitEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def sample(self, purpose):
        data = payload(purpose)
        if purpose == 'payment':
            data['documents'][1]['custom_fields']['payment_amount'][0].update(
                unit='HKD', context='Lobby hinge inspection')
        case = ROOT/'eval/scenarios'/f'format-{purpose}-units-v1'
        return data, case, json.loads((case/'expected.json').read_text())

    def test_value_unit_context_and_summary_match_frozen_contract(self):
        for purpose in ('payment', 'project'):
            data, case, expected = self.sample(purpose)
            source = self.folder/f'{purpose}.json'; source.write_text(json.dumps(data))
            before = source.read_bytes(); out = self.folder/f'{purpose}.xlsx'
            with redirect_stdout(io.StringIO()):
                self.assertEqual(process.main(['--extraction', str(source), '--out', str(out),
                                              '--custom', str(case/'custom.md')]), 0)
            self.assertFalse(score.score_workbook(out, expected)['details'])
            result = raw.score(data, expected['raw_tables'], score.score_table)
            self.assertFalse(result['details'])
            self.assertGreater(result['cells']['correct_blank'], 0)
            self.assertEqual(source.read_bytes(), before)

    def test_missing_wrong_or_duplicated_unit_and_wrong_context_fail(self):
        data, _, expected = self.sample('payment')
        for key, value in [('unit', ''), ('unit', 'USD'), ('value', '8,750/ HKD'), ('context', 'Other project')]:
            changed = copy.deepcopy(data)
            changed['documents'][1]['custom_fields']['payment_amount'][0][key] = value
            result = raw.score(changed, expected['raw_tables'], score.score_table)
            self.assertEqual(len(result['details']), 1)
            self.assertLess(score.metrics(result)['field_accuracy']['rate'], 1)

    def test_unrelated_page_currency_is_not_a_project_reference_unit(self):
        data, _, expected = self.sample('project')
        data['documents'][1]['custom_fields']['project_ref'][0]['unit'] = 'HKD'
        result = raw.score(data, expected['raw_tables'], score.score_table)
        self.assertEqual(result['cells']['invented'], 1)
