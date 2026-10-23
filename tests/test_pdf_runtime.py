import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'core/scripts'))
import reading_capabilities


class PdfRuntime(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'core/scripts/pdf_runtime.py'), *args],
                              capture_output=True, text=True, encoding='utf-8')

    def test_probe_and_routes_share_runtime_and_render_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probe = self.run_cli('probe', '--vision', 'available', '--ocr', 'off')
            self.assertEqual(probe.returncode, 0, probe.stderr)
            capability = json.loads(probe.stdout)
            self.assertEqual(capability['pdf_rendering']['status'], 'usable')
            out = root/'routes'
            args = ('prepare', str(ROOT/'eval/fixtures/coal-ocr.pdf'), '--out', str(out),
                    '--vision', 'available', '--ocr', 'off', '--dpi', '72')
            prepared = self.run_cli(*args)
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            report = json.loads((out/'routes.json').read_text(encoding='utf-8'))
            self.assertEqual(report['capabilities']['python'], capability['python'])
            self.assertEqual(report['capabilities']['libraries'], capability['libraries'])
            self.assertEqual([p['route'] for p in report['inputs'][0]['pages']], ['C', 'C'])
            self.assertTrue(all((out/p['image']).is_file() for p in report['inputs'][0]['pages']))
            render = self.run_cli('render', str(ROOT/'eval/fixtures/coal-ocr.pdf'), '--out', str(root/'recovery'),
                                  '--pages', '2', '--rotation', '90', '--dpi', '72')
            self.assertEqual(render.returncode, 0, render.stderr)
            self.assertTrue((root/'recovery/page-0002.png').is_file())
            before = (out/'routes.json').read_bytes()
            self.assertEqual(self.run_cli(*args).returncode, 2)
            self.assertEqual((out/'routes.json').read_bytes(), before)

    def test_probe_closes_legacy_handles_even_if_render_fails(self):
        import pypdfium2
        for fail in (False, True):
            closed = []
            image = SimpleNamespace(load=lambda: None, close=lambda: closed.append('image'))
            bitmap = SimpleNamespace(to_pil=lambda: image, close=lambda: closed.append('bitmap'))
            def render(**kwargs):
                if fail: raise RuntimeError('synthetic renderer failure')
                return bitmap
            page = SimpleNamespace(render=render, close=lambda: closed.append('page'))
            document = SimpleNamespace(new_page=lambda *args: page, close=lambda: closed.append('document'))
            with patch.object(pypdfium2.PdfDocument, 'new', return_value=document):
                result = reading_capabilities.probe(check_ocr=False)
            self.assertEqual(result['pdf_rendering']['status'], 'failed' if fail else 'usable')
            self.assertEqual(closed, ['page', 'document'] if fail else ['image', 'bitmap', 'page', 'document'])

    def test_missing_dependencies_probe_does_not_install(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', '-S', str(ROOT/'core/scripts/pdf_runtime.py'),
                                 'probe', '--ocr', 'off'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        info = json.loads(result.stdout)
        self.assertEqual(info['pdf_rendering']['status'], 'unavailable')
        self.assertEqual(info['tesseract']['status'], 'disabled')

    def test_runtime_rejects_unrecognised_action(self):
        result = self.run_cli('../process.py')
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
