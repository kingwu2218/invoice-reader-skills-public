"""Opt-in local Git guards. Does not alter hooks already installed by a user."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys

import publication_check as check


def guard(kind, root):
    script = str(root / 'tools' / 'publication_check.py')
    if kind == 'pre-commit':
        return subprocess.call([sys.executable, script, 'index', '--root', str(root)])
    refs = []
    review = check.Review()
    for line in sys.stdin:
        fields = line.split()
        if len(fields) != 4:
            print('Publication blocked: malformed push input.')
            return 1
        local_ref, oid, remote_ref, remote_oid = fields
        review.text(local_ref + '\n' + remote_ref, 'push-ref', 'ref')
        if set(oid) == {'0'}:
            continue
        if not all(c in '0123456789abcdef' for c in oid) or len(oid) not in (40, 64):
            print('Publication blocked: invalid object identifier.')
            return 1
        refs.append(oid)
    if review.findings:
        print('Publication blocked: private-looking ref name; value withheld.')
        return 1
    if not refs:
        return 0
    return subprocess.call([sys.executable, script, 'history', '--root', str(root), '--refs', *refs])


def install(root):
    configured = subprocess.run(['git', 'config', '--get', 'core.hooksPath'], cwd=root,
                                capture_output=True)
    if configured.returncode != 1:
        raise ValueError('An existing hooks directory configuration needs manual integration.')
    directory = Path(check.git(root, 'rev-parse', '--git-path', 'hooks').decode().strip())
    if not directory.is_absolute():
        directory = root / directory
    hooks = [directory / kind for kind in ('pre-commit', 'pre-push')]
    if any(path.exists() or path.is_symlink() for path in hooks):
        raise ValueError('Existing hooks are never overwritten; integrate manually.')
    interpreter = shlex.quote(Path(sys.executable).as_posix())
    directory.mkdir(parents=True, exist_ok=True)
    for hook in hooks:
        # Absolute interpreter is intentionally LOCAL ONLY, under Git metadata.
        hook.write_text('#!/bin/sh\nexec ' + interpreter +
                        ' tools/install_publication_hooks.py --guard ' + hook.name + '\n',
                        encoding='utf-8', newline='\n')
        hook.chmod(hook.stat().st_mode | 0o111)
    print('Installed local pre-commit and pre-push guards; no tracked files changed by installation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard', choices=['pre-commit', 'pre-push'])
    args = parser.parse_args()
    try:
        root = Path(check.git(Path.cwd(), 'rev-parse', '--show-toplevel').decode().strip())
        if args.guard:
            return guard(args.guard, root)
        install(root)
        return 0
    except Exception:
        print('Publication guard stopped: setup/inspection incomplete. Existing hooks were not replaced.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
