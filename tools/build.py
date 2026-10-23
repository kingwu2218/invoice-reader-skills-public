"""Build self-contained packages in dist/. Usage: python tools/build.py"""
import shutil
import tempfile
from pathlib import Path

import skillsets


def main():
    packages = skillsets.load_registry()
    for entry in packages:
        target = skillsets.package_path(entry)
        if not target.resolve().is_relative_to(skillsets.DIST.resolve()) or target.is_symlink():
            raise ValueError('Unsafe build destination')
        with tempfile.TemporaryDirectory() as scratch:
            built = Path(scratch) / entry['name']
            skillsets.render_set(entry, built)
            if target.exists():
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(built, target)
        print(f'built {target.relative_to(skillsets.ROOT).as_posix()}')
    skillsets.README.write_bytes(skillsets.readme_with_table(packages).encode('utf-8'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
