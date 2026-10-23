import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'eval' / 'runner'))
import skillsets
import cursor_session
import opening_v9


def load_adapter():
    spec = importlib.util.spec_from_file_location('cursor_eval', ROOT / 'adapters' / 'cursor' / 'eval_adapter.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    return adapter


class CursorAdapter(unittest.TestCase):
    def test_command_never_overrides_model_or_effort(self):
        adapter = load_adapter()
        argv = adapter.command('agent', 'Grok 4.7', 'Read the named public invoice.')
        self.assertEqual(argv[:5], ['agent', '-p', '--output-format', 'stream-json', '--trust'])
        self.assertNotIn('--model', argv)
        self.assertNotIn('Grok 4.7', argv)
        self.assertFalse(any('effort' in part.casefold() for part in argv))
        self.assertEqual(adapter.INSTALL_DIR, '.cursor/skills')
        with self.assertRaises(ValueError):
            adapter.command('agent', '', 'prompt', images=('page.png',))

    def test_completion_requires_one_successful_session(self):
        adapter = load_adapter()
        self.assertFalse(adapter.analyse('')['completed'])
        self.assertFalse(adapter.analyse('{"type":"error"}')['completed'])
        self.assertFalse(adapter.analyse('{"type":"result","subtype":"success","is_error":false}')['completed'])
        png = {'type': 'tool_call', 'subtype': 'completed', 'call_id': 'read-1',
               'tool_call': {'readToolCall': {'args': {'path': 'page.png'},
                                              'result': {'success': {'content': 'rendered text only'}}}}}
        success = {'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': 'chat-1',
                   'duration_ms': 5, 'result': 'done'}
        init = {'type': 'system', 'subtype': 'init', 'session_id': 'chat-1', 'model': 'display-name',
                'apiKeySource': 'login'}
        info = adapter.analyse('\n'.join(json.dumps(item) for item in (init, png, success)))
        self.assertTrue(info['completed'])
        self.assertEqual(info['models_reported_by_cli'], ['display-name'])
        self.assertEqual(info['session_ids'], ['chat-1'])
        self.assertEqual(info['api_key_source'], 'login')
        self.assertFalse(info['image_tool_returned_content'])
        mismatched = dict(success, session_id='chat-2')
        self.assertFalse(adapter.analyse(json.dumps(init) + '\n' + json.dumps(mismatched))['completed'])

    def test_package_is_explicit_and_reuses_xai_prompt(self):
        entry = next(item for item in skillsets.load_registry() if item['tool'] == 'cursor')
        self.assertEqual(entry['family'], 'xai')
        self.assertEqual(entry['invocation'], 'manual')
        self.assertEqual(entry['name'], 'invoice-reader-xai-cursor')
        self.assertFalse(entry['recommended_model'])
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / entry['name']
            skillsets.render_set(entry, target)
            front = (target / 'SKILL.md').read_text(encoding='utf-8').split('---', 2)[1]
            self.assertIn('name: invoice-reader-xai-cursor\n', front)
            self.assertIn('disable-model-invocation: true', front)
            self.assertNotIn('\nmodel:', front)
            self.assertNotIn('effort', front.casefold())
            self.assertIn('xAI-family prompt', (target / 'SKILL.md').read_text(encoding='utf-8'))
            self.assertIn('Alt+Enter', (target / 'references' / 'tool.md').read_text(encoding='utf-8'))

    def test_prepare_keeps_answers_outside_the_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = cursor_session.prepare(Path(directory) / 'batch', ['digit-boundary-v1'], r'Z:/synthetic-fixture/python.exe')
            work = Path(directory) / 'batch' / 'digit-boundary-v1' / 'workspace'
            run = Path(directory) / 'batch' / 'digit-boundary-v1' / 'run-1'
            self.assertTrue((work / '.cursor' / 'skills' / 'invoice-reader-xai-cursor' / 'SKILL.md').exists())
            self.assertTrue((work / 'digit-boundary-v1.pdf').exists())
            self.assertFalse((work / 'expected.json').exists())
            self.assertTrue((run / 'expected.json').exists())
            paste = (run / 'PASTE-OPENING.txt').read_text(encoding='utf-8')
            self.assertNotIn((run / 'expected.json').read_text(encoding='utf-8')[:80], paste)
            self.assertNotIn('--model', paste)
            self.assertIn('SCRIPTED PUBLIC FIXTURE', (run / 'PASTE-REPLY.txt').read_text(encoding='utf-8'))
            self.assertEqual(lock['cases'][0]['raw_reference'], 'configured')
            self.assertTrue((Path(directory) / 'batch' / 'lock.json').exists())

    def test_opening_observation_is_separate_from_codex_v9(self):
        self.assertEqual(opening_v9.VERSION, 'codex-opening-v9')
        message = ('Have you read the Readme about the data policy for your model?\n'
                   '- Yes, I have read it.\n'
                   '- No, but I will read it before I upload any confidential data')
        observed = cursor_session.observe_opening([message])
        self.assertEqual(observed['exact_question_count'], 1)
        self.assertTrue(observed['both_choices_present'])
        self.assertFalse(observed['yes_only_language_observed'])
        self.assertEqual(observed['pause'], 'not_attested_by_text')
        self.assertNotEqual(observed['grader'], opening_v9.VERSION)
        gated = cursor_session.observe_opening([message + '\nOnly a Yes answer can continue.'])
        self.assertTrue(gated['yes_only_language_observed'])

    def test_xai_prompt_keeps_one_channel_and_complete_numbers(self):
        packages = {item['tool']: item for item in skillsets.load_registry() if item['family'] == 'xai'}
        self.assertEqual(packages['cursor']['version'], '0.1.2')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for tool, entry in packages.items():
                target = root / tool
                skillsets.render_set(entry, target)
                text = (target / 'SKILL.md').read_text(encoding='utf-8')
                self.assertIn('Do not also call a question tool', text)
                self.assertIn('end the turn', text)
                self.assertIn('leave the field blank, mark it unclear', text)
                self.assertIn('Do not store that fragment as the amount', text)
                self.assertNotIn('\nmodel:', text.split('---', 2)[1])
            cursor_tool = (root / 'cursor' / 'references' / 'tool.md').read_text(encoding='utf-8')
            grok_tool = (root / 'grok-build' / 'references' / 'tool.md').read_text(encoding='utf-8')
            self.assertIn('Do not call AskQuestion', cursor_tool)
            self.assertIn('does not wait', cursor_tool)
            self.assertNotIn('AskQuestion', grok_tool)


if __name__ == '__main__':
    unittest.main()
