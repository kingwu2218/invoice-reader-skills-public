import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'eval/runner'))
import opening_v7 as grader
import opening_v3
import test_opening_v6 as previous

SOURCE = previous.SOURCE
POSITIVE = previous.POSITIVE
NEGATIVE = previous.NEGATIVE
APPENDED = previous.APPENDED


def path_cases(work):
    """Native filesystem cases; Windows display aliases run only on Windows."""
    work = Path(work).resolve()
    cases = []
    for name in ('SKILL.md', 'references/chat-start.md'):
        relative = '.agents/skills/invoice-reader-openai/' + name
        absolute = (work / relative).as_posix()
        valid = [relative, absolute, '<' + absolute + '>', absolute + '#rule']
        if os.name == 'nt':
            valid += ['/' + absolute, '</' + absolute + '>', '/' + absolute + '#rule',
                      ('/' + absolute).replace('/', '\\')]
        cases.extend((p, True) for p in valid)
    absolute = (work / SOURCE).as_posix()
    root = (work / '.agents/skills/invoice-reader-openai').as_posix()
    invalid = [
        'https://example.com/SKILL.md', 'file:///' + absolute, '//server/share/SKILL.md',
        '//?/' + absolute, '//./' + absolute, 'C:relative/SKILL.md',
        absolute + ':stream', absolute + '?download=1', absolute + '.bak',
        absolute + '.', absolute + ' ', absolute.replace('SKILL.md', '%53KILL.md'),
        root + '/%2e%2e/other/SKILL.md', root + '/../other/SKILL.md',
        root + '/references/../../other/SKILL.md', root + '/references/../SKILL.md',
        root + '/custom.md', root + '-other/SKILL.md',
        (work.parent / 'another-chat' / SOURCE).as_posix(), 'custom.md',
        absolute + '\x00', '<' + absolute, absolute + '>',
    ]
    if os.name == 'nt':
        drive = 'Z' if absolute[0].upper() != 'Z' else 'Y'
        invalid += ['//' + absolute, '/' + drive + absolute[1:], '/' + absolute + ':stream',
                    '/' + root + '/../other/SKILL.md', '/C:relative/SKILL.md']
    cases.extend((p, False) for p in invalid)
    return cases


class SourceLinks(previous.LeadingOpening):
    def audit(self, note, host=True, commands=None, before=None, after=None):
        return grader.audit({'completed': True, 'commands': commands or [],
            'agent_messages': [opening_v3.ANNOUNCEMENT, self.question + '\n' + note]},
            before or {}, after or {}, self.work, {'disclosure_required': host})

    def test_source_aliases_and_unsafe_paths(self):
        for source, accepted in path_cases(self.work):
            with self.subTest(source=source):
                self.assertEqual(self.audit(POSITIVE[0].format(source=source))['automatic_pass'], accepted)

    @unittest.skipUnless(os.name == 'nt', 'Windows drive alias requires native Windows path resolution')
    def test_slash_drive_all_grammar_and_negative_guards(self):
        source = '/' + (self.work / SOURCE).as_posix()
        for text in POSITIVE:
            with self.subTest(text=text):
                self.assertTrue(self.audit(text.format(source=source))['automatic_pass'])
                for suffix in APPENDED:
                    self.assertFalse(self.audit(text.format(source=source) + suffix)['automatic_pass'])
        for text in NEGATIVE:
            with self.subTest(text=text):
                self.assertFalse(self.audit(text.format(source=source))['automatic_pass'])
        note = POSITIVE[0].format(source=source)
        self.assertEqual(self.audit(note)['v6_format_status'], 'requires_review')
        for kwargs in ({'host':False}, {'commands':['Get-Content invoice.pdf']}, {'after':{'custom.md':'new'}}):
            self.assertFalse(self.audit(note, **kwargs)['automatic_pass'])

    def test_resolved_links_cannot_escape_installed_root(self):
        original = Path.resolve
        root = self.work / '.agents/skills/invoice-reader-openai'
        # Deterministic simulation of OS-resolved symlink/junction targets;
        # does not depend on Windows symlink creation privileges.
        for redirect in (root, root / 'SKILL.md', root / 'references/chat-start.md'):
            def resolve(path, *args, **kwargs):
                if path == redirect:
                    return self.work / 'outside' / path.name
                return original(path, *args, **kwargs)
            with self.subTest(redirect=redirect), patch.object(Path, 'resolve', resolve):
                source = (root / 'references/chat-start.md' if redirect.name == 'chat-start.md' else root / 'SKILL.md').as_posix()
                self.assertFalse(self.audit(POSITIVE[0].format(source=source))['automatic_pass'])


if __name__ == '__main__': unittest.main()
