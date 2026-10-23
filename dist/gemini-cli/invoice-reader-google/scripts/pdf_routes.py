# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=5.13,<6", "Pillow>=10.1"]
# ///
"""Prepare per-page PDF evidence and optional local OCR; never certify extracted values."""
import argparse
from contextlib import closing
import csv
import hashlib
import io
import json
import math
from pathlib import Path

from reading_capabilities import command, languages, probe


def classify(text, images, hidden_text, page_area):
    """Conservative routing hints, not proof of a document's creation method."""
    meaningful = sum(char.isalnum() for char in text)
    corrupt = text.count('\ufffd') + text.count('\x00')
    usable = meaningful > 0 and corrupt / max(len(text), 1) < .01
    largest = max((max(0, r[2]-r[0]) * max(0, r[3]-r[1]) for r in images), default=0)
    if not usable:
        return 'B', 'No usable text layer; inspect image (including possible blank/vector-only pages).'
    if images and (hidden_text or largest / max(page_area, 1) >= .5):
        return 'C', 'Image plus hidden text or large image: OCR-like or mixed; verify against image.'
    if images:
        return 'A', 'Text plus image regions; inspect every image region via route B if relevant.'
    return 'A', 'Usable text candidate; check layout and field associations visually.'


def inspect_page(page):
    import pypdfium2 as pdfium
    textpage = page.get_textpage()
    try:
        text = textpage.get_text_bounded()
        # Rectangles are PDF coordinates, not a semantic table or reading-order guarantee.
        count = textpage.count_rects()
        spans = []
        for i in range(count):
            left, bottom, right, top = textpage.get_rect(i)
            spans.append({'box': [left, bottom, right, top],
                          'text': textpage.get_text_bounded(left=left, bottom=bottom, right=right, top=top)})
    finally:
        textpage.close()
    images, hidden, nested = [], 0, False
    for obj in page.get_objects():
        if obj.type == pdfium.raw.FPDF_PAGEOBJ_FORM:
            nested = True
        if obj.type == pdfium.raw.FPDF_PAGEOBJ_IMAGE:
            # 5.x renamed the axis-aligned object bounds accessor.
            bounds = obj.get_bounds if hasattr(obj, 'get_bounds') else obj.get_pos
            images.append(list(bounds()))
        elif obj.type == pdfium.raw.FPDF_PAGEOBJ_TEXT:
            hidden += pdfium.raw.FPDFTextObj_GetTextRenderMode(obj) in (3, 7)
    width, height = page.get_size()
    route, reason = classify(text, images, hidden, width * height)
    return {'route': route, 'route_basis': reason, 'classification': 'heuristic; visual confirmation required',
            'size_points': [width, height], 'text': text, 'text_spans': spans,
            'image_regions': images, 'hidden_text_objects': hidden,
            'coordinate_system': 'PDF object coordinates; nested form transforms may need visual interpretation',
            'nested_forms': nested, 'region_routes': ['B'] if images and route == 'A' else []}


def ocr_image(path, executable, language):
    raw = command([executable, str(path), 'stdout', '-l', language, 'tsv'], timeout=60)
    words = []
    for number, row in enumerate(csv.DictReader(io.StringIO(raw), delimiter='\t', quoting=csv.QUOTE_NONE), 2):
        required = ('text', 'left', 'top', 'width', 'height', 'conf',
                    'block_num', 'par_num', 'line_num', 'word_num')
        if any(row.get(key) is None for key in required) or None in row:
            raise ValueError(f'Malformed OCR TSV row {number}; use source-image fallback.')
        if row.get('text', '').strip():
            words.append({key: row[key] for key in required})
    return {'status': 'completed' if words else 'empty', 'words': words,
            'coordinate_system': 'rendered image pixels, top-left origin',
            'verified': False, 'note': 'OCR confidence is not calibrated field accuracy.'}


