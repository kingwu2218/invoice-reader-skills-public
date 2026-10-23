import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'eval/runner'))
import public_repeats as runner


class PublicRepeats(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.batch = self.root/'batch'

    def prepare(self):
        with patch.object(runner, 'package_hash', return_value='package'):
            runner.plan(self.batch, ['digit-boundary-v1'], 3, 'chosen-model', 'recorded-route', sys.executable, 'default')

    def test_private_names_rejected_without_reading_or_creating_batch(self):
        for case in ('../runs/private', str(self.root/'private'), 'private/case'):
            with patch.object(runner.conversation.baseline, 'expectation') as lookup:
                with self.assertRaises(ValueError): runner.fixture_hash(case)
                lookup.assert_not_called()
        with patch.object(runner.conversation.baseline, 'expectation',
                          return_value=(ROOT/'eval/runs/private.pdf', {}, '', {})):
            with self.assertRaises(ValueError): runner.fixture_hash('named-private')

    def test_plan_tampering_and_package_drift_stop_before_execution(self):
        self.prepare()
        with patch.object(runner, 'package_hash', return_value='changed'), patch.object(runner.conversation, 'start') as start:
            with self.assertRaisesRegex(ValueError, 'Package changed'): runner.run_trial(self.batch, 1)
            start.assert_not_called()
        with (self.batch/'plan.json').open('a') as stream: stream.write(' ')
        with self.assertRaisesRegex(ValueError, 'Frozen plan changed'): runner.load_plan(self.batch)

    def test_fixture_drift_and_duplicate_plans_rejected(self):
        self.prepare()
        with patch.object(runner, 'package_hash', return_value='package'), patch.object(runner, 'fixture_hash', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'fixture changed'): runner.load_plan(self.batch)
        with self.assertRaises(ValueError):
            runner.plan(self.root/'other', ['digit-boundary-v1']*2, 3, 'm', 'p', sys.executable, 'default')

    def test_failed_attempt_is_recorded_and_cannot_be_replaced(self):
        self.prepare()
        with patch.object(runner, 'package_hash', return_value='package'), \
                patch.object(runner.conversation, 'start', side_effect=RuntimeError('transport failure')):
            result = runner.run_trial(self.batch, 1)
            self.assertEqual(result['status'], 'incomplete')
            with self.assertRaises(FileExistsError): runner.run_trial(self.batch, 1)
            report = runner.report(self.batch)
        self.assertEqual(report['planned_trials'], 3)
        self.assertEqual(report['recorded_trials'], 0)
        self.assertIsNone(report['extraction'])
        self.assertIn('transport failure', report['trials'][0]['error'])

    def test_suspicious_opening_cannot_get_scripted_reply(self):
        self.prepare()
        audit = {'workspace_unchanged': True, 'commands_requiring_review': ['read source.pdf']}
        state = {'session_id': 'fresh', 'phase': 'awaiting_reply', 'turns': [{'audit': audit}]}
        with patch.object(runner, 'package_hash', return_value='package'), \
                patch.object(runner.conversation, 'start', return_value=self.root/'conversation'), \
                patch.object(runner.conversation, 'load_state', return_value=state), \
                patch.object(runner.conversation, 'respond') as reply:
            result = runner.run_trial(self.batch, 1)
        reply.assert_not_called(); self.assertEqual(result['status'], 'incomplete')

    def test_public_reply_label_and_exact_session_are_preserved(self):
        self.prepare()
        base = self.root/'conversation'
        source = base/'extractions/digit-boundary-v1/run-1'; source.mkdir(parents=True)
        (source/'meta.json').write_text('{}')
        audit = {'workspace_unchanged': True, 'commands_requiring_review': []}
        state = {'session_id': 'fresh', 'phase': 'awaiting_reply', 'turns': [{'audit': audit}]}
        with patch.object(runner, 'package_hash', return_value='package'), \
                patch.object(runner.conversation, 'start', return_value=base), \
                patch.object(runner.conversation, 'load_state', return_value=state), \
                patch.object(runner.conversation, 'respond') as reply, \
                patch.object(runner.conversation, 'report', return_value={'onboarding': [{'audit': {}}]}):
            result = runner.run_trial(self.batch, 1)
        reply.assert_called_once_with(base, runner.conversation.READ_LATER, actor='scripted_negative_fixture')
        self.assertEqual(result['session_id'], 'fresh')
        self.assertEqual(result['status'], 'recorded')

    def test_reviewed_resume_rejects_stale_evidence_and_preserves_initial_failure(self):
        self.prepare()
        folder = self.batch/'trial-001'; folder.mkdir()
        base = self.root/'conversation'; turn = base/'turns/001-start'; turn.mkdir(parents=True)
        (turn/'stream.jsonl').write_text('trace'); (turn/'snapshots.json').write_text('{}')
        initial = {'id': 1, 'case': 'digit-boundary-v1', 'repeat': 1, 'status': 'incomplete',
                   'conversation': str(base), 'session_id': 'same', 'error': 'requires review'}
        runner.write_new(folder/'outcome.json', initial)
        review = {'reviewer': 'maintainer', 'reason': 'instruction reads only',
                  'no_document_work_observed': True, 'stream_sha256': 'stale',
                  'snapshots_sha256': runner.conversation.image_inputs.digest(turn/'snapshots.json')}
        (turn/'trace-review.json').write_text(json.dumps(review))
        state = {'session_id': 'same', 'case': 'digit-boundary-v1', 'phase': 'awaiting_reply'}
        with patch.object(runner, 'package_hash', return_value='package'), \
                patch.object(runner.conversation, 'load_state', return_value=state), \
                patch.object(runner, 'complete_trial') as complete:
            with self.assertRaisesRegex(ValueError, 'hash-bound'): runner.resume_reviewed(self.batch, 1)
            complete.assert_not_called()
            review['stream_sha256'] = runner.conversation.image_inputs.digest(turn/'stream.jsonl')
            (turn/'trace-review.json').write_text(json.dumps(review))
            runner.resume_reviewed(self.batch, 1)
            with self.assertRaises(FileExistsError): runner.resume_reviewed(self.batch, 1)
        self.assertEqual(json.loads((folder/'outcome.json').read_text()), initial)
