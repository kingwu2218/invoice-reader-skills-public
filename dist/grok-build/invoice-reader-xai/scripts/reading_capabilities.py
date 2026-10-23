# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Probe this execution environment without installing or downloading anything."""
import argparse
from contextlib import closing
import importlib
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def command(args, timeout=15):
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=timeout, shell=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or f'Exit {result.returncode}')[:1500])
    # Preserve trailing tabs/spaces: TSV may end with a valid empty text cell.
    return result.stdout.rstrip('\r\n')


def package(name, distribution=None):
    try:
        importlib.import_module(name)
        return {'status': 'usable', 'version': importlib.metadata.version(distribution or name)}
    except ModuleNotFoundError as error:
        return {'status': 'unavailable' if error.name == name else 'failed', 'reason': str(error)}
    except Exception as error:
        return {'status': 'failed', 'reason': str(error)}


def languages(value):
    if not re.fullmatch(r'[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*', value):
        raise ValueError('Languages must be Tesseract codes joined by +, for example eng+chi_tra.')
    return value.split('+')


def probe_tesseract(executable=None, language='eng'):
    required = languages(language)
    resolved = shutil.which(str(executable or 'tesseract'))
    if not resolved:
        return {'status': 'unavailable', 'reason': 'Not found at the configured path or on PATH; installation elsewhere is unknown.'}
    info = {'path': str(Path(resolved).resolve()), 'required_languages': required}
    try:
        info['version'] = command([resolved, '--version']).splitlines()[0]
        lines = command([resolved, '--list-langs']).splitlines()
        info['languages'] = [line.strip() for line in lines if re.fullmatch(r'[A-Za-z0-9_/]+', line.strip())]
        missing = sorted(set(required) - set(info['languages']))
        if missing:
            return dict(info, status='unavailable', reason='Missing language data: ' + ', '.join(missing))
        from PIL import Image, ImageDraw, ImageFont
        with tempfile.TemporaryDirectory(prefix='invoice-ocr-probe-') as directory:
            path = Path(directory) / 'smoke.png'
            picture = Image.new('RGB', (500, 110), 'white')
            ImageDraw.Draw(picture).text((20, 20), '12345', fill='black', font=ImageFont.load_default(size=54))
            picture.save(path)
            text = command([resolved, str(path), 'stdout', '-l', language, '--psm', '7'], timeout=20)
            if ''.join(text.split()) != '12345':
                return dict(info, status='failed', reason='Synthetic digit smoke test did not match.', smoke_output=text[:200])
        return dict(info, status='usable', smoke_test='passed; does not establish document accuracy')
    except ModuleNotFoundError:
        return dict(info, status='unknown', reason='Pillow is unavailable; OCR smoke test could not run.')
    except Exception as error:
        return dict(info, status='failed', reason=str(error)[:1500])


def probe(executable=None, language='eng', vision='unknown', check_ocr=True):
    if vision not in ('available', 'unavailable', 'unknown'):
        raise ValueError('Invalid vision capability')
    libraries = {name: package(name, dist) for name, dist in
                 [('pypdfium2', None), ('PIL', 'Pillow'), ('openpyxl', None)]}
    rendering = {'status': 'unavailable', 'reason': 'PDFium or Pillow not usable.'}
    if all(libraries[name]['status'] == 'usable' for name in ('pypdfium2', 'PIL')):
        try:
            import pypdfium2 as pdfium
            # PDFium 4.x exposes close(), but no context-manager protocol.
            with closing(pdfium.PdfDocument.new()) as pdf:
                with closing(pdf.new_page(72, 72)) as page:
                    with closing(page.render(scale=1)) as bitmap:
                        with closing(bitmap.to_pil()) as image:
                            image.load()
            rendering = {'status': 'usable', 'smoke_test': 'rendered a synthetic blank page'}
        except Exception as error:
            rendering = {'status': 'failed', 'reason': str(error)}
    return {'schema_version': 1, 'scope': 'current execution environment, not necessarily the user computer',
            'python': {'status': 'usable', 'path': sys.executable, 'version': sys.version.split()[0]},
            'libraries': libraries, 'pdf_rendering': rendering,
            'vision': {'status': vision, 'source': 'caller-supplied tool capability; not detected by Python'},
            'tesseract': probe_tesseract(executable, language) if check_ocr else {'status': 'disabled', 'reason': 'OCR disabled for this run.'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tesseract', help='Explicit executable path; otherwise search PATH.')
    parser.add_argument('--languages', default='eng')
    parser.add_argument('--vision', choices=['available', 'unavailable', 'unknown'], default='unknown')
    parser.add_argument('--ocr', choices=['auto', 'off'], default='auto')
    args = parser.parse_args()
    try:
        print(json.dumps(probe(args.tesseract, args.languages, args.vision, check_ocr=args.ocr != 'off'), indent=2))
    except ValueError as error:
        parser.exit(2, f'Problem: {error}\n')


if __name__ == '__main__':
    main()