def prepare_file(source, folder, capabilities, mode='auto', language='eng', dpi=300, ocr_pages=()):
    import pypdfium2 as pdfium
    result = {'file': str(source), 'pages': [], 'status': 'prepared', 'errors': []}
    try:
        result['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        with closing(pdfium.PdfDocument(source)) as pdf:
            pdf.init_forms()
            result['page_count'] = len(pdf)
            if not len(pdf):
                raise ValueError('PDF has no pages')
            if any(p < 1 or p > len(pdf) for p in ocr_pages):
                raise ValueError('Requested OCR page outside PDF')
            for index in range(len(pdf)):
                record = {'page': index + 1, 'status': 'prepared', 'visual_verification': 'pending', 'errors': []}
                page = None
                try:
                    page = pdf[index]
                    try:
                        record.update(inspect_page(page))
                    except Exception as error:
                        record.update(route='B', route_basis='Text inspection failed; inspect rendered page.',
                                      classification='unknown', inspection_error=str(error))
                    width, height = page.get_size()
                    scale = min(dpi / 72, math.sqrt(40_000_000 / max(width * height, 1)))
                    bitmap = page.render(scale=scale)
                    target = folder / f'page-{index+1:04}.png'
                    try:
                        bitmap.to_pil().save(target)
                    finally:
                        bitmap.close()
                    record.update(image=target.name, rendered_dpi=round(scale * 72, 2))
                    # C uses the existing layer initially; only explicit selected pages get re-OCR.
                    wanted = mode == 'auto' and (record['route'] == 'B' or index + 1 in ocr_pages)
                    engine = capabilities['tesseract']
                    record['ocr'] = {'status': 'not_requested'}
                    if wanted and engine['status'] == 'usable':
                        try:
                            record['ocr'] = ocr_image(target, engine['path'], language)
                        except Exception as error:
                            record['ocr'] = {'status': 'failed', 'reason': str(error)}
                    elif wanted:
                        record['ocr'] = {'status': engine['status'], 'reason': engine.get('reason', 'OCR unavailable')}
                    methods = []
                    if record.get('text'):
                        methods.append('text_layer')
                    if record['ocr']['status'] == 'completed':
                        methods.append('local_ocr')
                    vision = capabilities['vision']['status']
                    if vision == 'available':
                        methods.append('vision_pending')
                    else:
                        record['visual_verification'] = 'unavailable' if vision == 'unavailable' else 'unknown'
                    record['reading_methods'] = methods
                    if vision != 'available' and record['route'] in ('B', 'C'):
                        record['status'] = 'needs_review' if methods else 'unprocessed'
                        record['errors'].append('Image reading/verification not established; OCR is candidate evidence only.')
                    elif vision != 'available':
                        record['status'] = 'needs_review'
                        record['errors'].append('Visual layout/region verification not established.')
                except Exception as error:
                    record.update(status='unprocessed', visual_verification='unavailable')
                    record['errors'].append(str(error))
                finally:
                    if page is not None:
                        page.close()
                result['pages'].append(record)
            if any(p['status'] != 'prepared' for p in result['pages']):
                result['status'] = 'partial'
    except Exception as error:
        result.update(status='unprocessed')
        result['errors'].append(str(error))
    return result


def prepare(files, out, *, tesseract=None, language='eng', vision='unknown', mode='auto', dpi=300, ocr_pages=()):
    languages(language)
    if not 72 <= dpi <= 600:
        raise ValueError('DPI must be between 72 and 600')
    if mode == 'off' and ocr_pages:
        raise ValueError('--ocr-pages requires --ocr auto')
    sources = [Path(p).resolve() for p in files]
    if not sources or len(set(sources)) != len(sources):
        raise ValueError('Supply at least one unique PDF path')
    out = Path(out).resolve()
    # Dedicated evidence folder: never overwrite earlier evidence or source documents.
    out.mkdir(parents=True, exist_ok=False)
    capabilities = probe(tesseract, language, vision, check_ocr=mode != 'off')
    report = {'schema_version': 1, 'stage': 'prepared evidence; not completed extraction',
              'capabilities': capabilities, 'inputs': []}
    for number, source in enumerate(sources, 1):
        folder = out / f'input-{number:04}'
        folder.mkdir()
        if capabilities['pdf_rendering']['status'] != 'usable':
            item = {'file': str(source), 'status': 'unprocessed', 'pages': [],
                    'errors': ['PDF renderer unavailable; use an adapter-native reader if available.']}
        else:
            item = prepare_file(source, folder, capabilities, mode, language, dpi, ocr_pages)
        for record in item['pages']:
            if 'image' in record:
                record['image'] = f'{folder.name}/{record["image"]}'
        report['inputs'].append(item)
        # Save progress after every input; a later file failure cannot hide earlier evidence.
        (out / 'routes.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdfs', nargs='+')
    parser.add_argument('--out', required=True, help='New evidence folder inside the fresh run.')
    parser.add_argument('--tesseract')
    parser.add_argument('--languages', default='eng')
    parser.add_argument('--vision', choices=['available', 'unavailable', 'unknown'], default='unknown')
    parser.add_argument('--ocr', choices=['auto', 'off'], default='auto')
    parser.add_argument('--ocr-pages', help='Explicit comma-separated physical pages to re-OCR, for one PDF only.')
    parser.add_argument('--dpi', type=int, default=300)
    args = parser.parse_args()
    try:
        pages = tuple(int(p) for p in args.ocr_pages.split(',')) if args.ocr_pages else ()
        if pages and len(args.pdfs) != 1:
            raise ValueError('--ocr-pages requires exactly one PDF')
        report = prepare(args.pdfs, args.out, tesseract=args.tesseract, language=args.languages,
                         vision=args.vision, mode=args.ocr, dpi=args.dpi, ocr_pages=pages)
        print(Path(args.out) / 'routes.json')
        return 3 if any(i['status'] != 'prepared' for i in report['inputs']) else 0
    except (OSError, ValueError) as error:
        parser.exit(2, f'Problem: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
