import json
from pathlib import Path
import shutil
from unittest.mock import patch

import test_varied_use as previous
import varied_use
import varied_use_v2 as v2
ROOT = previous.ROOT


class VariedV2(previous.VariedPlan):
    """Run existing isolation/tamper/failed-attempt checks against the v2 engine too."""
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT/'eval/workflows/varied-use-v2', self.repo/'eval/workflows/varied-use-v2')
        shutil.copyfile(ROOT/'eval/runner/varied_use_v2.py', self.repo/'eval/runner/varied_use_v2.py')
        context = patch.object(v2.engine, 'REPO', self.repo); context.start(); self.addCleanup(context.stop)

    def plan(self):
        v2.plan(self.batch, self.work, 'selected', 'provider', 'https')

    def test_v2_reference_protocol_and_archived_entry_are_frozen(self):
        self.plan(); data, trial, folder = v2.load(self.batch, 1)
        self.assertEqual(data['protocol'], 'varied-use-v2')
        self.assertEqual(varied_use.VERSION, 'varied-use-v1')
        self.assertEqual(data['opening_contract'], 'codex-opening-v9')
        self.assertEqual(json.loads((folder/'expected.json').read_text()),
                         json.loads((self.repo/'eval/workflows/varied-use-v2/payment.json').read_text()))
        self.assertIn('eval/runner/varied_use_v2.py', data['harness_hashes'])
        self.assertTrue((self.batch/'frozen-harness/eval/runner/varied_use_v2.py').exists())
        self.assertFalse(any('workflows/varied-use-v1' in name for name in data['fixture_hashes']))
        result = v2.report(self.batch, self.batch/'v2.json')
        self.assertEqual(result['completed_chats'], 0)
        self.assertEqual(json.loads((self.batch/'v2.json').read_text())['protocol'], 'varied-use-v2')
        path = self.repo/'eval/workflows/varied-use-v2/payment.json'; path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'fixture_hashes'): v2.load(self.batch, 1)

    def test_v2_rejects_v1_without_reserving_an_attempt(self):
        varied_use.plan(self.batch, self.work, 'selected', 'provider', 'https')
        with self.assertRaisesRegex(ValueError, 'matching versioned runner'): v2.execute(self.batch, 1, 'start')
        self.assertFalse((self.batch/'trial-1/start-attempt.json').exists())

    def test_v2_failed_action_retains_correct_protocol_and_cannot_retry(self):
        self.plan()
        with patch.object(v2.engine.shared.conversation, 'invoke', side_effect=RuntimeError('transport failed')) as invoke:
            self.assertEqual(v2.execute(self.batch, 1, 'start')['status'], 'incomplete')
            self.assertEqual(json.loads((self.batch/'trial-1/start-attempt.json').read_text())['protocol'], 'varied-use-v2')
            with self.assertRaises(FileExistsError): v2.execute(self.batch, 1, 'start')
            self.assertEqual(invoke.call_count, 1)
