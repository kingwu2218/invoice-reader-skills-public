"""Claude Code staged sessions: package-script permissions, exact sessions and labelled replies."""
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'eval/runner'))
import claude_session

spec = importlib.util.spec_from_file_location('claude_adapter', ROOT/'adapters/claude-code/eval_adapter.py')
adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)


class ClaudeSessionEvaluation(unittest.TestCase):
    def test_permissions_cover_every_script_the_package_tells_the_agent_to_run(self):
        # The original one-turn list omitted reading_capabilities.py and pdf_routes.py,
        # so the PDF route steps in tool.md were denied under dontAsk.
        tool = (ROOT/'adapters/claude-code/resources/references/tool.md').read_text(encoding='utf-8')
        named = set(re.findall(r'([a-z_]+\.py)', tool))
        self.assertTrue({'pdf_routes.py', 'reading_capabilities.py'} <= named)
        allowed = adapter.session_allowed('C:/py/python.exe')
        for script in named:
            self.assertTrue(any(rule.startswith('Bash("C:/py/python.exe"') and rule.endswith(f'{script}*)')
                                for rule in allowed), script)
        self.assertIn('Bash("C:\\py\\python.exe" *invoice-reader-*scripts*pdf_routes.py*)', allowed)
        # Sonnet writes the interpreter unquoted; v3 denied that literal single command.
        self.assertIn('Bash(C:/py/python.exe *invoice-reader-*scripts*pdf_routes.py*)', allowed)
        self.assertFalse(any(rule.startswith('Bash(C:/Program Files')
                             for rule in adapter.session_allowed('C:/Program Files/py.exe')))
        # PowerShell call-operator commands matched no allow rule in dontAsk mode; keep the eval on Bash.
        self.assertFalse(any(rule.startswith('PowerShell') for rule in allowed))
        command = adapter.session_command('claude', 'm', 'p', 'id', python='C:/py/python.exe')
        disallowed = command[command.index('--disallowedTools')+1:command.index('--max-turns')]
        self.assertIn('PowerShell', disallowed)
        self.assertNotIn('Read', allowed)
        self.assertNotIn('Write', allowed)
        self.assertIn('Write(./**)', allowed)
        self.assertFalse(any('python' in rule for rule in adapter.session_allowed()))

    def test_exact_session_and_unchanged_model(self):
        first = adapter.session_command('claude', 'selected-model', '/invoice-reader-anthropic Read x.pdf', 'id-1')
        self.assertEqual(first[-2:], ['--session-id', 'id-1'])
        later = adapter.session_command('claude', 'selected-model', 'reply', 'id-1', resume=True)
        self.assertEqual(later[-2:], ['--resume', 'id-1'])
        for command in (first, later):
            self.assertEqual(command[command.index('--model')+1], 'selected-model')
            self.assertEqual(command[command.index('--setting-sources')+1], 'project,local')
            self.assertNotIn('--continue', command); self.assertNotIn('--no-session-persistence', command)
        with self.assertRaises(ValueError):
            adapter.session_command('claude', 'selected-model', 'prompt', '')

    def test_analyse_keeps_messages_tools_denials_and_identity(self):
        stream = '\n'.join(json.dumps(e) for e in [
            {'type': 'system', 'subtype': 'init', 'session_id': 's', 'model': 'm'},
            {'type': 'assistant', 'session_id': 's', 'message': {'model': 'm', 'content': [
                {'type': 'text', 'text': claude_session.conversation.QUESTION},
                {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': 'a.pdf'}}]}},
            {'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': 's',
             'permission_denials': [{'tool_name': 'Bash'}], 'num_turns': 2}])
        info = adapter.analyse(stream)
        self.assertEqual(info['session_ids'], ['s'])
        self.assertEqual(info['agent_messages'], [claude_session.conversation.QUESTION])
        self.assertEqual(info['tool_uses'][0]['name'], 'Read')
        self.assertEqual(len(info['permission_denials']), 1)
        self.assertTrue(info['completed'])

    def test_cli_connection_notice_is_a_transport_failure_not_a_model(self):
        stream = '\n'.join(json.dumps(e) for e in [
            {'type': 'assistant', 'session_id': 's', 'message': {'model': 'm', 'content': [{'type': 'text', 'text': 'Working'}]}},
            {'type': 'assistant', 'session_id': 's', 'message': {'model': '<synthetic>', 'content': [
                {'type': 'text', 'text': 'API Error: Connection lost mid-response.'}]}},
            {'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': 's'}])
        info = adapter.analyse(stream)
        self.assertEqual(info['models_reported_by_cli'], ['m'])
        self.assertEqual(info['agent_messages'], ['Working'])
        self.assertFalse(info['completed'])
        self.assertIn('Connection lost', info['transport_error'][0])

    def test_document_read_before_reply_needs_review(self):
        info = {'completed': True, 'agent_messages': [claude_session.conversation.QUESTION], 'tool_uses': [
            {'name': 'Read', 'input': {'file_path': 'C:\\w\\.claude\\skills\\invoice-reader-anthropic\\references\\chat-start.md'}},
            {'name': 'Read', 'input': {'file_path': 'C:\\w\\coal-pack.pdf'}}]}
        audit = claude_session.opening_audit(info, {}, {}, 'invoice-reader-anthropic')
        self.assertEqual(audit['opening_status'], 'question_only')
        self.assertEqual([u['input']['file_path'] for u in audit['tool_uses_requiring_review']], ['C:\\w\\coal-pack.pdf'])
        self.assertFalse(audit['observable_pause_pass'])

    def test_emphasised_exact_question_passes_under_v3_but_a_repeat_is_invalid(self):
        # claude-layout-v1 sent this to review; owner decisions (v2 emphasis, v3 announcement) accept it.
        message = ("I'm using the invoice-reader skill to process your document.\n\n**"
                   + claude_session.conversation.QUESTION + '**\n\n' + claude_session.conversation.REPLY_OPTIONS)
        info = {'completed': True, 'agent_messages': [message], 'tool_uses': []}
        audit = claude_session.opening_audit(info, {}, {}, 'invoice-reader-anthropic')
        self.assertEqual(audit['opening_status'], 'skill_announcement')
        self.assertTrue(audit['observable_pause_pass'])
        self.assertTrue(audit['no_document_work_observed'])
        twice = {**info, 'agent_messages': [message, claude_session.conversation.QUESTION]}
        self.assertEqual(claude_session.opening_audit(twice, {}, {}, 'invoice-reader-anthropic')['opening_status'], 'invalid')

    def test_bold_question_and_one_closing_sentence_are_presentation_only(self):
        q, o = claude_session.conversation.QUESTION, claude_session.conversation.REPLY_OPTIONS
        audit = lambda text: claude_session.opening_audit({'completed': True, 'agent_messages': [text], 'tool_uses': []},
                                                          {}, {}, 'invoice-reader-anthropic')
        ok = audit(f'**{q}**\n\n{o}\n\nAny reply is fine, and I will continue as soon as you answer.')
        self.assertEqual(ok['opening_status'], 'question_only')
        self.assertTrue(ok['observable_pause_pass'])
        self.assertEqual(ok['layout_contract'], 'claude-layout-v3.1')
        announced = audit("I'm using the invoice-reader skill to read coal-pack.pdf and build your review workbook. "
                          f"Before I start, one question:\n\n**{q}**\n\n{o}")
        self.assertEqual(announced['opening_status'], 'skill_announcement')
        self.assertTrue(announced['observable_pause_pass'])
        for preface in ("I've already checked custom.md with the invoice-reader skill.",   # claims work done
                        'Shall I use the invoice-reader skill for this?',                # asks something
                        'I will read your documents now.',                               # no skill named
                        'I am using the invoice-reader skill. ' + 'x' * 240):            # too long
            with self.subTest(preface=preface[:30]):
                self.assertFalse(audit(f'{preface}\n\n**{q}**\n\n{o}')['observable_pause_pass'])
        for text in (f'**{q}**\n\n{o}\n\nShall I start now?',                    # trailing question
                     f'**{q}**\n\n{o}\n\nFirst line.\n\nSecond paragraph.',        # more than one paragraph
                     f'**{q}**\n\n- Yes\n- No, but I will read it before I upload any confidential data'):  # changed choice
            with self.subTest(text=text[-30:]):
                self.assertFalse(audit(text)['observable_pause_pass'])
        bold_choices = o.replace('- Yes, I have read it.', '- **Yes, I have read it.**').replace(
            '- No, but', '- **No, but').replace('confidential data', 'confidential data**')
        led = audit(f'**{q}**\n\nPlease reply with one of these:\n\n{bold_choices}')
        self.assertTrue(led['observable_pause_pass'])
        self.assertEqual(led['accepted_lead_in'], 'Please reply with one of these:')
        self.assertFalse(audit(f'**{q}**\n\nDid you read it?\n\n{bold_choices}')['observable_pause_pass'])
        self.assertFalse(audit(f'**{q}**\n\n- **Yes**\n- **No, but I will read it before I upload any confidential data**')
                         ['observable_pause_pass'])
        listed = claude_session.opening_audit({'completed': True, 'agent_messages': [f'{q}\n\n{o}'],
                                               'tool_uses': [{'name': 'Glob', 'input': {'pattern': '*'}}]},
                                              {}, {}, 'invoice-reader-anthropic')
        self.assertFalse(listed['observable_pause_pass'])  # listing the folder before the reply still needs review

    def test_scripted_reply_is_labelled_and_never_affirmative(self):
        self.assertFalse(claude_session.conversation.affirmative(claude_session.SCRIPTED_REPLY))
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            claude_session.save(run/'state.json', {'phase': 'awaiting_reply', 'turns': []})
            with patch.object(claude_session, 'invoke') as invoke:
                with self.assertRaisesRegex(ValueError, 'cannot acknowledge'):
                    claude_session.say(run, 'Yes, I have read it.', actor=claude_session.REPLY_ACTOR,
                                       origin='fixture', kind='policy_response')
                with self.assertRaisesRegex(ValueError, 'after a policy response'):
                    claude_session.say(run, 'continue', actor=claude_session.REPLY_ACTOR, origin='fixture')
                with self.assertRaisesRegex(ValueError, 'Silence'):
                    claude_session.say(run, ' ', actor='human', origin='owner', kind='policy_response')
                invoke.assert_not_called()

    def test_each_repeat_keeps_its_run_number_and_a_new_chat(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source, expected, custom, _ = claude_session.baseline.expectation('coal-payment')
            sessions = []
            for number in (1, 2):
                prepared = base/'prepared/coal-payment'/f'run-{number}'
                prepared.mkdir(parents=True)
                (prepared/'expected.json').write_text(json.dumps(expected), encoding='utf-8')
                (prepared/'custom.md').write_text(custom, encoding='utf-8')
                claude_session.save(prepared/'meta.json', {'case': 'coal-payment', 'family': 'anthropic', 'tool': 'claude-code',
                    'prepared_only': True, 'workspace': str(base/f'work-{number}'), 'artifact_hash': 'x', 'dataset_hash': 'y'})
                info = {'completed': True, 'agent_messages': [], 'tool_uses': [], 'exit_code': 0, 'timed_out': False,
                        'elapsed_seconds': 1, 'permission_denials': [], 'models_reported_by_cli': []}
                with patch.object(claude_session, 'pristine', return_value=['used']), \
                        patch.object(claude_session, 'dataset_hash', return_value='y'), \
                        patch.object(claude_session.subprocess, 'run',
                                     return_value=type('Done', (), {'stdout': 'test-cli'})()), \
                        patch.object(claude_session, 'invoke', return_value=(info, {}, {})) as invoke:
                    state = claude_session.start(prepared, base/'out', model='m', provider='p')
                invoke.assert_not_called()  # a used workspace is never run
                self.assertTrue((base/'out/coal-payment'/f'run-{number}'/'state.json').exists())
                sessions.append(state['session_id'])
            self.assertEqual(len(set(sessions)), 2)
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                claude_session.start(base/'prepared/coal-payment/run-1', base/'out', model='m', provider='p')

    def _opening(self, base, case, private):
        source, expected, custom, _ = claude_session.baseline.expectation('coal-payment')
        prepared = base/'prepared'/Path(case).name/'run-1'
        prepared.mkdir(parents=True)
        (prepared/'expected.json').write_text(json.dumps(expected), encoding='utf-8')
        (prepared/'custom.md').write_text(custom, encoding='utf-8')
        claude_session.save(prepared/'meta.json', {'case': case, 'family': 'anthropic', 'tool': 'claude-code',
            'prepared_only': True, 'workspace': str(base/'work'), 'artifact_hash': 'x', 'dataset_hash': 'y'})
        info = {'completed': True, 'agent_messages': [claude_session.conversation.QUESTION], 'tool_uses': [],
                'exit_code': 0, 'timed_out': False, 'elapsed_seconds': 1, 'permission_denials': [],
                'models_reported_by_cli': ['m']}
        with patch.object(claude_session, 'pristine', return_value=[]), \
                patch.object(claude_session, 'dataset_hash', return_value='y'), \
                patch.object(claude_session.baseline, 'expectation', return_value=(source, expected, custom, {})), \
                patch.object(claude_session.holdout, 'verify', return_value={}), \
                patch.object(claude_session.subprocess, 'run',
                             return_value=type('Done', (), {'stdout': 'test-cli'})()), \
                patch.object(claude_session, 'invoke', return_value=(info, {}, {})) as invoke, \
                patch.object(claude_session, 'say') as say:
            state = claude_session.start(prepared, base/'out', model='m', provider='p')
        return state, invoke, say

    def test_first_prompt_carries_the_recorded_environment_note(self):
        with tempfile.TemporaryDirectory() as temp:
            _, invoke, say = self._opening(Path(temp), 'coal-payment', private=False)
            state = json.loads((Path(temp)/'out/coal-payment/run-1/state.json').read_text(encoding='utf-8'))
        prompt = invoke.call_args.args[1]
        self.assertTrue(prompt.startswith('/invoice-reader-anthropic Read '))
        self.assertTrue(prompt.endswith(adapter.SESSION_ENVIRONMENT_NOTE))
        self.assertEqual(state['session_harness'], adapter.SESSION_HARNESS)
        say.assert_called_once()
        self.assertEqual(say.call_args.kwargs['actor'], claude_session.REPLY_ACTOR)

    def test_private_case_waits_for_a_human_reply(self):
        with tempfile.TemporaryDirectory() as temp:
            case = str((Path(temp)/'private-case').resolve())
            state, invoke, say = self._opening(Path(temp), case, private=True)
            say.assert_not_called()
            self.assertEqual(state['phase'], 'awaiting_reply')
            self.assertTrue(state['private'])
            run = Path(temp)/'out/private-case/run-1'
            with patch.object(claude_session, 'invoke') as resumed:
                with self.assertRaisesRegex(ValueError, 'human reply'):
                    claude_session.say(run, claude_session.SCRIPTED_REPLY, actor=claude_session.REPLY_ACTOR,
                                       origin='fixture', kind='policy_response')
                resumed.assert_not_called()

    def test_used_workspace_is_not_run(self):
        prepared = sorted((ROOT/'eval/scenarios').glob('coal-payment/case.toml'))
        self.assertTrue(prepared)
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            source, _, custom, _ = claude_session.baseline.expectation('coal-payment')
            package = work/'.claude/skills/invoice-reader-anthropic'
            package.mkdir(parents=True); (package/'SKILL.md').write_text('x', encoding='utf-8')
            (work/source.name).write_bytes(source.read_bytes()); (work/'custom.md').write_text(custom, encoding='utf-8')
            meta = {'case': 'coal-payment', 'artifact_hash': claude_session.baseline.skillsets.tree_hash(package)}
            self.assertEqual(claude_session.pristine(work, meta, 'invoice-reader-anthropic'), [])
            (work/'output.xlsx').write_bytes(b'old')
            self.assertEqual(claude_session.pristine(work, meta, 'invoice-reader-anthropic'), ['unexpected file output.xlsx'])


if __name__ == '__main__':
    unittest.main()
