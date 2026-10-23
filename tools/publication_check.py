"""Fail-closed publication review; never print matched private values.

Run from the repository root. This detects patterns, not every possible secret.
Binary visual reviews are bound to exact artifact bytes in a review manifest.
"""
import argparse
import hashlib
import html
import io
import json
import logging
import re
import subprocess
import tarfile
import urllib.parse
import zipfile
from pathlib import Path

POLICY = 'publication-review.json'
LOCAL_ONLY = {'AGENTS.override.md', 'hook.md'}
PATTERNS = {
    'windows_path': re.compile(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s<>"\x27`|{}\[\]()]*'),
    'unc_path': re.compile(r'(?<![\\\w])\\\\[A-Za-z0-9._-]+[\\/][^\s<>"\x27`|{}\[\]()]+'),
    'file_url': re.compile(r'file:/+[^\s<>"\x27`|{}\[\]()]+', re.I),
    'posix_path': re.compile(r'(?<![\w:/])/(?:[A-Za-z._~-][\w.~-]*/)+[\w.~-]*'),
    'uuid': re.compile(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b', re.I),
    'generated_run_id': re.compile(r'\b(?:conversation-)?20\d{6}[-_]\d{6}[-_][0-9a-f]{6,}\b', re.I),
    'named_private_id': re.compile(r'\b(?:session|chat|thread|manifest|run)[_-][0-9a-f]{12,}\b', re.I),
    'email': re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b'),
    'credential': re.compile(r'(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|AIza[0-9A-Za-z_-]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)'),
}


def variants(text):
    seen = {text}
    for _ in range(4):
        text = html.unescape(urllib.parse.unquote(text))
        text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), text)
        text = text.replace('\\/', '/').replace('\\\\', '\\')
        seen.add(text)
    return sorted(seen)


def hits(text):
    found = set()
    for number, line in enumerate(text.splitlines(), 1):
        for variant in variants(line):
            for category, pattern in PATTERNS.items():
                for match in pattern.finditer(variant):
                    found.add((number, category, match[0]))
    return sorted(found)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL)


def safe_name(name):
    # Filenames and archive members themselves can contain the disclosed value.
    if hits(name) or any(ord(c) < 32 for c in name):
        return '[redacted filename]'
    return name


