"""Session binding, real acknowledgements and separate onboarding/extraction signals."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eval/runner'))
import conversation

spec = importlib.util.spec_from_file_location('session_adapter', ROOT/'adapters/codex/eval_adapter.py')
adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)


class ConversationEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.state = {'schema_version':1,'phase':'awaiting_acknowledgement','session_id':'known-session',
                      'workspace':str(self.base/'work'),'turns':[]}
        conversation.save(self.base/'state.json',self.state)

    def test_private_start_is_fresh_and_direct_with_locked_reference(self):
        from types import SimpleNamespace
        case=self.base/'private-case';case.mkdir()
        (case/'holdout-lock.json').write_text('{}')
        info={'completed':True,'session_ids':['fresh-private-session'],
              'agent_messages':[conversation.QUESTION+'\n\n'+conversation.REPLY_OPTIONS],'commands':[]}
        entry={'name':'invoice-reader-openai'}
        def prepared(entry, selected_case, run, work):
            run.mkdir(parents=True)
            return None,None,{'artifact_hash':'frozen-hash'}
        with patch.object(conversation.baseline,'REPO',self.base), \
                patch.object(conversation.baseline.skillsets,'load_registry',return_value=[entry]), \
                patch.object(conversation.baseline.skillsets,'package_path',return_value=self.base/'package'), \
                patch.object(conversation.baseline.skillsets,'tree_hash',return_value='frozen-hash'), \
                patch.object(conversation.holdout,'verify',return_value={'evaluation_kind':'known-source-regression'}) as verify, \
                patch.object(conversation.baseline,'prepare',side_effect=prepared) as prepare, \
                patch.object(conversation.baseline,'expectation',return_value=(case/'source.pdf',{},'',{})), \
                patch.object(conversation.tempfile,'mkdtemp',return_value=str(self.base/'work')), \
                patch.object(conversation.subprocess,'run',return_value=SimpleNamespace(stdout='test-cli')), \
                patch.object(conversation,'invoke',return_value=(info,{},{})) as invoke:
            base=conversation.start(str(case.resolve()),'selected-model','provider',private=True)
        verify.assert_called_once_with(case.resolve(),'frozen-hash')
        self.assertEqual(prepare.call_args.args[1],str(case.resolve()))
        self.assertEqual(len(invoke.call_args.args),3)  # No resume session or prior examples.
        prompt=invoke.call_args.args[1]
        self.assertIn('source.pdf',prompt)
        for forbidden in ('420','1420','Cash Memo','Receipt','expected.json','public'):
            self.assertNotIn(forbidden,prompt)
        state=conversation.load_state(base)
        self.assertTrue(state['private_start'])
        self.assertEqual(state['phase'],'awaiting_reply')
        self.assertEqual(state['session_id'],'fresh-private-session')

    def test_private_start_rejects_missing_lock_before_preparing_or_invoking(self):
        entry={'name':'invoice-reader-openai'}
        with patch.object(conversation.baseline.skillsets,'load_registry',return_value=[entry]), \
                patch.object(conversation.baseline.skillsets,'package_path',return_value=self.base/'package'), \
                patch.object(conversation.baseline.skillsets,'tree_hash',return_value='hash'), \
                patch.object(conversation.holdout,'verify',side_effect=ValueError('invalid lock')), \
                patch.object(conversation.baseline,'prepare') as prepare, \
                patch.object(conversation,'invoke') as invoke:
            with self.assertRaisesRegex(ValueError,'invalid lock'):
                conversation.start(str((self.base/'case').resolve()),'model','provider',private=True)
            prepare.assert_not_called();invoke.assert_not_called()

    def test_private_start_cannot_use_scripted_reply_or_changed_lock(self):
        self.state.update(phase='awaiting_reply',private_start=True,onboarding_contract=conversation.RESPONSE_CONTRACT,
                          case=str((self.base/'case').resolve()),artifact_hash='hash')
        conversation.save(self.base/'state.json',self.state)
        with patch.object(conversation,'invoke') as invoke:
            with self.assertRaisesRegex(ValueError,'Scripted responses'):
                conversation.respond(self.base,conversation.READ_LATER,actor='scripted_negative_fixture')
            with patch.object(conversation.holdout,'verify',side_effect=ValueError('changed lock')):
                with self.assertRaisesRegex(ValueError,'changed lock'):
                    conversation.respond(self.base,'No',evidence='actual new reply')
            invoke.assert_not_called()

    def test_exact_resume_never_latest_or_ephemeral(self):
        command = adapter.session_command('codex','selected-model','actual reply','session-123')
        self.assertIn('resume',command)
        self.assertEqual(command[-3:],['--','session-123','actual reply'])
        self.assertNotIn('--last',command); self.assertNotIn('--ephemeral',command)
        self.assertIn('--approve-for-me',command)

    def test_https_fallback_keeps_endpoint_auth_model_and_session(self):
        command=adapter.session_command('codex','selected-model','prompt','session-123',transport='https')
        self.assertEqual(command[-3:],['--','session-123','prompt'])
        self.assertEqual(command[command.index('--model')+1],'selected-model')
        config=next(c for c in command if c.startswith('model_providers.openai-https='))
        self.assertIn('https://chatgpt.com/backend-api/codex',config)
        self.assertIn('requires_openai_auth=true',config)
        self.assertIn('supports_websockets=false',config)
        self.assertNotIn('bearer_token',config)
        with self.assertRaises(ValueError):adapter.session_command('codex','model','prompt',transport='unknown')

    def test_public_scripted_policy_reply_cannot_continue_to_private_case(self):
        self.state.update(phase='response_received', turns=[{'actor':'scripted_negative_fixture',
                          'kind':'policy_response','reply':'No','reply_origin':'public fixture'}])
        conversation.save(self.base/'state.json', self.state)
        with patch.object(conversation, 'invoke') as invoke, patch.object(conversation.baseline,'prepare') as prepare, \
                patch.object(conversation.holdout,'verify') as verify:
            with self.assertRaisesRegex(ValueError,'public scripted policy fixture'):
                conversation.continue_case(self.base, str((self.base/'private-case').resolve()))
            invoke.assert_not_called(); prepare.assert_not_called(); verify.assert_not_called()

    def test_messages_only_and_session_identity_come_from_cli_events(self):
        stream = '\n'.join(json.dumps(e) for e in [
            {'type':'thread.started','thread_id':'id-1'},
            {'type':'item.completed','item':{'type':'command_execution','command':'cat SKILL.md','aggregated_output':conversation.QUESTION}},
            {'type':'item.completed','item':{'type':'agent_message','text':conversation.QUESTION}},
            {'type':'turn.completed'}])
        result = adapter.analyse(stream)
        self.assertEqual(result['session_ids'],['id-1'])
        self.assertEqual(result['agent_messages'],[conversation.QUESTION])
        self.assertEqual(result['models_reported_by_cli'],[])

    def test_failed_retry_preserves_attempt_and_exact_session(self):
        self.state.update(phase='execution_failed', case='format-parties-v2', case_id='format-parties-v2',
                          model_requested='selected-model', turns=[{'kind':'policy_response', 'actor':'human',
                          'reply_origin':'real reply'}])
        conversation.save(self.base/'state.json', self.state)
        old = self.base/'extractions/format-parties-v2/run-1/meta.json'
        old.parent.mkdir(parents=True)
        conversation.save(old, {'completed':False, 'valid':False})
        original = old.read_bytes()
        info = {'completed':True,'session_ids':['known-session'],'agent_messages':[]}
        with patch.object(conversation.baseline, 'prepare', return_value=(None,None,{})), \
                patch.object(conversation.tempfile, 'mkdtemp', return_value=str(self.base/'retry-work')), \
                patch.object(conversation, 'invoke', return_value=(info,{},{})) as invoke, \
                patch.object(conversation, 'finish'):
            conversation.continue_case(self.base, 'format-parties-v2', retry_failed=True)
        state = conversation.load_state(self.base)
        self.assertEqual(invoke.call_args.args[3], 'known-session')
        self.assertEqual(state['case_id'], 'format-parties-v2-retry-2')
        self.assertEqual(state['retry_of'], 'format-parties-v2')
        self.assertEqual(old.read_bytes(), original)

    def test_retry_rejects_successful_prediction_and_different_case(self):
        self.state.update(phase='execution_failed', case='format-parties-v2', case_id='format-parties-v2',
                          turns=[{'kind':'policy_response'}])
        conversation.save(self.base/'state.json', self.state)
        (self.base/'extractions/format-parties-v2/run-1').mkdir(parents=True)
        conversation.save(self.base/'extractions/format-parties-v2/run-1/meta.json',
                          {'completed':True, 'valid':False})
        with patch.object(conversation, 'invoke') as invoke:
            with self.assertRaisesRegex(ValueError, 'incomplete executions'):
                conversation.continue_case(self.base, 'format-parties-v2', retry_failed=True)
            with self.assertRaisesRegex(ValueError, 'same failed case'):
                conversation.continue_case(self.base, 'different-case', retry_failed=True)
            invoke.assert_not_called()

    def test_next_batch_after_incomplete_execution_keeps_failure(self):
        self.state.update(phase='execution_failed', case='old-case', case_id='old-case',
                          turns=[{'kind':'policy_response','actor':'human','reply_origin':'real reply'}])
        conversation.save(self.base/'state.json', self.state)
        old=self.base/'extractions/old-case/run-1/meta.json'; old.parent.mkdir(parents=True)
        conversation.save(old, {'completed':False,'valid':False})
        original=old.read_bytes()
        info={'completed':True,'session_ids':['known-session'],'agent_messages':[]}
        with patch.object(conversation.baseline,'prepare',return_value=(None,None,{})), \
                patch.object(conversation.tempfile,'mkdtemp',return_value=str(self.base/'next-work')), \
                patch.object(conversation,'invoke',return_value=(info,{},{})) as invoke, \
                patch.object(conversation,'finish'):
            conversation.continue_case(self.base,'format-parties-v2')
        self.assertEqual(invoke.call_args.args[3],'known-session')
        self.assertIn('do not finish or modify earlier workspaces',invoke.call_args.args[1])
        self.assertEqual(conversation.load_state(self.base)['after_failure'],'old-case')
        self.assertEqual(old.read_bytes(),original)

    def test_retry_earlier_failure_after_later_case_keeps_completion_and_deadline(self):
        self.state.update(phase='acknowledged',case='later-case',case_id='later-case',
                          turns=[{'kind':'policy_response','actor':'human','reply_origin':'real reply'},
                                 {'kind':'same_chat_batch','case':'format-parties-v2'},
                                 {'kind':'same_chat_batch','case':'later-case'}])
        conversation.save(self.base/'state.json',self.state)
        for case, completed in [('format-parties-v2',False),('later-case',True)]:
            p=self.base/'extractions'/case/'run-1/meta.json';p.parent.mkdir(parents=True)
            conversation.save(p,{'case':case,'completed':completed,'valid':completed})
        later=self.base/'extractions/later-case/run-1/meta.json'; original=later.read_bytes()
        info={'completed':True,'session_ids':['known-session'],'agent_messages':[]}
        with patch.object(conversation.baseline,'prepare',return_value=(None,None,{})), \
                patch.object(conversation.tempfile,'mkdtemp',return_value=str(self.base/'retry-work')), \
                patch.object(conversation,'invoke',return_value=(info,{},{})) as invoke, \
                patch.object(conversation,'finish'):
            conversation.continue_case(self.base,'format-parties-v2',retry_failed=True,timeout_seconds=600)
        self.assertEqual(invoke.call_args.args[0]['execution_timeout_seconds'],600)
        self.assertEqual(conversation.load_state(self.base)['retry_of'],'format-parties-v2')
        self.assertEqual(later.read_bytes(),original)
        with self.assertRaisesRegex(ValueError,'incomplete executions'):
            conversation.continue_case(self.base,'later-case',retry_failed=True)

    def test_invalid_deadline_cannot_start_execution(self):
        with patch.object(conversation,'invoke') as invoke:
            for value in (0,3601,True,'600'):
                with self.assertRaisesRegex(ValueError,'Execution timeout'):
                    conversation.continue_case(self.base,'format-parties-v2',timeout_seconds=value)
            invoke.assert_not_called()
        with patch.object(conversation.baseline,'module') as module:
            with self.assertRaisesRegex(ValueError,'Execution timeout'):
                conversation.invoke({'execution_timeout_seconds':0},'prompt',self.base/'new-turn')
            module.assert_not_called()

    def test_retry_finds_failed_opening_batch_without_case_id_in_turns(self):
        self.state.update(phase='response_received',case='later-case',case_id='later-case',
                          turns=[{'kind':'start'},
                                 {'kind':'policy_response','actor':'human','reply_origin':'real reply'},
                                 {'kind':'same_chat_batch','case':'later-case'}])
        conversation.save(self.base/'state.json',self.state)
        for case, completed in [('format-parties-v2',False),('later-case',True)]:
            p=self.base/'extractions'/case/'run-1/meta.json';p.parent.mkdir(parents=True)
            conversation.save(p,{'case':case,'completed':completed,'valid':completed})
        info={'completed':True,'session_ids':['known-session'],'agent_messages':[]}
        with patch.object(conversation.baseline,'prepare',return_value=(None,None,{})), \
                patch.object(conversation.tempfile,'mkdtemp',return_value=str(self.base/'retry-work')), \
                patch.object(conversation,'invoke',return_value=(info,{},{})), \
                patch.object(conversation,'finish'):
            conversation.continue_case(self.base,'format-parties-v2',retry_failed=True)
        self.assertEqual(conversation.load_state(self.base)['retry_of'],'format-parties-v2')
        conversation.save(self.base/'extractions/format-parties-v2/run-1/meta.json',
                          {'case':'format-parties-v2','completed':True,'valid':True})
        with self.assertRaisesRegex(ValueError,'incomplete executions'):
            conversation.continue_case(self.base,'format-parties-v2',retry_failed=True)

    def test_recorded_deadline_is_passed_to_subprocess(self):
        from types import SimpleNamespace
        work=self.base/'work';work.mkdir()
        state={**self.state,'model_requested':'selected-model','execution_timeout_seconds':17,
               'codex_transport':'https'}
        fake=SimpleNamespace(session_command=lambda *a,**kw:['codex','exec','--','prompt'],
                             analyse=lambda text:{'session_ids':['known-session'],
                                                  'models_reported_by_cli':[],'completed':True})
        with patch.object(conversation.baseline,'module',return_value=fake), \
                patch.object(conversation.shutil,'which',return_value='codex'), \
                patch.object(conversation.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
            conversation.invoke(state,'prompt',self.base/'turn','known-session')
        self.assertEqual(run.call_args.kwargs['timeout'],17)

    def test_retry_can_copy_archived_intermediates_without_answers_or_workbook(self):
        self.state.update(phase='execution_failed',case='format-parties-v2',case_id='format-parties-v2',
                          turns=[{'kind':'policy_response','actor':'human','reply_origin':'actual reply'}])
        conversation.save(self.base/'state.json',self.state)
        run=self.base/'extractions/format-parties-v2/run-1';archived=run/'work/run-a'
        archived.mkdir(parents=True)
        (archived/'manifest.json').write_text('{"inputs":[]}')
        (archived/'page.png').write_bytes(b'rendered page')
        (run/'output.xlsx').write_bytes(b'old partial workbook')
        (run/'expected.json').write_text('private reference')
        conversation.save(run/'meta.json',{'case':'format-parties-v2','completed':False,'valid':False})
        before=conversation.snapshot(run)
        work=self.base/'new-work';work.mkdir()
        info={'completed':True,'session_ids':['known-session'],'agent_messages':[]}
        with patch.object(conversation.baseline,'prepare',return_value=(None,None,{})), \
                patch.object(conversation.tempfile,'mkdtemp',return_value=str(work)), \
                patch.object(conversation,'invoke',return_value=(info,{},{})) as invoke, \
                patch.object(conversation,'finish'):
            conversation.continue_case(self.base,'format-parties-v2',retry_failed=True,resume_work=True)
        self.assertEqual(conversation.snapshot(run),before)
        self.assertTrue((work/'invoice-reader-work/run-a/page.png').exists())
        self.assertFalse((work/'expected.json').exists());self.assertFalse((work/'output.xlsx').exists())
        self.assertIn('existing manifest and rendered pages',invoke.call_args.args[1])
        self.assertEqual(conversation.load_state(self.base)['resumed_work']['from_attempt'],'format-parties-v2')

    def test_resume_refuses_ambiguous_manifests_before_preparing_new_case(self):
        self.state.update(phase='execution_failed',case='format-parties-v2',case_id='format-parties-v2',
                          turns=[{'kind':'policy_response','actor':'human','reply_origin':'actual reply'}])
        conversation.save(self.base/'state.json',self.state)
        run=self.base/'extractions/format-parties-v2/run-1';run.mkdir(parents=True)
        conversation.save(run/'meta.json',{'case':'format-parties-v2','completed':False,'valid':False})
        for name in ('run-a','run-b'):
            folder=run/'work'/name;folder.mkdir(parents=True)
            (folder/'manifest.json').write_text('{}')
        with patch.object(conversation.baseline,'prepare') as prepare,patch.object(conversation,'invoke') as invoke:
            with self.assertRaisesRegex(ValueError,'exactly one archived'):
                conversation.continue_case(self.base,'format-parties-v2',retry_failed=True,resume_work=True)
            prepare.assert_not_called();invoke.assert_not_called()

    def test_waiting_is_not_extraction_failure_or_zero_accuracy(self):
        info = {'completed':True,'agent_messages':[conversation.QUESTION],'commands':[]}
        audit = conversation.onboarding(info,{'custom.md':'hash'},{'custom.md':'hash'},first=True)
        self.assertTrue(audit['observable_pause_pass'])
        self.assertNotIn('field_accuracy',audit)
        self.assertFalse(list(self.base.glob('extractions/**/meta.json')))

    def test_generic_preface_and_work_before_ack_are_separate_failures(self):
        info = {'completed':True,'agent_messages':['I will start.',conversation.QUESTION],'commands':[]}
        audit = conversation.onboarding(info,{}, {},first=True)
        self.assertFalse(audit['question_first']);self.assertTrue(audit['no_document_work_observed'])
        info['commands'] = ['python scripts/pdf_routes.py client.pdf']
        audit = conversation.onboarding(info,{}, {'output.xlsx':'hash'},first=True)
        self.assertFalse(audit['no_document_work_observed'])
        self.assertTrue(audit['commands_requiring_review'])

    def test_announcement_before_exact_question_in_one_or_two_messages(self):
        announcement = 'I’m using the invoice-reader-openai skill.'
        for messages in ([announcement, conversation.QUESTION], [announcement+'\n\n'+conversation.QUESTION]):
            info = {'completed':True, 'agent_messages':messages, 'commands':[]}
            audit = conversation.onboarding(info, {}, {}, first=True)
            self.assertFalse(audit['question_first'])
            self.assertEqual(audit['opening_status'], 'skill_announcement')
            self.assertTrue(audit['observable_pause_pass'])
            old = conversation.onboarding(info, {}, {}, first=True, contract='literal-first-v1')
            self.assertFalse(old['observable_pause_pass'])

    def test_announcement_cannot_replace_question_or_cover_early_work(self):
        announcement = 'I will use the invoice-reader skill.'
        for messages in ([announcement], [announcement, 'Have you read the policy?'],
                         [conversation.QUESTION, conversation.QUESTION],
                         [conversation.QUESTION, announcement]):
            info = {'completed':True, 'agent_messages':messages, 'commands':[]}
            self.assertFalse(conversation.onboarding(info, {}, {}, first=True)['observable_pause_pass'])
        info = {'completed':True, 'agent_messages':[announcement, conversation.QUESTION],
                'commands':['python scripts/pdf_routes.py source.pdf']}
        self.assertFalse(conversation.onboarding(info, {}, {}, first=True)['observable_pause_pass'])
        info['commands'] = []
        self.assertFalse(conversation.onboarding(info, {}, {'custom.md':'new'}, first=True)['observable_pause_pass'])

    def test_unrecognised_or_misleading_preface_requires_review(self):
        for preface in ('I read your PDF using the invoice-reader skill.',
                        'I’m using the invoice-reader skill. I extracted the total.',
                        '我會使用 invoice-reader skill。'):
            info = {'completed':True, 'agent_messages':[preface, conversation.QUESTION], 'commands':[]}
            audit = conversation.onboarding(info, {}, {}, first=True)
            self.assertEqual(audit['opening_status'], 'requires_review')
            self.assertFalse(audit['observable_pause_pass'])

    def test_historical_report_keeps_original_contract(self):
        info = {'completed':True, 'agent_messages':['I am using the invoice-reader skill.', conversation.QUESTION],
                'commands':[], 'session_ids':['known-session']}
        folder = self.base/'turns/001-start'; folder.mkdir(parents=True)
        conversation.save(folder/'turn.json', info)
        conversation.save(folder/'snapshots.json', {'before':{}, 'after':{}})
        self.state['turns'] = [{'folder':'turns/001-start', 'kind':'start', 'audit':{'question_first':False}}]
        conversation.save(self.base/'state.json', self.state)
        result = conversation.report(self.base)
        audit = result['onboarding'][0]['audit']
        self.assertEqual(audit['onboarding_contract'], 'literal-first-v1')
        self.assertFalse(audit['observable_pause_pass'])

    def test_negative_silence_or_custom_confirmation_cannot_acknowledge(self):
        for text in ('', 'No', 'Not sure', 'Confirmed by user: yes', 'Continue processing', 'Yesterday I read it'):
            self.assertFalse(conversation.affirmative(text))
        self.assertTrue(conversation.affirmative('Yes, I have read it.'))
        self.assertTrue(conversation.affirmative('已讀'))
        with patch.object(conversation,'invoke') as invoke:
            with self.assertRaisesRegex(ValueError,'scripted'):
                conversation.respond(self.base,'Yes',actor='scripted_negative_fixture')
            with self.assertRaisesRegex(ValueError,'origin'):
                conversation.respond(self.base,'Yes')
            with self.assertRaisesRegex(ValueError,'Silence'):
                conversation.respond(self.base,'',evidence='human message')
            invoke.assert_not_called()

    def test_negative_reply_keeps_exact_session_waiting(self):
        info = {'completed':True,'agent_messages':['Please read the README and let me know.'],'commands':[]}
        with patch.object(conversation,'invoke',return_value=(info,{},{})) as invoke:
            conversation.respond(self.base,conversation.NEGATIVES['no'],actor='scripted_negative_fixture')
        self.assertEqual(invoke.call_args.args[3],'known-session')
        state = conversation.load_state(self.base)
        self.assertEqual(state['phase'],'awaiting_acknowledgement')
        self.assertEqual(state['turns'][0]['actor'],'scripted_negative_fixture')

    def test_fresh_chat_does_not_inherit_or_replace_acknowledged_session(self):
        self.state['phase']='acknowledged';conversation.save(self.base/'state.json',self.state)
        info = {'completed':True,'agent_messages':[conversation.QUESTION],'commands':[],'session_ids':['new-id']}
        with patch.object(conversation,'invoke',return_value=(info,{},{})) as invoke:
            conversation.reset(self.base)
        self.assertEqual(len(invoke.call_args.args),3)  # No old session passed to the new chat.
        state = conversation.load_state(self.base)
        self.assertEqual(state['session_id'],'known-session')
        self.assertEqual(state['phase'],'acknowledged')
        self.assertTrue(state['turns'][-1]['audit']['different_session'])

    def test_any_response_contract_resumes_verbatim_without_claiming_reading(self):
        for reply in ('Yes', conversation.READ_LATER, 'No', 'Not sure', '繼續', 'Stop this task'):
            with self.subTest(reply=reply):
                self.state.update(phase='awaiting_reply', onboarding_contract=conversation.RESPONSE_CONTRACT)
                conversation.save(self.base/'state.json', self.state)
                info = {'completed':True, 'agent_messages':[], 'commands':[]}
                with patch.object(conversation, 'invoke', return_value=(info,{},{})) as invoke, \
                     patch.object(conversation, 'finish') as finish:
                    conversation.respond(self.base, reply, evidence='actual user reply')
                self.assertEqual(invoke.call_args.args[1], reply)  # Even stop requests reach the model unchanged.
                self.assertEqual(invoke.call_args.args[3], 'known-session')
                state = conversation.load_state(self.base)
                self.assertEqual(state['phase'], 'response_received')
                self.assertEqual(state['turns'][-1]['kind'], 'policy_response')
                self.assertEqual(state['turns'][-1]['reply'], reply)
                finish.assert_called_once()

    def test_any_response_still_requires_real_reply_and_honest_origin(self):
        self.state.update(phase='awaiting_reply', onboarding_contract=conversation.RESPONSE_CONTRACT)
        conversation.save(self.base/'state.json', self.state)
        with patch.object(conversation, 'invoke') as invoke:
            with self.assertRaisesRegex(ValueError, 'Silence'):
                conversation.respond(self.base, '  ', evidence='no answer')
            with self.assertRaisesRegex(ValueError, 'origin'):
                conversation.respond(self.base, 'No')
            with self.assertRaisesRegex(ValueError, 'actor'):
                conversation.respond(self.base, 'No', actor='unknown')
            invoke.assert_not_called()

    def test_scripted_no_can_test_public_resume_but_is_not_human_consent(self):
        self.state.update(phase='awaiting_reply', onboarding_contract=conversation.RESPONSE_CONTRACT,
                          case='coal-scan-payment-lines-v2')
        conversation.save(self.base/'state.json', self.state)
        info = {'completed':True, 'agent_messages':[], 'commands':[]}
        with patch.object(conversation, 'invoke', return_value=(info,{},{})), patch.object(conversation, 'finish'):
            conversation.respond(self.base, 'No', actor='scripted_negative_fixture')
        state = conversation.load_state(self.base)
        self.assertEqual(state['phase'], 'response_received')
        self.assertEqual(state['turns'][-1]['actor'], 'scripted_negative_fixture')
        self.state['case'] = str(self.base.resolve())
        conversation.save(self.base/'state.json', self.state)
        with patch.object(conversation, 'invoke') as invoke:
            with self.assertRaisesRegex(ValueError, 'public cases'):
                conversation.respond(self.base, 'No', actor='scripted_negative_fixture')
            invoke.assert_not_called()

    def test_choices_are_allowed_only_under_new_opening_contract(self):
        info = {'completed':True, 'agent_messages':[conversation.QUESTION+'\n\n'+conversation.REPLY_OPTIONS], 'commands':[]}
        self.assertTrue(conversation.onboarding(info, {}, {}, first=True,
                        contract=conversation.RESPONSE_CONTRACT)['observable_pause_pass'])
        self.assertFalse(conversation.onboarding(info, {}, {}, first=True)['observable_pause_pass'])
        info['agent_messages'][0] += '\nI already read the PDF.'
        self.assertFalse(conversation.onboarding(info, {}, {}, first=True,
                         contract=conversation.RESPONSE_CONTRACT)['observable_pause_pass'])

    def test_new_contract_reset_does_not_carry_response_to_new_chat(self):
        self.state.update(phase='response_received', onboarding_contract=conversation.RESPONSE_CONTRACT)
        conversation.save(self.base/'state.json', self.state)
        info = {'completed':True, 'agent_messages':[conversation.QUESTION+'\n\n'+conversation.REPLY_OPTIONS],
                'commands':[], 'session_ids':['new-id']}
        with patch.object(conversation, 'invoke', return_value=(info,{},{})) as invoke:
            conversation.reset(self.base)
        self.assertEqual(len(invoke.call_args.args), 3)
        state = conversation.load_state(self.base)
        self.assertEqual(state['session_id'], 'known-session')
        self.assertEqual(state['phase'], 'response_received')
        self.assertTrue(state['turns'][-1]['audit']['observable_pause_pass'])
