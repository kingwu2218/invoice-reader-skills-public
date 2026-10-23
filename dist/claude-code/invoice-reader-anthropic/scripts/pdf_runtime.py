# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=5.13,<6", "Pillow>=10.1"]
# ///
"""One dependency environment for PDF probing, preparation and recovery rendering.

Running through uv is explicit dependency setup, not installation-free discovery.
An existing interpreter can invoke this entry without installing anything.
"""
import argparse
from pathlib import Path
import runpy
import sys


SCRIPTS = {'probe': 'reading_capabilities.py', 'prepare': 'pdf_routes.py', 'render': 'render_pages.py'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=SCRIPTS)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    target = Path(__file__).resolve().with_name(SCRIPTS[args.action])
    original = sys.argv
    try:
        sys.argv = [str(target), *args.arguments]
        # No subprocess/interpreter selection: all actions use this runtime.
        runpy.run_path(str(target), run_name='__main__')
    finally:
        sys.argv = original


if __name__ == '__main__':
    main()