class Review:
    def __init__(self, policy=None):
        policy = policy or {}
        self.exceptions = policy.get('synthetic_matches', [])
        self.binary_reviews = policy.get('binary_reviews', [])
        self.findings = []
        self.checked = 0
        self.budget = 128 * 1024 * 1024

    def add(self, name, location, category, line=None):
        finding = dict(file=safe_name(name), location=safe_name(location), category=category)
        if line is not None:
            finding['line'] = line
        if finding not in self.findings:
            self.findings.append(finding)

    def text(self, text, name, location='text'):
        for line, category, value in hits(text):
            if category == 'email' and location in ('commit_metadata', 'metadata'):
                source_line = text.splitlines()[line - 1]
                public_address = (value.endswith('@users.noreply.github.com')
                                  or value == 'noreply' + '@' + 'anthropic.com')
                identity = re.fullmatch(
                    r'(?:author|committer|tagger) [^<>\r\n]+ <([^<>]+)> \d+ [+-]\d{4}',
                    source_line)
                coauthor = re.fullmatch(r'Co-authored-by: [^<>\r\n]+ <([^<>]+)>',
                                       source_line, re.I)
                if public_address and any(match and match[1] == value
                                          for match in (identity, coauthor)):
                    # Public attribution is distinct from addresses in report
                    # text or arbitrary commit-message prose.
                    continue
            if name == POLICY and location == 'text' and any(
                    e.get('reason') and any(cat == category and matched == value
                                           for _, cat, matched in hits(json.dumps(e.get('value', ''))))
                    for e in self.exceptions):
                # Scan the manifest too; only its individually approved literals
                # may repeat here, never unrelated metadata or whole-file content.
                continue
            # Narrow reviewed synthetic matches only. No directory/file wildcards.
            if not any(e.get('file') == name and e.get('location', 'text') == location
                       and e.get('category') == category and e.get('value') == value
                       and e.get('reason') for e in self.exceptions):
                self.add(name, location, category, line)

    def reviewed_binary(self, data, name):
        return any(e.get('file') == name and e.get('sha256') == digest(data)
                   and e.get('reason') for e in self.binary_reviews)

    def scan(self, data, name, depth=0):
        self.checked += 1
        self.text(name, name, 'filename')
        if Path(name).name in LOCAL_ONLY:
            self.add(name, 'filename', 'local_maintainer_file')
        if depth > 5 or len(data) > self.budget:
            self.add(name, 'content', 'inspection_limit')
            return
        self.budget -= len(data)
        if data.startswith(b'%PDF'):
            self.pdf(data, name)
        elif zipfile.is_zipfile(io.BytesIO(data)):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    self.text(archive.comment.decode('utf-8', errors='strict'), name, 'zip_comment')
                    for member in archive.infolist():
                        child = name + '!' + member.filename
                        self.text(member.filename, child, 'filename')
                        self.text(member.comment.decode('utf-8', errors='strict'), child, 'zip_comment')
                        if member.is_dir():
                            continue
                        if member.file_size > self.budget:
                            self.add(child, 'content', 'inspection_limit')
                            continue
                        self.scan(archive.read(member), child, depth + 1)
            except Exception:
                self.add(name, 'content', 'archive_inspection_failed')
        elif data.startswith(b'\x1f\x8b') or data[257:262] == b'ustar':
            try:
                with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
                    for member in archive:
                        child = name + '!' + member.name
                        self.text(member.name, child, 'filename')
                        self.text(json.dumps(member.pax_headers) + '\n' + member.uname + '\n' + member.gname,
                                  child, 'tar_metadata')
                        if member.isfile() and member.size <= self.budget:
                            self.scan(archive.extractfile(member).read(), child, depth + 1)
                        elif not member.isdir():
                            self.add(child, 'content', 'archive_special_member_or_limit')
            except Exception:
                self.add(name, 'content', 'archive_inspection_failed')
        else:
            try:
                encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
                text = data.decode(encoding)
                if '\0' in text:
                    raise ValueError('binary')
                self.text(text, name)
            except (UnicodeError, ValueError):
                if not self.reviewed_binary(data, name):
                    self.add(name, 'content', 'binary_requires_manual_review')

    def pdf(self, data, name):
        # Exact-byte review includes rendered pages, metadata, annotations,
        # attachments and object streams. Changed PDFs always need a new review.
        if not self.reviewed_binary(data, name):
            self.add(name, 'content', 'pdf_requires_manual_review')
        logger = logging.getLogger('pypdf')
        saved_handlers, saved_propagate = logger.handlers, logger.propagate
        logger.handlers, logger.propagate = [logging.NullHandler()], False
        try:
            from pypdf import PdfReader
            pdf = PdfReader(io.BytesIO(data))
            if pdf.is_encrypted:
                self.add(name, 'content', 'encrypted_pdf')
                return
            self.text(str(dict(pdf.metadata or {})), name, 'pdf_metadata')
            if pdf.xmp_metadata:
                self.text(pdf.xmp_metadata.stream.get_data().decode('utf-8'), name, 'pdf_xmp')
            for number, page in enumerate(pdf.pages, 1):
                self.text(page.extract_text() or '', name, f'page-{number}')
                if page.get('/Annots'):
                    self.text(str(page['/Annots'].get_object()), name, f'page-{number}-annotations')
            for attachment, copies in pdf.attachments.items():
                for content in copies:
                    self.scan(content, name + '!' + attachment, 5)
        except Exception:
            self.add(name, 'content', 'pdf_inspection_failed')
        finally:
            logger.handlers, logger.propagate = saved_handlers, saved_propagate


