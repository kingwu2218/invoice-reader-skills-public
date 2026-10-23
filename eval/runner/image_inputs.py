"""Harness-owned page attachment receipts. These prove CLI inputs, not model attention."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_bytes((json.dumps(value, indent=2)+'\n').encode('utf-8'))
    return digest(path)


def prepare(source, work, run):
    import pypdfium2 as pdfium
    source = Path(source)
    with pdfium.PdfDocument(source) as pdf:
        count = len(pdf)
    # This opt-in mode is for small public eval cases, not unattended large uploads.
    if not 1 <= count <= 20:
        raise ValueError('Image-assisted eval supports 1-20 PDF pages per case.')
    folder = work/'eval-page-images'
    if folder.exists():
        raise ValueError('Use a fresh image evidence directory.')
    renderer = Path(__file__).resolve().parents[2]/'core/scripts/render_pages.py'
    subprocess.run([sys.executable, str(renderer), str(source), '--out', str(folder), '--dpi', '200'],
                   check=True, capture_output=True, text=True)
    archive = run/'page-images'
    archive.mkdir()
    pages = []
    for number in range(1, count+1):
        path = folder/f'page-{number:04}.png'
        shutil.copyfile(path, archive/path.name)
        pages.append({'page': number, 'workspace_path': path.relative_to(work).as_posix(),
                      'archive_path': 'page-images/'+path.name, 'sha256': digest(path)})
    receipt = {'schema_version': 1, 'source': source.name, 'source_sha256': digest(source),
               'page_count': count, 'dpi': 200, 'pages': pages,
               'evidence_scope': 'Files prepared for CLI image arguments; model attention is not established.'}
    receipt_hash = save(run/'image-inputs.json', receipt)
    return [work/p['workspace_path'] for p in pages], receipt_hash


def audit(run, meta):
    """Verify archived evidence and exact invocation; never accept model-written ledgers."""
    if meta.get('image_input_mode') != 'cli-attachments':
        return {'status': 'not_captured', 'numerator': None, 'denominator': None}
    try:
        for name, key in [('image-inputs.json', 'image_inputs_hash'), ('invocation.json', 'invocation_hash')]:
            if digest(run/name) != meta.get(key):
                raise ValueError(f'{name} missing hash or changed')
        receipt = json.loads((run/'image-inputs.json').read_text(encoding='utf-8'))
        invocation = json.loads((run/'invocation.json').read_text(encoding='utf-8'))
        pages, count = receipt['pages'], receipt['page_count']
        if receipt['schema_version'] != 1 or not isinstance(count, int) or not 1 <= count <= 20:
            raise ValueError('Invalid page inventory')
        if [p['page'] for p in pages] != list(range(1, count+1)):
            raise ValueError('Missing, duplicate or reordered pages')
        work = Path(meta['workspace'])
        arguments = invocation['argv']
        flags = arguments[:arguments.index('--')]
        supplied = [flags[i+1] for i, flag in enumerate(flags) if flag == '--image']
        expected = []
        for page in pages:
            # Fixed relative names prevent a changed receipt redirecting verification elsewhere.
            filename = f"page-{page['page']:04}.png"
            if page['archive_path'] != 'page-images/'+filename or page['workspace_path'] != 'eval-page-images/'+filename:
                raise ValueError('Invalid page path')
            if digest(run/page['archive_path']) != page['sha256']:
                raise ValueError('Archived page changed')
            expected.append(str(work/page['workspace_path']))
        if supplied != expected or invocation['cwd'] != str(work):
            raise ValueError('CLI image arguments do not match the page inventory')
        if meta.get('prepared_only'):
            return {'status': 'prepared_only', 'numerator': None, 'denominator': count}
        if not meta.get('image_inputs_unchanged') or meta.get('exit_code') != 0 or not meta.get('completed'):
            raise ValueError('Image integrity or CLI completion not established')
        return {'status': 'supplied_to_cli', 'numerator': count, 'denominator': count,
                'attention_verified': False}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        return {'status': 'unavailable', 'numerator': None, 'denominator': None, 'error': str(error)}
