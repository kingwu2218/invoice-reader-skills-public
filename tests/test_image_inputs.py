"""Verify image-input provenance without mistaking preparation or self-report for reading."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'eval/runner'))
import image_inputs
import score

spec = importlib.util.spec_from_file_location('codex_adapter', ROOT/'adapters/codex/eval_adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class ImageInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.work, self.run = root/'work', root/'batch/case/run-1'
        self.work.mkdir(); self.run.mkdir(parents=True)
        (self.work/'eval-page-images').mkdir(); (self.run/'page-images').mkdir()
        # Controlled bytes test receipt integrity; the separate renderer test uses real PDF pages.
        pages = []
        for n in (1, 2):
            name = f'page-{n:04}.png'
            a, b = self.work/'eval-page-images'/name, self.run/'page-images'/name
            a.write_bytes(f'test image {n}'.encode()); shutil.copyfile(a, b)
            pages.append({'page': n, 'workspace_path': 'eval-page-images/'+name,
                          'archive_path': 'page-images/'+name, 'sha256': image_inputs.digest(a)})
        self.receipt = {'schema_version': 1, 'source': 'test.pdf', 'source_sha256': 'test-source',
                        'page_count': 2, 'pages': pages}
        self.meta = {'workspace': str(self.work), 'image_input_mode': 'cli-attachments',
                     'prepared_only': False, 'image_inputs_unchanged': True, 'exit_code': 0,
                     'completed': True, 'valid': False}
        self.meta['image_inputs_hash'] = image_inputs.save(self.run/'image-inputs.json', self.receipt)
        self.command = adapter.command('codex', 'requested-example', 'read',
                                       [self.work/p['workspace_path'] for p in pages])
        self.meta['invocation_hash'] = image_inputs.save(self.run/'invocation.json',
                                                       {'argv': self.command, 'cwd': str(self.work)})

    def test_inputs_are_auditable_but_attention_is_not_claimed(self):
        result = image_inputs.audit(self.run, self.meta)
        self.assertEqual((result['status'], result['numerator'], result['denominator']), ('supplied_to_cli', 2, 2))
        self.assertFalse(result['attention_verified'])
        meta = {**self.meta, 'prepared_only': True}
        self.assertEqual(image_inputs.audit(self.run, meta)['status'], 'prepared_only')
        self.assertIsNone(image_inputs.audit(self.run, meta)['numerator'])
        self.assertEqual(image_inputs.audit(self.run, {})['status'], 'not_captured')

    def test_missing_changed_and_unpassed_images_are_not_success(self):
        for changed in ({'completed': False}, {'exit_code': 1}, {'image_inputs_unchanged': False}):
            self.assertEqual(image_inputs.audit(self.run, {**self.meta, **changed})['status'], 'unavailable')
        path = self.run/self.receipt['pages'][0]['archive_path']
        path.write_bytes(b'changed')
        self.assertEqual(image_inputs.audit(self.run, self.meta)['status'], 'unavailable')
        path.unlink()
        self.assertEqual(image_inputs.audit(self.run, self.meta)['status'], 'unavailable')

    def test_receipt_tampering_and_duplicate_pages_fail(self):
        receipt = copy.deepcopy(self.receipt); receipt['pages'][1]['page'] = 1
        image_inputs.save(self.run/'image-inputs.json', receipt)
        self.assertEqual(image_inputs.audit(self.run, self.meta)['status'], 'unavailable')
        self.meta['image_inputs_hash'] = image_inputs.digest(self.run/'image-inputs.json')
        self.assertEqual(image_inputs.audit(self.run, self.meta)['status'], 'unavailable')

    def test_agent_checked_ledger_cannot_replace_cli_arguments(self):
        (self.run/'reading-review.json').write_text('{"visual_status":"checked"}')
        self.meta['invocation_hash'] = image_inputs.save(self.run/'invocation.json', {
            'argv': adapter.command('codex', 'requested-example', 'read'), 'cwd': str(self.work)})
        self.assertEqual(image_inputs.audit(self.run, self.meta)['status'], 'unavailable')
        (self.run/'meta.json').write_text(json.dumps(self.meta))
        result = score.score_batch(self.run.parents[1])['runs'][0]
        self.assertEqual(result['image_input_audit']['status'], 'unavailable')

    def test_real_render_preserves_pdf_and_inventories_all_pages(self):
        work, run = self.work/'real', self.run/'real'
        work.mkdir(); run.mkdir()
        source = work/'format-pack.pdf'
        shutil.copyfile(ROOT/'eval/fixtures/format-pack.pdf', source)
        original = source.read_bytes()
        images, digest = image_inputs.prepare(source, work, run)
        self.assertEqual(len(images), 2)
        self.assertEqual(digest, image_inputs.digest(run/'image-inputs.json'))
        self.assertEqual(source.read_bytes(), original)
        from PIL import Image
        for path in images:
            with Image.open(path) as image:
                self.assertGreater(image.width, 1000)
                image.verify()
        with self.assertRaises(ValueError):
            image_inputs.prepare(source, work, run)