def policy_from(data):
    value = json.loads(data)
    if value.get('version') != 1:
        raise ValueError('Unsupported review policy')
    return value


def index_entries(root):
    entries = []
    for record in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if record:
            meta, name = record.split(b'\t', 1)
            mode, oid, stage = meta.decode().split()
            if stage != '0':
                raise ValueError('Unmerged index')
            entries.append((name.decode('utf-8'), mode, oid))
    return entries


def tree_entries(root, commit):
    entries = []
    for record in git(root, 'ls-tree', '-r', '-z', commit).split(b'\0'):
        if record:
            meta, name = record.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            entries.append((name.decode('utf-8'), mode, oid))
    return entries


def scan_entries(review, root, entries, seen=None):
    seen = seen if seen is not None else set()
    for name, mode, oid in entries:
        if (name, oid) in seen:
            continue
        seen.add((name, oid))
        if mode != '100644' and mode != '100755':
            review.add(name, 'git', 'symlink_or_submodule_requires_review')
        else:
            review.scan(git(root, 'cat-file', 'blob', oid), name)


def run(args):
    root = Path(args.root).resolve()
    # Index checks use the INDEX policy, not uncommitted working-tree approvals.
    raw_policy = (git(root, 'show', ':' + POLICY) if args.mode == 'index'
                  else (root / POLICY).read_bytes())
    review = Review(policy_from(raw_policy))
    if args.mode == 'worktree':
        names = git(root, 'ls-files', '-co', '--exclude-standard', '-z').decode('utf-8').split('\0')
        for name in sorted(set(names) - {''}):
            path = root / name
            if path.is_symlink():
                review.add(name, 'content', 'symlink_requires_review')
            elif path.is_file():
                review.scan(path.read_bytes(), name)
            else:
                review.add(name, 'content', 'missing_worktree_file')
    elif args.mode == 'index':
        scan_entries(review, root, index_entries(root))
    elif args.mode == 'history':
        if not args.refs:
            raise ValueError('Explicit refs/range required')
        if any(ref.startswith('-') for ref in args.refs):
            raise ValueError('Options cannot be refs')
        commits = git(root, 'rev-list', *args.refs).decode().splitlines()
        seen = set()
        for ref in args.refs:
            review.text(ref, 'requested-ref', 'ref')
            if '..' not in ref:
                kind = git(root, 'cat-file', '-t', ref).strip()
                if kind == b'tag':
                    review.text(git(root, 'cat-file', 'tag', ref).decode('utf-8'), 'tag', 'metadata')
        for commit in commits:
            review.text(git(root, 'cat-file', 'commit', commit).decode('utf-8'), commit, 'commit_metadata')
            scan_entries(review, root, tree_entries(root, commit), seen)
    elif args.mode == 'artifact':
        if not args.artifacts:
            raise ValueError('Actual archive/notes paths required')
        for supplied in args.artifacts:
            path = Path(supplied)
            review.scan(path.read_bytes(), path.name)
    return review


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['worktree', 'index', 'history', 'artifact'])
    parser.add_argument('--root', default='.')
    parser.add_argument('--refs', nargs='+')
    parser.add_argument('--artifacts', nargs='+')
    parser.add_argument('--output', help='Optional masked JSON report, preferably in ignored local storage')
    args = parser.parse_args(argv)
    try:
        review = run(args)
        result = {'status': 'blocked' if review.findings else 'passed',
                  'mode': args.mode, 'items_checked': review.checked, 'findings': review.findings,
                  'limits': 'Pattern checks and exact-byte manual reviews do not certify every possible private value or external copy.'}
    except Exception as exc:
        result = {'status': 'blocked', 'mode': args.mode, 'error': type(exc).__name__,
                  'message': 'Inspection incomplete; no private error details printed.'}
    encoded = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(encoded + '\n', encoding='utf-8')
    print(encoded)
    return int(result['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
