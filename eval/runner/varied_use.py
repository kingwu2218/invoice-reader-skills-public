"""Two fresh public multi-file chats, same sources with different user purposes.

Freezes source, answer, package and harness bytes before execution. A failed
action consumes its attempt; reports never substitute a retry for that evidence.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import shutil
import subprocess

import first_use as shared

REPO = shared.REPO
VERSION = 'varied-use-v1'
FILES = ('batch-invoices.pdf', 'batch-support.pdf')
PURPOSES = {
    'payment': shared.PURPOSES['payment'],
    'quality': 'I need to compare certificate results. Use the column names "Energy Level of Coal", "Sulphur" and "Ash content". Keep every sample, its printed sample label and unit; do not convert units. Treat all requested fields as optional; leave missing information blank.',
}
LABELS = {'payment': ['Invoice number', 'Payment due date'],
          'quality': ['Energy Level of Coal', 'Sulphur', 'Ash content']}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def plan(batch, workspace_root, model, provider, transport):
    workspace_root = workspace_root.resolve()
    if workspace_root.is_relative_to(REPO.resolve()) or REPO.resolve().is_relative_to(workspace_root):
        raise ValueError('Use new workspaces outside the repository and its ancestors.')
    if batch.exists() or workspace_root.exists(): raise ValueError('Batch and workspace must both be new.')
    if not model.strip() or not provider.strip() or transport not in ('default', 'https'):
        raise ValueError('Explicit benchmark model, provider and valid transport required.')
    entry, package = shared.package()
    fixtures = [REPO/'eval/fixtures'/name for name in FILES]
    fixtures += [REPO/'eval/workflows'/VERSION/(purpose+'.json') for purpose in PURPOSES]
    fixtures += [REPO/'eval/workflows'/VERSION/'README.md']
    harness = sorted((REPO/'eval/runner').glob('*.py')) + [REPO/'adapters/codex/eval_adapter.py',
        REPO/'tools/skillsets.py', REPO/'eval/tools/build_varied_use.py']
    harness += sorted((REPO/'core/scripts').rglob('*.py')) + sorted((REPO/'core/scripts/data').glob('*.toml'))
    hashes = {p.relative_to(REPO).as_posix(): shared.digest(p) for p in fixtures}
    code = {p.relative_to(REPO).as_posix(): shared.digest(p) for p in harness}
    batch.mkdir(parents=True); workspace_root.mkdir(parents=True)
    trials = []
    for number, purpose in enumerate(PURPOSES, 1):
        work = workspace_root/f'chat-{number}'; work.mkdir()
        shutil.copytree(package, work/'.agents/skills/invoice-reader-openai')
        for name in FILES: shutil.copyfile(REPO/'eval/fixtures'/name, work/name)
        folder = batch/f'trial-{number}'; folder.mkdir()
        shutil.copyfile(REPO/'eval/workflows'/VERSION/(purpose+'.json'), folder/'expected.json')
        prompt = ('Use $invoice-reader-openai to read batch-invoices.pdf and batch-support.pdf. '+PURPOSES[purpose]+
                  ' Create custom.md for these requirements and save output.xlsx. '
                  'I do not need sales/purchase direction, so proceed without a company profile. '
                  'Keep the standard document sheets too. Please handle the setup and processing for me.')
        trials.append(dict(id=number, purpose=purpose, workspace=str(work), prompt=prompt,
                           expected_sha256=shared.digest(folder/'expected.json'), initial_snapshot=shared.conversation.snapshot(work)))
    for name in code:
        dest = batch/'frozen-harness'/name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO/name, dest)
    data = dict(protocol=VERSION, opening_contract=shared.OPENING_GRADER.VERSION,
        opening_grader_sha256=shared.digest(Path(shared.OPENING_GRADER.__file__)),
        opening_dependency_hashes=shared.opening_dependencies(), package_version=entry['version'],
        artifact_hash=shared.conversation.baseline.skillsets.tree_hash(package), fixture_hashes=hashes,
        harness_hashes=code, model_requested=model, provider=provider, transport=transport, trials=trials,
        reply_actor='scripted_negative_fixture', reply=shared.conversation.READ_LATER,
        tool_version=subprocess.run(['codex', '--version'], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip(),
        scope='New public synthetic layouts and authored values after 0.3.16 prompt/package freeze. Two fresh CLI sessions, one per purpose; same two files, three pages, four documents. No prior examples, settings, profile or answer files supplied. Existing host tooling/auth and global instructions remain available.')
    shared.save_new(batch/'plan.json', data)
    (batch/'plan.sha256').write_text(shared.digest(batch/'plan.json'), encoding='utf-8')
    return dict(trials=len(trials), plan_sha256=shared.digest(batch/'plan.json'))


def load(batch, number):
    if shared.digest(batch/'plan.json') != (batch/'plan.sha256').read_text(encoding='utf-8'):
        raise ValueError('Frozen plan changed.')
    data = read(batch/'plan.json')
    for category in ('fixture_hashes', 'harness_hashes'):
        for name, value in data[category].items():
            if shared.digest(REPO/name) != value: raise ValueError('Frozen '+category+' changed: '+name)
    if shared.conversation.baseline.skillsets.tree_hash(shared.package()[1]) != data['artifact_hash']:
        raise ValueError('Frozen package changed.')
    trial = next(t for t in data['trials'] if t['id'] == number)
    folder = batch/f'trial-{number}'
    if shared.digest(folder/'expected.json') != trial['expected_sha256']: raise ValueError('Frozen trial reference changed.')
    return data, trial, folder


def execute(batch, number, action):
    if action not in ('start', 'reply'): raise ValueError('Unknown action.')
    data, trial, folder = load(batch, number)
    work = Path(trial['workspace'])
    shared.save_new(folder/(action+'-attempt.json'), dict(action=action, protocol=VERSION))
    result = dict(action=action, status='incomplete', model_reported='Unknown')
    try:
        if shared.conversation.baseline.skillsets.tree_hash(work/'.agents/skills/invoice-reader-openai') != data['artifact_hash']:
            raise ValueError('Installed package changed.')
        if any(shared.digest(work/name) != data['fixture_hashes']['eval/fixtures/'+name] for name in FILES):
            raise ValueError('Workspace source changed.')
        session = None
        if action == 'start':
            if shared.conversation.snapshot(work) != trial['initial_snapshot']: raise ValueError('Initial workspace changed.')
            prompt = trial['prompt']
        else:
            initial = read(folder/'start-result.json'); session = initial['session_id']
            audit = initial['opening_v9']
            if not all(audit.get(k) for k in ('observed_pause', 'exact_question_once', 'both_exact_choices_once')):
                raise ValueError('Opening needs trace review; no automatic reply sent.')
            prompt = data['reply']
        before_manifests = {str(p.resolve()): shared.digest(p) for p in (work/'invoice-reader-work').glob('*/manifest.json')}
        state = dict(workspace=str(work), model_requested=data['model_requested'], codex_transport=data['transport'], execution_timeout_seconds=1200)
        info, before, after = shared.conversation.invoke(state, prompt, folder/action, session)
        result.update(status='recorded', completed=info['completed'], exit_code=info['exit_code'],
            elapsed_seconds=info['elapsed_seconds'], session_ids=info['session_ids'],
            model_reported=', '.join(info['models_reported_by_cli']) or 'Unknown',
            policy_question_count=sum(m.count(shared.conversation.QUESTION) for m in info['agent_messages']))
        if len(info['session_ids']) == 1:
            result['session_id'] = info['session_ids'][0]
            result['image_evidence'] = shared.capture_trace(result['session_id'], folder/action)
        if action == 'start':
            result['opening_v9'] = shared.OPENING_GRADER.audit(info, before, after, work,
                shared.OPENING_GRADER.host_evidence(folder/action/'session-trace.jsonl', result.get('session_id')))
        else:
            result['same_session'] = info['session_ids'] == [session]
            result['reply_actor'] = data['reply_actor']
            result['extraction'] = shared.evaluate(work, folder, action, before_manifests)
        result['package_unchanged'] = shared.conversation.baseline.skillsets.tree_hash(work/'.agents/skills/invoice-reader-openai') == data['artifact_hash']
        result['sources_unchanged'] = all(shared.digest(work/name) == data['fixture_hashes']['eval/fixtures/'+name] for name in FILES)
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    shared.save_new(folder/(action+'-result.json'), result)
    return result


def report(batch, destination):
    if destination.suffix != '.json' or destination.exists() or destination.with_suffix('.csv').exists():
        raise ValueError('Use new .json and .csv report destinations.')
    data = read(batch/'plan.json'); rows = []
    for trial in data['trials']:
        _, _, folder = load(batch, trial['id'])
        start = read(folder/'start-result.json') if (folder/'start-result.json').exists() else {}
        path = folder/'reply-result.json'
        r = read(path) if path.exists() else {}
        e = r.get('extraction', {}); fields = e.get('custom_fields', [])
        coverage = e.get('raw_coverage', [])
        coverage_ok = len(coverage) == len(FILES) and {c['file'] for c in coverage} == set(FILES) and all(c['status'] == 'Processed' for c in coverage)
        custom_ok = [f['label'] for f in fields] == LABELS[trial['purpose']] and all(not f['required'] for f in fields)
        if trial['purpose'] == 'quality': custom_ok = custom_ok and all(f['values'] == 'many' for f in fields[:2])
        complete = all((r.get('completed'), r.get('same_session'), r.get('package_unchanged'), r.get('sources_unchanged'),
                        e.get('output_present'), e.get('custom_created'), coverage_ok, custom_ok, r.get('policy_question_count') == 0))
        row = dict(trial=trial['id'], purpose=trial['purpose'], core_delivery_complete=complete,
            opening_pass=start.get('opening_v9', {}).get('automatic_pass', False), coverage_matches_request=coverage_ok,
            custom_matches_request=custom_ok, policy_questions_after_reply=r.get('policy_question_count'),
            model_reported=r.get('model_reported', 'Unknown'), elapsed_seconds=r.get('elapsed_seconds'),
            result_sha256=shared.digest(path) if path.exists() else None, workbook_sha256=e.get('workbook_sha256'),
            trace_sha256=r.get('image_evidence', {}).get('trace_sha256'),
            tool_returned_images=r.get('image_evidence', {}).get('returned_images'),
            package_unchanged=r.get('package_unchanged'), sources_unchanged=r.get('sources_unchanged'))
        for layer in ('raw', 'workbook'):
            layer_data = e.get(layer, {})
            for key in ('correct', 'denominator', 'correct_blank', 'cells', 'tables', 'checks'):
                row[layer+'_'+key] = layer_data.get(key)
            score_path = folder/'reply-artifacts'/(layer+'-score.json')
            if score_path.exists(): row[layer+'_metrics'] = shared.score.metrics(read(score_path))
        if r.get('error'): row['error_type'] = r['error'].split(':', 1)[0]
        rows.append(row)
    totals = {}
    for layer in ('raw', 'workbook'):
        scored = [r for r in rows if r[layer+'_denominator'] is not None]
        cells = Counter()
        for r in scored: cells.update(r[layer+'_cells'])
        totals[layer] = dict(scored_chats=len(scored), cells=dict(cells), **{
            key: sum(r[layer+'_'+key] for r in scored) if scored else None for key in ('correct', 'denominator', 'correct_blank')})
    result = dict(protocol=VERSION, package_version=data['package_version'], package_sha256=data['artifact_hash'],
        requested_model=data['model_requested'], provider=data['provider'], tool_version=data['tool_version'],
        opening_contract=data['opening_contract'], opening_grader_sha256=data['opening_grader_sha256'],
        plan_sha256=shared.digest(batch/'plan.json'), fixture_hashes=data['fixture_hashes'], harness_hashes=data['harness_hashes'],
        planned_chats=len(rows), completed_chats=sum(r['core_delivery_complete'] for r in rows),
        opening_passes=sum(r['opening_pass'] for r in rows), rows=rows, totals=totals, scope=data['scope'],
        limitations=['Two synthetic purpose trials, not a stability or production accuracy estimate.',
            'Blank cells excluded; printed status/structure cells included, so inspect per-table results.',
            'Requested model is not verified runtime identity. Image return is not proof of attention.',
            'No private handwriting, rotated/poor scans, OCR-text conflict, or password-protected documents in this batch.'])
    shared.save_new(destination, result)
    columns = [k for k in rows[0] if not k.endswith(('_tables', '_cells', '_checks', '_metrics'))]
    with destination.with_suffix('.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
    return dict(completed_chats=result['completed_chats'], opening_passes=result['opening_passes'], totals=totals)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='action', required=True)
    s = sub.add_parser('plan'); s.add_argument('batch', type=Path); s.add_argument('--workspace-root', type=Path, required=True)
    s.add_argument('--model', required=True); s.add_argument('--provider', required=True); s.add_argument('--transport', choices=('default', 'https'), default='https')
    for action in ('start', 'reply'):
        s = sub.add_parser(action); s.add_argument('batch', type=Path); s.add_argument('--trial', type=int, required=True)
    s = sub.add_parser('report'); s.add_argument('batch', type=Path); s.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.action == 'plan': result = plan(a.batch, a.workspace_root, a.model, a.provider, a.transport)
    elif a.action == 'report': result = report(a.batch, a.out)
    else: result = execute(a.batch, a.trial, a.action)
    print(json.dumps(result, indent=2))
