"""Build PDF-format variants of the same synthetic invoice/certificate and fixed answers.

Requires reportlab, Pillow and pypdfium2. Existing answers are never overwritten.
"""
import json
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

REPO = Path(__file__).resolve().parents[2]


def create_variants(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    paths = {}
    with pdfium.PdfDocument(source) as pdf:
        for variant in ('scan', 'ocr', 'mixed'):
            target = destination / f'coal-{variant}.pdf'
            if target.exists():
                raise ValueError(f'Refusing to overwrite fixture: {target}')
            output = canvas.Canvas(str(target), invariant=1)
            for number in range(len(pdf)):
                page = pdf[number]
                width, height = page.get_size()
                output.setPageSize((width, height))
                textpage = page.get_textpage()
                try:
                    lines = textpage.get_text_bounded().splitlines()
                finally:
                    textpage.close()
                if variant == 'mixed' and number == 0:
                    # Same visible facts as the original, native text on page 1.
                    y = 785
                    for index, line in enumerate(lines):
                        if line.startswith('Page '):
                            output.setFont('Helvetica', 9)
                            output.drawString(42, 35, line)
                            continue
                        output.setFont('Helvetica-Bold' if index == 0 else 'Helvetica', 18 if index == 0 else 11)
                        output.drawString(42, y, line)
                        y -= 42 if index == 0 else 29
                else:
                    bitmap = page.render(scale=200/72)
                    try:
                        output.drawImage(ImageReader(bitmap.to_pil()), 0, 0, width=width, height=height)
                    finally:
                        bitmap.close()
                    if variant == 'ocr':
                        hidden = output.beginText(42, 785)
                        hidden.setFont('Helvetica', 11)
                        hidden.setLeading(29)
                        hidden.setTextRenderMode(3)
                        for line in lines:
                            # Intentionally incorrect hidden layer; image/answer stay unchanged.
                            hidden.textLine(line.replace('6,200', '8,200').replace('105.00', '100.00'))
                        output.drawText(hidden)
                output.showPage()
                page.close()
            output.save()
            paths[variant] = target
    return paths


def main():
    paths = create_variants(REPO/'eval/fixtures/coal-pack.pdf', REPO/'eval/fixtures')
    routes = {'scan': ['B', 'B'], 'ocr': ['C', 'C'], 'mixed': ['A', 'B']}
    for variant, source in paths.items():
        for purpose in ('payment', 'energy'):
            base = REPO/'eval/scenarios'/f'coal-{purpose}'
            folder = REPO/'eval/scenarios'/f'coal-{variant}-{purpose}'
            folder.mkdir(parents=True, exist_ok=True)
            (folder/'case.toml').write_text(
                f'source = "fixtures/{source.name}"\nmedium = "pdf-{variant}"\n'
                f'content_group = "coal-pack"\nexpected_routes = {json.dumps(routes[variant])}\n', encoding='utf-8')
            (folder/'custom.md').write_text((base/'custom.md').read_text(encoding='utf-8'), encoding='utf-8')
            expected = json.loads((base/'expected.json').read_text(encoding='utf-8'))
            for table in expected['tables'].values():
                for row in table['rows']:
                    if row.get('File') == 'coal-pack.pdf':
                        row['File'] = source.name
            path = folder/'expected.json'
            if path.exists():
                raise ValueError(f'Refusing to overwrite answer: {path}')
            path.write_text(json.dumps(expected, indent=2), encoding='utf-8')
    print('Created 3 format variants and 6 purpose-specific scenarios; no model evaluated.')


if __name__ == '__main__':
    main()
