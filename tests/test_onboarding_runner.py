"""The single-turn benchmark must not bypass the owner's per-chat question."""
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'eval/runner'))
spec = importlib.util.spec_from_file_location('onboarding_runner', ROOT/'eval/runner/run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class OnboardingRunner(unittest.TestCase):
    def test_live_launch_stops_before_preparation_or_model_call(self):
        for package in ('invoice-reader-openai', 'invoice-reader-anthropic'):
            for image_flags in ([], ['--attach-page-images']):
                with self.subTest(package=package, images=bool(image_flags)):
                    argv = ['run.py', '--package', package, '--model', 'test-model', *image_flags]
                    error = io.StringIO()
                    with patch.object(sys, 'argv', argv), patch.object(runner, 'prepare') as prepare, \
                            patch.object(runner.subprocess, 'run') as invoke, redirect_stderr(error):
                        with self.assertRaises(SystemExit) as stopped:
                            runner.main()
                    self.assertEqual(stopped.exception.code, 2)
                    prepare.assert_not_called()
                    invoke.assert_not_called()
                    self.assertIn('real user answer', error.getvalue())
