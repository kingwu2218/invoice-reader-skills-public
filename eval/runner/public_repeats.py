"""Freeze, run and score fresh Codex chats on PUBLIC fixtures only.

Each numbered trial runs once. Scripted read-later replies are test data, never
human consent. Private scenarios must use the separate human-reply workflow.
"""
import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

import conversation
import score


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def fixture_hash(case):
    if not re.fullmatch(r'[a-z0-9-]+', case):
        raise ValueError('Only named public fixtures are permitted.')
    source, expected, custom, _ = conversation.baseline.expectation(case)
    if not source.resolve().is_relative_to((conversation.baseline.REPO/'eval').resolve()):
        raise ValueError('Source is outside the public evaluation tree.')
    if not any(source.resolve().is_relative_to((conversation.baseline.REPO/'eval'/p).resolve())
               for p in ('fixtures', 'cases')):
        raise ValueError('Source must be in public fixtures or cases, never private runs.')
    return hashlib.sha256(source.read_bytes() + custom.encode() +
                          json.dumps(expected, sort_keys=True, default=str).encode()).hexdigest()


def package_hash():
    entry = next(e for e in conversation.baseline.skillsets.load_registry()
                 if e['name'] == 'invoice-reader-openai')
    return conversation.baseline.skillsets.tree_hash(conversation.baseline.skillsets.package_path(entry))


def plan(batch, cases, repeats, model, provider, python, transport):
    if repeats < 1 or not cases or len(cases) != len(set(cases)):
        raise ValueError('Use distinct cases and a positive repeat count.')
    if not model.strip() or not provider.strip() or not Path(python).is_file():
        raise ValueError('Explicit benchmark model, provider and existing Python are required.')
    hashes = {case: fixture_hash(case) for case in cases}
    trials = [{'id': i+1, 'case': case, 'repeat': n}
              for i, (case, n) in enumerate((c, n) for c in cases for n in range(1, repeats+1))]
    batch.mkdir(parents=True, exist_ok=False)
    write_new(batch/'plan.json', {
        'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'artifact_hash': package_hash(), 'fixture_hashes': hashes, 'trials': trials,
        'model_requested': model, 'provider': provider, 'python': str(Path(python).resolve()),
        'transport': transport, 'reply_actor': 'scripted_negative_fixture',
        'reply': conversation.READ_LATER,
        'scope': 'Known public fixtures; fresh chat per trial; no private data or automatic retries.'})
    (batch/'plan.sha256').write_text(hashlib.sha256((batch/'plan.json').read_bytes()).hexdigest())
    return trials


def load_plan(batch):
    if hashlib.sha256((batch/'plan.json').read_bytes()).hexdigest() != (batch/'plan.sha256').read_text():
        raise ValueError('Frozen plan changed.')
    data = json.loads((batch/'plan.json').read_text())
    if data['artifact_hash'] != package_hash():
        raise ValueError('Package changed since the plan was frozen.')
    for case, digest in data['fixture_hashes'].items():
        if fixture_hash(case) != digest:
            raise ValueError('Public fixture changed since the plan was frozen.')
    return data


def run_trial(batch, number):
    data = load_plan(batch)
    trial = next((t for t in data['trials'] if t['id'] == number), None)
    if trial is None:
        raise ValueError('Unknown trial number.')
    folder = batch/f'trial-{number:03}'
    folder.mkdir(exist_ok=False)  # Atomic reservation: failed attempts cannot be overwritten.
    outcome = {**trial, 'status': 'incomplete'}
    try:
        with (folder/'runner.log').open('w', encoding='utf-8') as log, redirect_stdout(log):
            base = conversation.start(trial['case'], data['model_requested'], data['provider'],
                                      data['python'], transport=data['transport'])
            outcome['conversation'] = str(base)
            write_new(folder/'conversation.json', {'path': str(base)})
            state = conversation.load_state(base)
            outcome['session_id'] = state['session_id']
            outcome['opening'] = state['turns'][0]['audit']
            # An opening failure stays visible; never continue observed document work.
            if (state['phase'] != 'awaiting_reply' or not outcome['opening']['workspace_unchanged']
                    or outcome['opening']['commands_requiring_review']):
                raise ValueError('Opening requires trace review before a scripted continuation.')
            complete_trial(batch, data, outcome, base)
    except Exception as error:
        outcome['error'] = f'{type(error).__name__}: {error}'
    finally:
        write_new(folder/'outcome.json', outcome)
    return outcome


