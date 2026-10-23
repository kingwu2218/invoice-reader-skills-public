import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import skillsets


class PromptParts(unittest.TestCase):
    def source(self, root, body='Part one'):
        (root / 'prompt').mkdir()
        (root / 'prompt/one.md').write_text(body, encoding='utf-8')
        (root / 'SKILL.md').write_text('Header\n\n<!-- include: prompt/one.md -->\n', encoding='utf-8')

    def test_complete_body_is_embedded_and_tracks_source_edits(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.source(root)
            self.assertEqual(skillsets.compose_prompt(root), 'Header\n\nPart one\n')
            (root / 'prompt/one.md').write_text('Changed constraint', encoding='utf-8')
            self.assertIn('Changed constraint', skillsets.compose_prompt(root))

    def test_omitted_duplicate_and_missing_parts_fail(self):
        for mode in ('omitted', 'duplicate', 'missing'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d:
                root = Path(d); self.source(root)
                if mode == 'omitted': (root / 'prompt/two.md').write_text('Unloaded guardrail')
                elif mode == 'missing': (root / 'prompt/one.md').unlink()
                else:
                    p = root / 'SKILL.md'; p.write_text(p.read_text() * 2)
                with self.assertRaises(ValueError): skillsets.compose_prompt(root)

    def test_traversal_and_unrecognised_directives_fail(self):
        for include in ('../outside.md', 'prompt/../outside.md', '/absolute.md', 'prompt/one.md extra'):
            with self.subTest(include=include), tempfile.TemporaryDirectory() as d:
                root = Path(d); self.source(root)
                (root / 'SKILL.md').write_text(f'<!-- include: {include} -->')
                with self.assertRaises(ValueError): skillsets.compose_prompt(root)

    def test_empty_nested_and_frontmatter_parts_fail(self):
        for body in (' ', '<!-- include: prompt/two.md -->', '---\nmodel: override\n---'):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as d:
                root = Path(d); self.source(root, body)
                with self.assertRaises(ValueError): skillsets.compose_prompt(root)

    def test_installed_package_contains_all_parts_without_authoring_files(self):
        entry = next(e for e in skillsets.load_registry() if e['family'] == 'openai')
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'package'; skillsets.render_set(entry, target)
            text = (target / 'SKILL.md').read_text(encoding='utf-8')
            for part in (ROOT / 'skills/openai/prompt').glob('*.md'):
                self.assertIn(part.read_text(encoding='utf-8').strip(), text)
            self.assertNotIn('<!-- include:', text)
            self.assertFalse((target / 'prompt').exists())

    def test_unpartitioned_families_remain_unchanged(self):
        for name in ('anthropic', 'google', 'xai'):
            source = ROOT / 'skills' / name
            self.assertEqual(skillsets.compose_prompt(source), (source / 'SKILL.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
