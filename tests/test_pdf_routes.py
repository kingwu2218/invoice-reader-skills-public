import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'core/scripts'))
import pdf_routes
import reading_capabilities as capabilities

HAS_PDF = importlib.util.find_spec('pypdfium2') is not None


class Capabilities(unittest.TestCase):
    def test_missing_command_is_not_proof_of_no_installation(self):
        with patch('reading_capabilities.shutil.which', return_value=None):
            info = capabilities.probe_tesseract()
        self.assertEqual(info['status'], 'unavailable')
        self.assertIn('elsewhere is unknown', info['reason'])

    def test_missing_language_does_not_run_ocr(self):
        with patch('reading_capabilities.shutil.which', return_value='engine'), patch(
                'reading_capabilities.command', side_effect=['tesseract 5', 'List of available languages (1):\neng']) as run:
            info = capabilities.probe_tesseract(language='eng+chi_tra')
        self.assertEqual(info['status'], 'unavailable')
        self.assertEqual(run.call_count, 2)

    def test_smoke_failure_and_timeout_not_usable(self):
        with patch('reading_capabilities.shutil.which', return_value='engine'), patch(
                'reading_capabilities.command', side_effect=['tesseract 5', 'eng', '1234S']):
            self.assertEqual(capabilities.probe_tesseract()['status'], 'failed')
        with patch('reading_capabilities.shutil.which', return_value='engine'), patch(
                'reading_capabilities.command', side_effect=subprocess.TimeoutExpired('engine', 15)):
            self.assertEqual(capabilities.probe_tesseract()['status'], 'failed')

    def test_successful_smoke_and_explicit_path(self):
        with patch('reading_capabilities.shutil.which', return_value='engine') as find, patch(
                'reading_capabilities.command', side_effect=['tesseract 5', 'eng', '12345']):
            info = capabilities.probe_tesseract('/configured/engine')
        self.assertEqual(info['status'], 'usable')
        find.assert_called_once_with('/configured/engine')

    def test_invalid_languages_not_passed_to_engine(self):
        with self.assertRaises(ValueError):
            capabilities.probe_tesseract(language='eng --other-option')

    def test_ocr_tsv_retains_positions_and_confidence_without_verification(self):
        data = 'text\tleft\ttop\twidth\theight\tconf\tblock_num\tpar_num\tline_num\tword_num\n6,200\t1\t2\t3\t4\t95\t1\t1\t1\t1\n'
        with patch('pdf_routes.command', return_value=data):
            result = pdf_routes.ocr_image(Path('image.png'), 'engine', 'eng')
        self.assertEqual(result['words'][0]['text'], '6,200')
        self.assertFalse(result['verified'])

    def test_mixed_small_image_requires_region_reading(self):
        route, reason = pdf_routes.classify('Invoice 123', [[0, 0, 10, 10]], 0, 10000)
        self.assertEqual(route, 'A')
        self.assertIn('image regions', reason)
        self.assertEqual(pdf_routes.classify('', [], 0, 10000)[0], 'B')
        self.assertEqual(pdf_routes.classify('\ufffd'*10+'Invoice', [], 0, 10000)[0], 'B')

    def test_command_preserves_final_empty_tsv_cell(self):
        data = 'left\ttop\twidth\theight\tconf\tblock_num\tpar_num\tline_num\tword_num\ttext\n1\t2\t3\t4\t95\t1\t1\t1\t1\t\n'
        completed = subprocess.CompletedProcess(['engine'], 0, stdout=data, stderr='')
        with patch('reading_capabilities.subprocess.run', return_value=completed):
            result = pdf_routes.ocr_image(Path('image.png'), 'engine', 'eng')
        self.assertEqual(result['status'], 'empty')
        self.assertEqual(result['words'], [])

    def test_malformed_ocr_tsv_has_explicit_fallback_error(self):
        with patch('pdf_routes.command', return_value='text\tleft\n123'):
            with self.assertRaisesRegex(ValueError, 'source-image fallback'):
                pdf_routes.ocr_image(Path('image.png'), 'engine', 'eng')