def complete_trial(batch, data, outcome, base):
    conversation.respond(base, data['reply'], actor='scripted_negative_fixture')
    result = conversation.report(base)
    outcome['reply_audit'] = result['onboarding'][-1]['audit']
    source = base/'extractions'/outcome['case']/'run-1'
    target = batch/'extractions'/outcome['case']/f"run-{outcome['repeat']}"
    target.mkdir(parents=True, exist_ok=False)
    for name in ('meta.json', 'expected.json', 'custom.md', 'output.xlsx', 'raw-extraction.json'):
        if (source/name).exists():
            shutil.copyfile(source/name, target/name)
    outcome['status'] = 'recorded'


def resume_reviewed(batch, number):
    """Continue the same waiting session after a trace review; never replace a run."""
    data = load_plan(batch)
    folder = batch/f'trial-{number:03}'
    original = json.loads((folder/'outcome.json').read_text())
    base = Path(original['conversation'])
    state = conversation.load_state(base)
    if original['status'] != 'incomplete' or state['phase'] != 'awaiting_reply':
        raise ValueError('Only an incomplete trial still awaiting its first reply can resume.')
    if state['session_id'] != original['session_id'] or state['case'] != original['case']:
        raise ValueError('Session or case changed.')
    turn = base/'turns/001-start'
    review = json.loads((turn/'trace-review.json').read_text())
    digest = conversation.image_inputs.digest
    if (review.get('stream_sha256') != digest(turn/'stream.jsonl') or
            review.get('snapshots_sha256') != digest(turn/'snapshots.json') or
            review.get('no_document_work_observed') is not True or
            not review.get('reviewer') or not review.get('reason')):
        raise ValueError('A hash-bound maintainer review of the opening is required.')
    write_new(folder/'continuation-start.json', {'session_id': state['session_id'], 'review': review})
    outcome = {**original, 'status': 'incomplete', 'maintainer_review': review}
    outcome.pop('error', None)
    try:
        with (folder/'continuation.log').open('x', encoding='utf-8') as log, redirect_stdout(log):
            complete_trial(batch, data, outcome, base)
    except Exception as error:
        outcome['error'] = f'{type(error).__name__}: {error}'
    finally:
        write_new(folder/'continuation-outcome.json', outcome)
    return outcome


def report(batch):
    data = load_plan(batch)
    outcomes = []
    for trial in data['trials']:
        folder = batch/f"trial-{trial['id']:03}"
        path = folder/'outcome.json'
        outcome = json.loads(path.read_text()) if path.exists() else {**trial, 'status': 'not_recorded'}
        if (folder/'continuation-outcome.json').exists():
            outcome = {**json.loads((folder/'continuation-outcome.json').read_text()), 'initial_attempt': outcome}
        outcomes.append(outcome)
    scored = score.score_batch(batch/'extractions') if list((batch/'extractions').glob('*/run-*/meta.json')) else None
    result = {'planned_trials': len(outcomes), 'recorded_trials': sum(o['status']=='recorded' for o in outcomes),
              'trials': outcomes, 'extraction': scored,
              'artifact_hash': data['artifact_hash'], 'model_requested': data['model_requested'],
              'provider': data['provider'], 'reply_actor': data['reply_actor']}
    conversation.save(batch/'report.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('plan'); p.add_argument('batch', type=Path)
    p.add_argument('--cases', nargs='+', required=True); p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--model', required=True); p.add_argument('--provider', required=True)
    p.add_argument('--python', required=True); p.add_argument('--transport', choices=('default','https'), default='default')
    p = sub.add_parser('run'); p.add_argument('batch', type=Path); p.add_argument('--trial', type=int, required=True)
    p = sub.add_parser('resume-reviewed'); p.add_argument('batch', type=Path); p.add_argument('--trial', type=int, required=True)
    p = sub.add_parser('report'); p.add_argument('batch', type=Path)
    args = parser.parse_args()
    if args.action == 'plan':
        result = plan(args.batch, args.cases, args.repeats, args.model, args.provider, args.python, args.transport)
    elif args.action == 'run':
        result = run_trial(args.batch, args.trial)
    elif args.action == 'resume-reviewed':
        result = resume_reviewed(args.batch, args.trial)
    else:
        result = report(args.batch)
        result = {k:v for k,v in result.items() if k not in ('trials','extraction')}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
