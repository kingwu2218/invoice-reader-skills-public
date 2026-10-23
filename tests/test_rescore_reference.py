"""Later reference versions rescore copied predictions; the original batch never changes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rescore_reference', ROOT/'eval/tools/rescore_reference.py')
rescore = importlib.util.module_from_spec(spec); spec.loader.exec_module(rescore)


class RescoreReference(unittest.TestCase):
    def test_mapped_case_uses_locked_new_reference_and_original_is_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            for case in ('mapped', 'unmapped'):
                run = base/'batch'/case/'run-1'
                run.mkdir(parents=True)
                (run/'meta.json').write_text(json.dumps({'artifact_hash': 'pkg', 'valid': False}), encoding='utf-8')
                (run/'expected.json').write_text('{"tables": {}, "old": true}', encoding='utf-8')
                (run/'raw-extraction.json').write_text('{}', encoding='utf-8')
            reference = base/'mapped-v2'
            reference.mkdir()
            (reference/'expected.json').write_text('{"tables": {}, "new": true}', encoding='utf-8')
            (reference/'holdout-lock.json').write_text('{}', encoding='utf-8')
            before = {p: p.read_bytes() for p in (base/'batch').rglob('*') if p.is_file()}
            with patch.object(rescore.holdout, 'verify', return_value={'reference_status': 'owner-verified'}) as verify:
                rescore.rescore(base/'batch', {'mapped': reference}, base/'out')
            verify.assert_called_once_with(reference, 'pkg')
            self.assertEqual(json.loads((base/'out/mapped/run-1/expected.json').read_text())['new'], True)
            self.assertEqual(json.loads((base/'out/unmapped/run-1/expected.json').read_text())['old'], True)
            self.assertEqual({p: p.read_bytes() for p in (base/'batch').rglob('*') if p.is_file()}, before)
            record = json.loads((base/'out/rescore-record.json').read_text())
            self.assertEqual([r['reference_version'] for r in record['runs']], ['mapped-v2', 'original'])
            with self.assertRaisesRegex(ValueError, 'never overwrite'):
                rescore.rescore(base/'batch', {}, base/'out')


if __name__ == '__main__':
    unittest.main()
