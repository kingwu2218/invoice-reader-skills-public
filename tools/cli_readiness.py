"""Read-only CLI discovery; no install, login, model call or account inspection."""
import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone

TOOLS = {'codex': ('codex', '--version'), 'gemini-cli': ('gemini', '--version'),
         'grok-build': ('grok', 'version'), 'cursor': ('agent', '--version')}


def probe(tool, versions=False):
    command, flag = TOOLS[tool]
    executable = shutil.which(command)
    result = {'tool': tool, 'status': 'found_on_path' if executable else 'not_found_on_path',
              'version': None, 'authentication': 'not_checked', 'vision': 'not_checked',
              'session_resume': 'not_checked', 'model': 'Unknown'}
    if executable and versions:
        try:
            completed = subprocess.run([executable, flag], capture_output=True, text=True,
                                       encoding='utf-8', errors='replace', timeout=15)
            result['version_exit_code'] = completed.returncode
            if completed.returncode == 0 and completed.stdout.strip():
                result['version'] = completed.stdout.strip()[:300]
            else:
                result['status'] = 'version_probe_failed'
        except (OSError, subprocess.TimeoutExpired):
            result['status'] = 'version_probe_failed'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--versions', action='store_true', help='Run bounded local version commands.')
    args = parser.parse_args()
    print(json.dumps({'checked_utc': datetime.now(timezone.utc).isoformat(),
                      'scope': 'Current PATH only; absence does not prove not installed. No model-readiness claim.',
                      'tools': [probe(tool, args.versions) for tool in TOOLS]}, indent=2))


if __name__ == '__main__':
    main()