@unittest.skipUnless(HAS_PDF, 'PDF routing tests require the declared pypdfium2 dependency')
class PdfRoutes(unittest.TestCase):
    def test_native_scan_ocr_and_mixed_dispatch_all_pages(self):
        for name, expected in [('pack', ['A', 'A']), ('scan', ['B', 'B']), ('ocr', ['C', 'C']), ('mixed', ['A', 'B'])]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                result = pdf_routes.prepare([ROOT/f'eval/fixtures/coal-{name}.pdf'], Path(directory)/'evidence',
                                            vision='available', mode='off', dpi=72)
                item = result['inputs'][0]
                self.assertEqual(item['status'], 'prepared')
                self.assertEqual([p['route'] for p in item['pages']], expected)
                self.assertEqual([p['page'] for p in item['pages']], [1, 2])
                self.assertTrue(all(p['visual_verification'] == 'pending' for p in item['pages']))
                for page in item['pages']:
                    self.assertTrue((Path(directory)/'evidence'/page['image']).exists())
                if name == 'ocr':
                    self.assertIn('8,200', item['pages'][1]['text'])
                    self.assertGreater(item['pages'][1]['hidden_text_objects'], 0)

    def test_missing_ocr_falls_back_to_vision(self):
        with tempfile.TemporaryDirectory() as directory, patch('reading_capabilities.shutil.which', return_value=None):
            result = pdf_routes.prepare([ROOT/'eval/fixtures/coal-scan.pdf'], Path(directory)/'evidence', vision='available', dpi=72)
        page = result['inputs'][0]['pages'][0]
        self.assertEqual(page['ocr']['status'], 'unavailable')
        self.assertEqual(page['reading_methods'], ['vision_pending'])
        self.assertEqual(page['status'], 'prepared')

    def test_ocr_failure_preserves_image_and_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch('reading_capabilities.probe_tesseract',
                return_value={'status': 'usable', 'path': 'engine'}), patch('pdf_routes.ocr_image', side_effect=RuntimeError('timeout')):
            result = pdf_routes.prepare([ROOT/'eval/fixtures/coal-scan.pdf'], Path(directory)/'evidence', vision='available', dpi=72)
            self.assertTrue((Path(directory)/'evidence'/result['inputs'][0]['pages'][0]['image']).exists())
        self.assertEqual(result['inputs'][0]['pages'][0]['ocr']['status'], 'failed')
        self.assertEqual(result['inputs'][0]['status'], 'prepared')

    def test_no_vision_no_ocr_does_not_claim_image_read(self):
        with tempfile.TemporaryDirectory() as directory:
            result = pdf_routes.prepare([ROOT/'eval/fixtures/coal-scan.pdf'], Path(directory)/'evidence',
                                        vision='unavailable', mode='off', dpi=72)
        self.assertEqual(result['inputs'][0]['status'], 'partial')
        self.assertTrue(all(p['status'] == 'unprocessed' for p in result['inputs'][0]['pages']))

    def test_corrupt_file_does_not_hide_good_file_and_no_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            broken = root/'broken.pdf'
            broken.write_bytes(b'not a pdf')
            result = pdf_routes.prepare([broken, ROOT/'eval/fixtures/coal-pack.pdf'], root/'evidence',
                                        vision='available', mode='off', dpi=72)
            self.assertEqual([x['status'] for x in result['inputs']], ['unprocessed', 'prepared'])
            saved = (root/'evidence/routes.json').read_bytes()
            with self.assertRaises(FileExistsError):
                pdf_routes.prepare([broken], root/'evidence', mode='off')
            self.assertEqual(saved, (root/'evidence/routes.json').read_bytes())

    def test_off_never_probes_ocr_and_c_not_automatically_reocred(self):
        with tempfile.TemporaryDirectory() as directory, patch('reading_capabilities.probe_tesseract') as engine:
            pdf_routes.prepare([ROOT/'eval/fixtures/coal-scan.pdf'], Path(directory)/'off', mode='off', dpi=72)
            engine.assert_not_called()
        with tempfile.TemporaryDirectory() as directory, patch('reading_capabilities.probe_tesseract',
                return_value={'status': 'usable', 'path': 'engine'}), patch('pdf_routes.ocr_image', return_value={'status': 'empty'}) as read:
            pdf_routes.prepare([ROOT/'eval/fixtures/coal-ocr.pdf'], Path(directory)/'auto', vision='available', dpi=72)
            read.assert_not_called()
            pdf_routes.prepare([ROOT/'eval/fixtures/coal-ocr.pdf'], Path(directory)/'retry', vision='available', dpi=72, ocr_pages=(2,))
            self.assertEqual(read.call_count, 1)

    def test_fixture_answers_follow_visible_values_and_two_purposes(self):
        for variant in ('scan', 'ocr', 'mixed'):
            energy = json.loads((ROOT/f'eval/scenarios/coal-{variant}-energy/expected.json').read_text())
            payment = json.loads((ROOT/f'eval/scenarios/coal-{variant}-payment/expected.json').read_text())
            self.assertNotEqual(energy['tables']['Requested values'], payment['tables']['Requested values'])
            self.assertIn('6,200', json.dumps(energy))
            self.assertNotIn('8,200', json.dumps(energy))
            self.assertEqual(energy['tables']['Billing documents']['rows'][0]['Total'], '105.00')

    def test_locked_pdf_remains_unprocessed_and_other_inputs_continue(self):
        from reportlab.lib.pdfencrypt import StandardEncryption
        from reportlab.pdfgen import canvas
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            locked = root/'locked.pdf'
            document = canvas.Canvas(str(locked), encrypt=StandardEncryption('test-password'))
            document.drawString(20, 100, 'Locked fixture')
            document.save()
            result = pdf_routes.prepare([locked, ROOT/'eval/fixtures/coal-pack.pdf'], root/'evidence',
                                        vision='available', mode='off', dpi=72)
        self.assertEqual([x['status'] for x in result['inputs']], ['unprocessed', 'prepared'])
        self.assertTrue(result['inputs'][0]['errors'])

    def test_failed_page_stays_visible_and_later_pages_continue(self):
        import pypdfium2 as pdfium
        original = pdfium.PdfPage.render
        calls = []
        def fail_one(page, *args, **kwargs):
            calls.append(page.get_size())
            # Probe renders a 72-point synthetic page; fail only the first document page.
            if len(calls) == 2:
                raise RuntimeError('Synthetic page failure')
            return original(page, *args, **kwargs)
        with tempfile.TemporaryDirectory() as directory, patch.object(pdfium.PdfPage, 'render', fail_one):
            result = pdf_routes.prepare([ROOT/'eval/fixtures/coal-pack.pdf'], Path(directory)/'evidence',
                                        vision='available', mode='off', dpi=72)
        self.assertEqual([p['status'] for p in result['inputs'][0]['pages']], ['unprocessed', 'prepared'])
        self.assertEqual(result['inputs'][0]['status'], 'partial')

    def test_rotation_crop_and_no_overwrite_in_recovery_cli(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            args = [sys.executable, str(ROOT/'core/scripts/render_pages.py'), str(ROOT/'eval/fixtures/coal-pack.pdf'),
                    '--out', directory, '--pages', '2', '--rotation', '90', '--dpi', '72', '--crop', '10,20,30,40']
            run = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            target = Path(directory)/'page-0002.png'
            with Image.open(target) as image:
                self.assertGreater(image.width, image.height)
            before = target.read_bytes()
            retry = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(retry.returncode, 0)
            self.assertEqual(before, target.read_bytes())


if __name__ == '__main__':
    unittest.main()
