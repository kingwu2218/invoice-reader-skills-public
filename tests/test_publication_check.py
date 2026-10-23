"""Synthetic publication failures; never use real machine/session identifiers."""
import argparse
import contextlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import publication_check as pc
import install_publication_hooks as hooks


class PublicationPatterns(unittest.TestCase):
    def test_public_noreply_identity_is_scoped_to_git_metadata(self):
        address = '12345+synthetic-user' + '@' + 'users.noreply.github.com'
        author = f'author Synthetic Contributor <{address}> 1234567890 +0000'
        coauthor = 'Co-authored-by: Synthetic Bot <' + 'noreply' + '@' + 'anthropic.com>'
        r = pc.Review()
        r.text(author + '\n' + coauthor, 'commit', 'commit_metadata')
        self.assertFalse(r.findings)
        r.text(author, 'report.md')
        r.text('Contact ' + address, 'commit', 'commit_metadata')
        r.text('author Synthetic Contributor <' + 'person' + '@' + 'synthetic.example> 1234567890 +0000',
               'private-commit', 'commit_metadata')
        self.assertEqual(len(r.findings), 3)

    def test_encoded_paths_all_text_formats_and_keys(self):
        value = 'Z:' + '/synthetic-fixture/private.txt'
        for name in ('report.csv', 'report.json', 'script.py', 'NOTICE'):
            for content in (value, value.replace('/', '\\'),
                            value.replace(':', '%3A').replace('/', '%2F'),
                            json.dumps({value: 42}), value.replace(':', r'\u003a')):
                with self.subTest(name=name, content=content):
                    r = pc.Review()
                    r.scan(content.encode(), name)
                    self.assertTrue(r.findings)
                    self.assertNotIn('private.txt', json.dumps(r.findings))

    def test_identifiers_credentials_and_email(self):
        for value in (str(uuid.uuid4()), 'conversation-' + '20990101-123456-' + 'abcdef12',
                      'session_' + 'a' * 16, 'ghp_' + 'q' * 32,
                      'fixture-person' + '@' + 'synthetic.example'):
            r = pc.Review()
            r.scan(value.encode(), 'result.txt')
            self.assertTrue(r.findings)
            self.assertNotIn(value, json.dumps(r.findings))

    def test_absolute_and_file_url_and_unc(self):
        for value in ('/' + 'synthetic-fixture/work/input.pdf',
                      'file:' + '///synthetic-fixture/input.pdf',
                      '\\' * 2 + 'synthetic-host\\share\\input.pdf'):
            r = pc.Review()
            r.scan(value.encode(), 'result.txt')
            self.assertTrue(r.findings)

    def test_filenames_are_masked_and_local_rules_blocked(self):
        value = str(uuid.uuid4())
        r = pc.Review()
        r.scan(b'ok', value + '.txt')
        r.scan(b'local', 'hook.md')
        self.assertNotIn(value, json.dumps(r.findings))
        self.assertIn('local_maintainer_file', {f['category'] for f in r.findings})

    def test_individual_exception_does_not_allow_other_values_or_files(self):
        value = 'Z:' + '/synthetic-fixture/python.exe'
        entry = dict(file='fixture.py', category='windows_path', value=value, reason='Synthetic mock')
        r = pc.Review({'synthetic_matches': [entry]})
        r.scan(value.encode(), 'fixture.py')
        self.assertFalse(r.findings)
        r.scan((value + '\n' + str(uuid.uuid4())).encode(), 'fixture.py')
        r.scan(value.encode(), 'report.csv')
        self.assertEqual({f['category'] for f in r.findings}, {'uuid', 'windows_path'})

    def test_utf16_is_scanned_unknown_binary_and_bad_pdf_block(self):
        r = pc.Review()
        r.scan(str(uuid.uuid4()).encode('utf-16'), 'extensionless')
        r.scan(b'\0opaque', 'unknown.bin')
        r.scan(b'%PDF broken', 'broken.pdf')
        self.assertTrue({'uuid', 'binary_requires_manual_review', 'pdf_inspection_failed'} <=
                        {f['category'] for f in r.findings})

    def test_binary_review_invalidated_by_changed_bytes(self):
        data = b'\0synthetic binary'
        policy = {'binary_reviews': [{'file': 'fixture.bin', 'sha256': pc.digest(data),
                                     'reason': 'Inspected synthetic fixture'}]}
        r = pc.Review(policy)
        r.scan(data, 'fixture.bin')
        self.assertFalse(r.findings)
        r.scan(data + b'x', 'fixture.bin')
        self.assertTrue(r.findings)

    def test_zip_comments_members_xlsx_hidden_parts_and_nested(self):
        inner = io.BytesIO()
        marker = str(uuid.uuid4()).encode()
        with zipfile.ZipFile(inner, 'w') as z:
            z.writestr('xl/comments/comment1.xml', marker)
            z.writestr('docProps/core.xml', marker)
            z.writestr('xl/worksheets/hidden.xml', marker)
            z.comment = marker
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, 'w') as z:
            z.writestr('fixture.xlsx', inner.getvalue())
        r = pc.Review()
        r.scan(outer.getvalue(), 'release.zip')
        self.assertEqual(len(r.findings), 4)
        self.assertNotIn(marker.decode(), json.dumps(r.findings))

    def test_tar_checks_content_and_owner_without_extraction(self):
        payload = io.BytesIO()
        marker = str(uuid.uuid4())
        with tarfile.open(fileobj=payload, mode='w:gz') as tar:
            item = tarfile.TarInfo('fixture.txt')
            item.uname = marker
            data = marker.encode()
            item.size = len(data)
            tar.addfile(item, io.BytesIO(data))
        r = pc.Review()
        r.scan(payload.getvalue(), 'source.tar.gz')
        self.assertEqual({f['location'] for f in r.findings}, {'tar_metadata', 'text'})

    def test_budget_and_archive_depth_fail_closed(self):
        r = pc.Review()
        r.budget = 2
        r.scan(b'long', 'fixture.txt')
        r.scan(b'', 'nested.zip', depth=6)
        self.assertEqual(len(r.findings), 2)


class GitPublicationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic Fixture')
        self.git('config', 'user.email', 'fixture@synthetic.example')
        self.policy = {'version': 1, 'synthetic_matches': [], 'binary_reviews': []}
        self.write(pc.POLICY, json.dumps(self.policy))
        self.git('add', pc.POLICY)

    def git(self, *args, input=None):
        return subprocess.check_output(['git', *args], cwd=self.root, input=input, stderr=subprocess.DEVNULL)

    def write(self, name, text):
        (self.root / name).write_text(text, encoding='utf-8')

    def run_check(self, mode, refs=None):
        return pc.run(argparse.Namespace(root=str(self.root), mode=mode, refs=refs, artifacts=None))

    def test_index_not_worktree_and_policy_not_worktree(self):
        marker = str(uuid.uuid4())
        self.write('report.csv', marker)
        self.git('add', 'report.csv')
        self.write('report.csv', 'chat-01')
        self.policy['synthetic_matches'].append(dict(file='report.csv', category='uuid',
                                                    value=marker, reason='unapproved unstaged exception'))
        self.write(pc.POLICY, json.dumps(self.policy))
        self.assertFalse(self.run_check('worktree').findings)
        self.assertTrue(self.run_check('index').findings)

    def test_clean_tip_does_not_hide_old_blob(self):
        # Commit objects only in this disposable fixture, never the user's repo.
        marker = str(uuid.uuid4())
        self.write('report.csv', marker)
        self.git('add', 'report.csv')
        tree1 = self.git('write-tree').decode().strip()
        commit1 = self.git('commit-tree', tree1, input=b'synthetic old fixture\n').decode().strip()
        self.write('report.csv', 'chat-01')
        self.git('add', 'report.csv')
        tree2 = self.git('write-tree').decode().strip()
        commit2 = self.git('commit-tree', tree2, '-p', commit1, input=b'synthetic cleaned fixture\n').decode().strip()
        r = self.run_check('history', [commit2])
        self.assertIn('uuid', {f['category'] for f in r.findings})
        self.assertNotIn(marker, json.dumps(r.findings))

    def test_installer_refuses_existing_hook(self):
        target = self.root / '.git' / 'hooks' / 'pre-commit'
        target.write_text('keep this', encoding='utf-8')
        with self.assertRaises(ValueError):
            hooks.install(self.root)
        self.assertEqual(target.read_text(), 'keep this')

    def test_installer_refuses_custom_hooks_path(self):
        self.git('config', 'core.hooksPath', 'custom-hooks')
        with self.assertRaises(ValueError):
            hooks.install(self.root)

    def test_installer_and_precommit_guard(self):
        with contextlib.redirect_stdout(io.StringIO()):
            hooks.install(self.root)
        target = self.root / '.git' / 'hooks' / 'pre-commit'
        self.assertIn('--guard pre-commit', target.read_text())
        with patch.object(hooks.subprocess, 'call', return_value=1) as call:
            self.assertEqual(hooks.guard('pre-commit', self.root), 1)
            self.assertIn('index', call.call_args[0][0])

    def test_prepush_scans_full_proposed_history_and_deletions(self):
        oid = 'a' * 40
        zeros = '0' * 40
        with patch('sys.stdin', io.StringIO(f'refs/heads/main {oid} refs/heads/main {zeros}\n')):
            with patch.object(hooks.subprocess, 'call', return_value=1) as call:
                self.assertEqual(hooks.guard('pre-push', self.root), 1)
                self.assertEqual(call.call_args[0][0][-2:], ['--refs', oid])
        with patch('sys.stdin', io.StringIO(f'(delete) {zeros} refs/heads/main {oid}\n')):
            self.assertEqual(hooks.guard('pre-push', self.root), 0)

    def test_failed_inspection_never_prints_path_details(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = pc.main(['worktree', '--root', str(self.root / 'absent')])
        self.assertEqual(result, 1)
        self.assertNotIn(str(self.root), output.getvalue())


if __name__ == '__main__':
    unittest.main()
