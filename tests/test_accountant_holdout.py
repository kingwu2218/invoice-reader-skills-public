"""Frozen public holdouts. These checks do not call a model."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_generator():
    spec = importlib.util.spec_from_file_location(
        'holdout_v1', ROOT / 'eval' / 'tools' / 'make_accountant_holdout_v1.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AccountantHoldout(unittest.TestCase):
    def test_references_keep_clear_values_and_a_blank_total(self):
        module = load_generator()
        harbour = module.harbour_expected()
        receipt = module.northwharf_expected()
        self.assertEqual(harbour['tables']['Billing documents']['rows'][0]['Total'], '180.00')
        self.assertEqual(harbour['tables']['Line items']['rows'][0]['Unit'], 'kWh')
        self.assertEqual(harbour['tables']['Requested values']['rows'][0]['Status'], 'printed')
        self.assertIsNone(receipt['tables']['Reference documents']['rows'][0]['Total'])
        self.assertEqual(receipt['tables']['Requested data']['rows'][0]['Storage fee'], '80.00')
        self.assertEqual(receipt['tables']['Reference documents']['rows'][0]['Document type'], 'Receipt')
        import sys
        sys.path.insert(0, str(ROOT / 'eval' / 'runner'))
        import raw
        raw.validate_line_definitions(harbour['raw_tables'])
        raw.validate_line_definitions(receipt['raw_tables'])

    def test_generator_refuses_to_overwrite(self):
        module = load_generator()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module.build(root)
            with self.assertRaises(ValueError):
                module.build(root)
            self.assertTrue((root / 'eval' / 'fixtures' / 'harbour-meter-v1.pdf').exists())
            self.assertTrue((root / 'eval' / 'scenarios' / 'northwharf-receipt-v1' / 'expected.json').exists())


if __name__ == '__main__':
    unittest.main()
