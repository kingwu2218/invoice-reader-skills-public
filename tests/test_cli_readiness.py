import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cli_readiness', Path(__file__).resolve().parents[1]/'tools/cli_readiness.py')
readiness = importlib.util.module_from_spec(spec); spec.loader.exec_module(readiness)


class CliReadiness(unittest.TestCase):
    def test_missing_executable_and_default_discovery_never_launch(self):
        with patch.object(readiness.shutil, 'which', return_value=None), patch.object(readiness.subprocess, 'run') as run:
            result = readiness.probe('gemini-cli', versions=True)
            self.assertEqual(result['status'], 'not_found_on_path'); run.assert_not_called()
        with patch.object(readiness.shutil, 'which', return_value='codex'), patch.object(readiness.subprocess, 'run') as run:
            result = readiness.probe('codex')
            self.assertIsNone(result['version']); run.assert_not_called()

    def test_version_is_bounded_and_never_model_or_authentication_evidence(self):
        for response in (SimpleNamespace(returncode=0, stdout='grok test-version'),
                         SimpleNamespace(returncode=1, stdout=''), subprocess.TimeoutExpired('grok', 15)):
            with patch.object(readiness.shutil, 'which', return_value='grok'), \
                    patch.object(readiness.subprocess, 'run') as run:
                if isinstance(response, Exception): run.side_effect = response
                else: run.return_value = response
                result = readiness.probe('grok-build', versions=True)
            self.assertEqual(run.call_args.args[0], ['grok', 'version'])
            self.assertEqual(run.call_args.kwargs['timeout'], 15)
            self.assertEqual(result['model'], 'Unknown')
            self.assertEqual(result['authentication'], 'not_checked')
