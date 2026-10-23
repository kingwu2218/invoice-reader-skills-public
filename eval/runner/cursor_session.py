"""Prepare isolated Cursor workspaces for the unchanged xAI prompt.

This does not start a chat, pass --model, or copy answers into the model workspace.
Codex opening v9 is not applied. Public paste replies are labelled scripted fixtures.
"""
import hashlib
import json
import sys
from pathlib import Path

RUNNER = Path(__file__).resolve().parent
if str(RUNNER) not in sys.path:
    sys.path.insert(0, str(RUNNER))
import run as baseline

QUESTION = 'Have you read the Readme about the data policy for your model?'
CHOICES = ('Yes, I have read it.', 'No, but I will read it before I upload any confidential data')
SCRIPTED_REPLY = CHOICES[1]
PUBLIC_CASES = ('digit-boundary-v1', 'cash-memo-classification-v1', 'coal-ocr-payment', 'coal-ocr-energy')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observe_opening(messages):
    """Record the Cursor question, choices, and Yes-only wording. Text cannot prove a pause."""
    text = '\n'.join(message.strip() for message in messages if message and message.strip())
    lowered = text.casefold()
    yes_only = ('only a yes' in lowered or 'must answer yes' in lowered or 'only yes' in lowered)
    return {'grader': 'cursor-opening-observation-v1', 'not_codex_v9': True,
            'exact_question_count': text.count(QUESTION),
            'both_choices_present': all(choice in text for choice in CHOICES),
            'yes_only_language_observed': yes_only,
            'pause': 'not_attested_by_text'}


def _raw_reference(path):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    return 'configured' if isinstance(payload, dict) and 'raw_tables' in payload else 'not_configured'


def prepare(batch, cases=PUBLIC_CASES, python_executable=''):
    batch = Path(batch)
    if batch.exists():
        raise ValueError('Refusing to overwrite an existing Cursor batch.')
    if any(case not in PUBLIC_CASES for case in cases):
        raise ValueError('Cursor baseline preparation is limited to the named public cases.')
    entry = next(item for item in baseline.skillsets.load_registry() if item['name'] == 'invoice-reader-xai-cursor')
    package = baseline.skillsets.package_path(entry)
    if not package.exists():
        raise ValueError('Build the Cursor package before preparing workspaces.')
    adapter = baseline.module(baseline.REPO / 'adapters' / 'cursor' / 'eval_adapter.py')
    batch.mkdir(parents=True)
    case_records = []
    for case in cases:
        work = batch / case / 'workspace'
        run_dir = batch / case / 'run-1'
        _, prompt, meta = baseline.prepare(entry, case, run_dir, work)
        if (work / 'expected.json').exists() or (work / 'PASTE-REPLY.txt').exists():
            raise ValueError('Scoring material leaked into the model workspace.')
        paste = prompt.rstrip()
        if python_executable:
            paste += (f' An existing Python interpreter is {python_executable}. Use it directly for the skill scripts '
                      'instead of provisioning another environment with uv. This is evaluator-provided environment '
                      'information, not document content.')
        argv = adapter.command(adapter.COMMAND, 'do-not-pass-this-model', paste)
        if '--model' in argv or any('effort' in part.casefold() for part in argv[:-1]):
            raise ValueError('Cursor invocation included a model or effort override.')
        (run_dir / 'PASTE-OPENING.txt').write_text(paste + '\n', encoding='utf-8')
        (run_dir / 'PASTE-REPLY.txt').write_text(
            'SCRIPTED PUBLIC FIXTURE, NOT A HUMAN CONFIRMATION:\n' + SCRIPTED_REPLY + '\n', encoding='utf-8')
        (run_dir / 'prompt.txt').write_text(prompt + '\n', encoding='utf-8')
        meta.update(prepared_only=True, valid=False, extraction_status='not_run',
                    model_requested='Grok 4.7', model_reported='Unknown', effort_requested='High',
                    effort_reported='Unknown', provider='Unknown', raw_reference=_raw_reference(run_dir / 'expected.json'),
                    invocation=argv[:-1] + ['<prompt>'])
        (run_dir / 'meta.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
        case_records.append({'case': case, 'raw_reference': meta['raw_reference'],
                             'artifact_hash': meta['artifact_hash'], 'dataset_hash': meta['dataset_hash']})
    lock = {'package': entry['name'], 'family': 'xai', 'family_prompt_unchanged': True,
            'package_hash': baseline.skillsets.tree_hash(package),
            'family_source_hash': baseline.skillsets.tree_hash(baseline.REPO / 'skills' / 'xai'),
            'adapter_hash': baseline.skillsets.tree_hash(baseline.REPO / 'adapters' / 'cursor'),
            'codex_opening_v9_hash': file_hash(baseline.REPO / 'eval' / 'runner' / 'opening_v9.py'),
            'cases': case_records}
    (batch / 'lock.json').write_text(json.dumps(lock, indent=2), encoding='utf-8')
    return lock


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', type=Path)
    parser.add_argument('--cases', nargs='+', default=list(PUBLIC_CASES))
    parser.add_argument('--python', default='', help='Existing interpreter path recorded in the paste prompt.')
    args = parser.parse_args(argv)
    print(json.dumps(prepare(args.batch, args.cases, args.python), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
