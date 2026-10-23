# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=5.13,<6", "Pillow>=10.1"]
# ///
"""Render PDF pages for the agent's image-viewing tool, never OCR or infer values."""
import argparse
from contextlib import closing
import math
from pathlib import Path
import pypdfium2 as pdfium


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf')
    parser.add_argument('--out', required=True)
    parser.add_argument('--pages', help='One-based comma-separated page numbers; default: all pages.')
    parser.add_argument('--dpi', type=int, default=200)
    parser.add_argument('--rotation', type=int, choices=[0, 90, 180, 270], default=0)
    parser.add_argument('--crop', default='0,0,0,0', help='PDF points removed from left,bottom,right,top after rotation.')
    args = parser.parse_args()
    crop = tuple(float(n) for n in args.crop.split(','))
    if len(crop) != 4 or any(not math.isfinite(n) or n < 0 for n in crop) or not 72 <= args.dpi <= 600:
        parser.error('Use four nonnegative crop amounts and DPI between 72 and 600.')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with closing(pdfium.PdfDocument(args.pdf)) as pdf:
        pdf.init_forms()
        pages = [int(n) - 1 for n in args.pages.split(',')] if args.pages else range(len(pdf))
        for index in pages:
            if index < 0 or index >= len(pdf):
                raise ValueError('Page number outside the PDF')
            page = pdf[index]
            try:
                width, height = page.get_size()
                if args.rotation in (90, 270):
                    width, height = height, width
                width, height = width-crop[0]-crop[2], height-crop[1]-crop[3]
                if width <= 0 or height <= 0:
                    raise ValueError('Crop removes the whole page')
                target = out / f'page-{index+1:04}.png'
                if target.exists():
                    raise ValueError('Use a new output directory; do not overwrite earlier page evidence.')
                scale = min(args.dpi/72, math.sqrt(40_000_000/(width*height)))
                bitmap = page.render(scale=scale, rotation=args.rotation, crop=crop)
                try:
                    bitmap.to_pil().save(target)
                    print(target)
                finally:
                    bitmap.close()
            finally:
                page.close()
        print(f'Total PDF pages: {len(pdf)}')


if __name__ == '__main__':
    main()
