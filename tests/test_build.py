import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import skillsets
import check


class Build(unittest.TestCase):
    def test_packages_are_self_contained_and_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for entry in skillsets.load_registry():
                a, b = root / (entry['name']+'-a'), root / (entry['name']+'-b')
                skillsets.render_set(entry, a)
                skillsets.render_set(entry, b)
                self.assertEqual(skillsets.tree_hash(a), skillsets.tree_hash(b))
                self.assertTrue((a/'scripts/custom_fields.py').exists())
                self.assertTrue((a/'references/tool.md').exists())
                self.assertTrue((a/'references/policy.md').exists())
                self.assertTrue((a/'scripts/data/set.toml').exists())
                front = (a/'SKILL.md').read_text().split('---', 2)[1]
                self.assertNotIn('\nmodel:', front)
                if entry['tool'] == 'codex':
                    self.assertIn('allow_implicit_invocation: false', (a/'agents/openai.yaml').read_text())
                elif entry['adapter']['invocation_format'] in ('claude', 'grok', 'cursor'):
                    self.assertIn('disable-model-invocation: true', front)
                else:
                    spec = importlib.util.spec_from_file_location('preview_adapter', ROOT/'adapters'/entry['tool']/'eval_adapter.py')
                    adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
                    self.assertEqual(adapter.INSTALL_DIR, '.invoice-reader/packages')
                    self.assertFalse(adapter.analyse('{"type":"result","success":true}')['completed'])

    def test_build_refuses_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            keep = root/'user.txt'
            keep.write_text('Keep me')
            with self.assertRaises(ValueError):
                skillsets.render_set(skillsets.load_registry()[0], root)
            self.assertEqual(keep.read_text(), 'Keep me')

    def test_drift_check_detects_changed_script(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = skillsets.load_registry()[0]
            a, b = root/'a', root/'b'
            skillsets.render_set(entry, a)
            skillsets.render_set(entry, b)
            (b/'scripts/process.py').write_text('changed')
            self.assertIn('changed scripts/process.py', check.differences(a, b))

    def test_cli_failures_are_not_valid_completions(self):
        for tool in ('codex', 'claude-code', 'gemini-cli', 'grok-build', 'cursor'):
            spec = importlib.util.spec_from_file_location(tool, ROOT/'adapters'/tool/'eval_adapter.py')
            adapter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(adapter)
            self.assertFalse(adapter.analyse('')['completed'])
            self.assertFalse(adapter.analyse('{"type":"error"}')['completed'])

    def test_codex_telemetry_does_not_turn_request_into_identity(self):
        spec = importlib.util.spec_from_file_location('codex_eval', ROOT/'adapters/codex/eval_adapter.py')
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        completed = '{"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":3}}'
        result = adapter.analyse('non-json diagnostic\n' + completed)
        self.assertTrue(result['completed'])
        self.assertEqual(result['models_reported_by_cli'], [])
        self.assertEqual(result['usage'], {'input_tokens': 12, 'output_tokens': 3})
        failed = adapter.analyse(completed + '\n{"type":"turn.failed"}')
        self.assertFalse(failed['completed'])
        reported = adapter.analyse('{"model":"reported-example"}\n' + completed)
        self.assertEqual(reported['models_reported_by_cli'], ['reported-example'])

    def test_codex_reconnection_notice_requires_later_success(self):
        spec = importlib.util.spec_from_file_location('codex_eval', ROOT/'adapters/codex/eval_adapter.py')
        adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
        notice = '{"type":"error","message":"Reconnecting... 1/5 (stream disconnected before completion: websocket closed by server before response.completed)"}'
        done = '{"type":"turn.completed"}'
        result = adapter.analyse(notice+'\n'+done)
        self.assertTrue(result['completed']); self.assertEqual(len(result['transport_retries']),1)
        for stream in (notice, notice+'\n{"type":"turn.failed"}\n'+done,
                       '{"type":"error","message":"Authentication failed"}\n'+done, done+'\n'+notice):
            self.assertFalse(adapter.analyse(stream)['completed'])
