"""Verify generated packages, local links, invocation metadata and README drift."""
import filecmp
import re
import subprocess
import tempfile
from pathlib import Path

import skillsets

PRIVATE_PATH = re.compile(r'[A-Za-z]:\\Users\\[^\\\s]+|/Users/[^/\s]+/|/home/[a-z][^/\s]*/')


def differences(expected, actual, prefix=''):
    comparison = filecmp.dircmp(expected, actual, ignore=['__pycache__'])
    _, changed, errors = filecmp.cmpfiles(expected, actual, comparison.common_files, shallow=False)
    problems = [f'missing {prefix}{name}' for name in comparison.left_only]
    problems += [f'unexpected {prefix}{name}' for name in comparison.right_only]
    problems += [f'changed {prefix}{name}' for name in changed + errors]
    for sub in comparison.common_dirs:
        problems += differences(expected / sub, actual / sub, f'{prefix}{sub}/')
    return problems


def check_sets(packages, problems):
    expected = {skillsets.package_path(entry) for entry in packages}
    for entry in packages:
        folder = skillsets.package_path(entry)
        if not folder.exists():
            problems.append(f'{folder.name}: missing; run tools/build.py')
            continue
        with tempfile.TemporaryDirectory() as scratch:
            built = Path(scratch) / folder.name
            skillsets.render_set(entry, built)
            problems.extend(f'{folder.name}: {d}' for d in differences(built, folder))
        for path in folder.rglob('*.md'):
            text = path.read_text(encoding='utf-8')
            for link in re.findall(r'\]\(([^)]+)\)', text):
                if '://' not in link and not link.startswith('#') and not (path.parent / link.split('#')[0]).exists():
                    problems.append(f'{path.name}: missing reference {link}')
        text = (folder / 'SKILL.md').read_text(encoding='utf-8')
        front = text.split('---', 2)[1]
        if f'name: {folder.name}\n' not in front or re.search(r'^model:', front, re.MULTILINE):
            problems.append(f'{folder.name}: invalid name or forbidden model override')
    for folder in skillsets.DIST.glob('*/*'):
        if folder.is_dir() and folder not in expected:
            problems.append(f'{folder}: not registered')


def main():
    problems = []
    packages = skillsets.load_registry()
    check_sets(packages, problems)
    if skillsets.README.read_text(encoding='utf-8') != skillsets.readme_with_table(packages):
        problems.append('README table differs from registry')
    paths = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard'], cwd=skillsets.ROOT,
                           capture_output=True, text=True, check=True).stdout.splitlines()
    for name in set(paths):
        path = skillsets.ROOT / name
        if name == 'tools/check.py' or path.suffix not in ('.md', '.py', '.toml', '.json', '.yaml') or not path.is_file():
            continue
        if PRIVATE_PATH.search(path.read_text(encoding='utf-8', errors='ignore')):
            problems.append(f'{name}: absolute workstation path')
    for problem in problems:
        print(f'FAIL {problem}')
    print('check passed' if not problems else f'{len(problems)} problems')
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
