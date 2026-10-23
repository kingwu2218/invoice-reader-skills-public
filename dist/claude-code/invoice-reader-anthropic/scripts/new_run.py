# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Create a fresh run and input manifest. Usage: uv run new_run.py FILE [FILE ...]"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def create(files, root):
    inputs, seen = [], set()
    for file in files:
        path = Path(file).resolve()
        if not path.is_file():
            raise ValueError(f'Input file not found: {file}')
        if path in seen:
            raise ValueError(f'Duplicate input: {file}')
        seen.add(path)
        try:
            name = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            name = path.as_posix()
        inputs.append({'file': name, 'extraction': None, 'reason': 'Not processed yet'})
    folder = root / 'invoice-reader-work' / (datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8])
    folder.mkdir(parents=True)
    manifest = folder / 'manifest.json'
    manifest.write_text(json.dumps({'version': 1, 'inputs': inputs}, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    try:
        print(create(args.files, Path.cwd()))
    except (OSError, ValueError) as error:
        parser.exit(2, f'Problem: {error}\n')
