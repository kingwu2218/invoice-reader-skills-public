"""Run prepared public cases in fresh Claude Code chats, one persisted session per case.

run.py --prepare-only freezes each workspace and keeps its record. This runner never edits
that record: it verifies the workspace is untouched, then writes execution evidence to a
separate batch. Turn 1 invokes the skill by name without page images. When the policy
question is asked, the reply is a labelled public test fixture, never a human answer,
reading or consent. Answers stay in the results folder, outside the model workspace.

  python eval/runner/claude_session.py run PREPARED_BATCH --cases A B --model ID --provider ROUTE
  python eval/runner/claude_session.py say EXECUTION_RUN --text-file FILE --actor ACTOR --origin TEXT
  python eval/runner/claude_session.py report EXECUTION_BATCH
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from uuid import uuid4

import run as baseline
import image_inputs
import conversation
import holdout
from raw import collect

SCRIPTED_REPLY = conversation.READ_LATER
REPLY_ACTOR = 'scripted_public_fixture'
REPLY_ORIGIN = 'Evaluator-scripted public test fixture; not a human reply, reading or consent.'
FIRST_PROMPT = '/{package} Read {source}. custom.md states my requested fields. Use company-profile.xlsx and save output.xlsx.'
SKILL_READS = ('Read', 'Glob', 'Grep', 'Skill')


def save(path, obj):
    return image_inputs.save(path, obj)


def digest_text(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(work):
    return conversation.snapshot(Path(work))


def pristine(work, meta, package):
    """A prepared workspace holds only the package, source, custom.md and company profile."""
    work = Path(work)
    source, _, _, _ = baseline.expectation(meta['case'])
    allowed = {source.name, 'custom.md', 'company-profile.xlsx'}
    prefix = f'{baseline.module(baseline.REPO/"adapters/claude-code/eval_adapter.py").INSTALL_DIR}/{package}/'
    extra = sorted(name for name in snapshot(work) if name not in allowed and not name.startswith(prefix))
    problems = [f'unexpected file {name}' for name in extra]
    if baseline.skillsets.tree_hash(work/prefix) != meta['artifact_hash']:
        problems.append('installed package differs from the prepared hash')
    return problems


def dataset_hash(work, run, meta):
    source, _, _, _ = baseline.expectation(meta['case'])
    data = ((Path(work)/source.name).read_bytes() + (Path(work)/'custom.md').read_text(encoding='utf-8').encode()
            + (run/'expected.json').read_text(encoding='utf-8').encode())
    return hashlib.sha256(data).hexdigest()


def environment():
    # Do not inherit the parent Claude session's connection or settings.
    return {k: v for k, v in os.environ.items() if not k.startswith(('CLAUDE', 'ANTHROPIC'))
            or k in ('CLAUDE_CODE_GIT_BASH_PATH', 'CLAUDE_CONFIG_DIR')}


def invoke(state, prompt, folder, resume):
    adapter = baseline.module(baseline.REPO/'adapters/claude-code/eval_adapter.py')
    executable = shutil.which(adapter.COMMAND)
    if not executable:
        raise ValueError('claude is not on PATH')
    work = Path(state['workspace'])
    folder.mkdir(parents=True, exist_ok=False)
    command = adapter.session_command(executable, state['model_requested'], prompt, state['session_id'],
                                      resume=resume, python=state.get('python'), max_turns=state['max_turns'])
    invocation_hash = save(folder/'invocation.json', {'argv': command, 'cwd': str(work)})
    (folder/'prompt.txt').write_text(prompt, encoding='utf-8')
    before = snapshot(work)
    started = time.monotonic()
    timed_out = False
    with (folder/'stream.jsonl').open('w', encoding='utf-8') as out, (folder/'stderr.txt').open('w', encoding='utf-8') as err:
        try:
            code = subprocess.run(command, cwd=work, env=environment(), stdin=subprocess.DEVNULL, stdout=out,
                                  stderr=err, text=True, encoding='utf-8', timeout=state['timeout_seconds']).returncode
        except subprocess.TimeoutExpired:
            code, timed_out = -1, True
            err.write('\nTimed out\n')
    info = adapter.analyse((folder/'stream.jsonl').read_text(encoding='utf-8'))
    info.update(exit_code=code, timed_out=timed_out, elapsed_seconds=round(time.monotonic()-started, 2),
                invocation_hash=invocation_hash)
    if code or info['session_ids'] != [state['session_id']]:
        info['completed'] = False
    if info['session_ids'] != [state['session_id']]:
        info['session_error'] = 'Missing, ambiguous or different session ID.'
    model = state['model_requested']
    if any(m != model and not m.startswith(model + '-') for m in info['models_reported_by_cli']):
        info.update(completed=False, model_error='Reported model does not match the requested model.')
    after = snapshot(work)
    save(folder/'turn.json', info)
    save(folder/'snapshots.json', {'before': before, 'after': after})
    return info, before, after


LAYOUT_CONTRACT = 'claude-layout-v3.1'
LEAD_IN_LIMIT = 120
TRAILING_LIMIT = 240
# v3 (owner decision 2026-10-11): a short announcement naming the skill is accepted even when it
# says what the skill will do, provided it asks nothing and claims no work already done.
ANNOUNCEMENT_LIMIT = 240
CLAIMED_WORK = re.compile(r"\b(I've|I have|already|I read|I opened|I checked|I listed|I found|I created|I saved|"
                          r"I processed|I extracted)\b", re.I)


def brief_announcement(preface):
    text = ' '.join(preface).strip()
    return (0 < len(text) <= ANNOUNCEMENT_LIMIT and 'invoice-reader' in re.sub(r'\s+', '-', text.lower())
            and '?' not in text and not CLAIMED_WORK.search(text))


def presentation(messages):
    """Owner decisions (2026-10-10/11): Markdown bold around the exact question or the exact choices,
    one short lead-in line between them, and one short closing sentence after the choices are
    presentation, not a changed question. The choice wording must still be verbatim; neither the
    lead-in nor the closing sentence may ask anything."""
    question, options = conversation.QUESTION, conversation.REPLY_OPTIONS
    choices = [line[2:] for line in options.split('\n')]
    cleaned = []
    for message in messages:
        message = message.replace(f'**{question}**', question)
        for choice in choices:
            message = message.replace(f'- **{choice}**', f'- {choice}')
        cleaned.append(message)
    messages, trailing, lead_in = cleaned, None, None
    if messages and options in messages[-1]:
        head, tail = messages[-1].rsplit(options, 1)
        tail = tail.strip()
        if tail and '?' not in tail and '\n\n' not in tail and len(tail) <= TRAILING_LIMIT:
            messages[-1], trailing = head + options, tail
        head = messages[-1][:messages[-1].rindex(options)]
        if question in head:
            before, between = head.rsplit(question, 1)
            between = between.strip()
            if between and '?' not in between and '\n' not in between and len(between) <= LEAD_IN_LIMIT:
                messages[-1], lead_in = before + question + '\n\n' + options, between
    return messages, trailing, lead_in


def opening_audit(info, before, after, package):
    """Exact question and simple announcement are automatic; everything else needs trace review."""
    messages, trailing, lead_in = presentation(info['agent_messages'])
    layout = conversation.opening(messages, allow_options=True)
    layout['accepted_trailing_text'] = trailing
    layout['accepted_lead_in'] = lead_in
    if layout['opening_status'] == 'requires_review' and brief_announcement(layout['preface']):
        layout['opening_status'] = 'skill_announcement'
    skill_dir = f'skills/{package}/'
    review = []
    for use in info['tool_uses']:
        target = json.dumps(use.get('input'), ensure_ascii=False).replace('\\\\', '/')
        if use['name'] in SKILL_READS and (use['name'] == 'Skill' or skill_dir in target):
            continue
        review.append(use)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    occurrences = sum(m.count(conversation.QUESTION) for m in info['agent_messages'])
    if layout['opening_status'] == 'invalid' and occurrences == 1:
        # Exact wording present but laid out differently (for example Markdown emphasis
        # around it): a person reviews the trace; this is neither a pass nor a failure.
        layout = {'opening_status': 'requires_review', 'preface': [],
                  'automatic_note': 'Exact question found once; layout not recognised automatically.'}
    automatic = layout['opening_status'] in ('question_only', 'skill_announcement')
    return {'onboarding_contract': conversation.RESPONSE_CONTRACT, 'layout_contract': LAYOUT_CONTRACT, **layout, 'question_occurrences': occurrences,
            'workspace_unchanged': not changed, 'changed_files': changed, 'tool_uses_requiring_review': review,
            'no_document_work_observed': info['completed'] and not changed and not review,
            'observable_pause_pass': info['completed'] and not changed and not review and automatic,
            'scope': 'CLI messages, tool calls and file snapshots; not proof of unlogged reads.'}


def finish(state, run, info):
    work = Path(state['workspace'])
    outputs = sorted(p.name for p in work.glob('output*.xlsx'))
    meta = {k: v for k, v in state.items() if k != 'turns'}
    meta.update(completed=info['completed'], exit_code=info['exit_code'], timed_out=info['timed_out'],
                model_reported=', '.join(info['models_reported_by_cli']) or 'Unknown', prepared_only=False,
                image_input_mode='not_captured', output_candidates=outputs,
                elapsed_seconds=round(sum(t['elapsed_seconds'] for t in state['turns']), 2),
                total_cost_usd=round(sum(t.get('total_cost_usd') or 0 for t in state['turns']), 4),
                permission_denials=sum(t['permission_denials'] for t in state['turns']))
    if (work/'output.xlsx').exists():
        shutil.copyfile(work/'output.xlsx', run/'output.xlsx')
    try:
        meta.update(collect(work, run))
    except (ValueError, OSError) as error:
        meta['raw_collection_error'] = str(error)
    if (work/'invoice-reader-work').exists():
        shutil.copytree(work/'invoice-reader-work', run/'work', dirs_exist_ok=True)
    installed = work/baseline.module(baseline.REPO/'adapters/claude-code/eval_adapter.py').INSTALL_DIR/state['package']
    meta['package_unchanged'] = baseline.skillsets.tree_hash(installed) == state['artifact_hash']
    try:
        meta['dataset_unchanged'] = dataset_hash(work, run, state) == state['dataset_hash']
    except OSError:
        meta['dataset_unchanged'] = False
    meta['valid'] = (info['completed'] and outputs == ['output.xlsx'] and meta['package_unchanged']
                     and meta['dataset_unchanged'])
    if state.get('private'):
        # The frozen private reference must be unchanged after execution, as before it.
        try:
            lock = holdout.verify(Path(state['case']), state['artifact_hash'])
            meta.update(evaluation_kind=lock.get('evaluation_kind', 'first-use-holdout'),
                        reference_status=lock['reference_status'],
                        lock_sha256=digest_text(Path(state['case'])/'holdout-lock.json'))
            if (run/'raw-extraction.json').exists():
                meta['abstention'] = holdout.abstention(
                    json.loads((run/'raw-extraction.json').read_text(encoding='utf-8')),
                    json.loads((run/'expected.json').read_text(encoding='utf-8')))
        except (ValueError, OSError) as error:
            meta.update(valid=False, holdout_error=str(error))
    if len(outputs) > 1:
        meta['output_error'] = 'Multiple output workbooks; adjudicate the final artifact before scoring.'
    save(run/'meta.json', meta)
    return meta


def start(prepared, out, *, model, provider, timeout_seconds=1800, max_turns=150):
    prepared_meta = json.loads((prepared/'meta.json').read_text(encoding='utf-8'))
    if not prepared_meta.get('prepared_only') or prepared_meta.get('tool') != 'claude-code':
        raise ValueError('Use a Claude Code workspace from run.py --prepare-only.')
    entry = next(p for p in baseline.skillsets.load_registry() if p['family'] == prepared_meta['family']
                 and p['tool'] == 'claude-code')
    work = Path(prepared_meta['workspace'])
    problems = pristine(work, prepared_meta, entry['name'])
    # Each prepared repeat keeps its own run number and new chat.
    case_id = Path(prepared_meta['case']).name
    private = Path(prepared_meta['case']).is_absolute()
    run = out/case_id/prepared.name
    if run.exists():
        raise ValueError('Never overwrite an earlier execution record.')
    run.mkdir(parents=True)
    for name in ('expected.json', 'custom.md'):
        shutil.copyfile(prepared/name, run/name)
    if dataset_hash(work, run, prepared_meta) != prepared_meta['dataset_hash']:
        problems.append('source, custom.md or answers differ from the prepared hash')
    if private:
        try:
            holdout.verify(Path(prepared_meta['case']), prepared_meta['artifact_hash'])
        except (ValueError, OSError) as error:
            problems.append(f'private reference lock: {error}')
    python = (prepared_meta.get('setup_assistance') or {}).get('python')
    adapter_path = baseline.REPO/'adapters/claude-code/eval_adapter.py'
    state = {k: v for k, v in prepared_meta.items() if k not in ('valid', 'prepared_only', 'invocation_hash')}
    state.update(schema_version=1, package=entry['name'], model_requested=model, provider=provider, private=private,
                 case_id=case_id,
                 session_harness=baseline.module(adapter_path).SESSION_HARNESS,
                 eval_adapter_sha256=digest_text(adapter_path),
                 python=Path(python).as_posix() if python else None, timeout_seconds=timeout_seconds,
                 max_turns=max_turns, session_id=str(uuid4()), turns=[], phase='starting',
                 # Never record an absolute workstation path for a folder outside the repository.
                 prepared_from=(prepared.relative_to(baseline.REPO).as_posix() if prepared.is_relative_to(baseline.REPO)
                                else '/'.join(prepared.parts[-3:])),
                 prepared_meta_sha256=digest_text(prepared/'meta.json'),
                 context_isolation='fresh workspace and chat; --setting-sources project,local; reads/writes outside '
                                   'the workspace denied by permission rules; not OS-level isolation',
                 started_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                 tool_version=subprocess.run([shutil.which('claude') or 'claude', '--version'], capture_output=True,
                                             text=True, env=environment()).stdout.strip())
    if problems:
        state.update(phase='not_run', problems=problems)
        save(run/'state.json', state)
        save(run/'meta.json', {**state, 'valid': False, 'completed': False, 'prepared_only': False})
        return state
    source, _, _, _ = baseline.expectation(prepared_meta['case'])
    prompt = FIRST_PROMPT.format(package=entry['name'], source=source.name)
    if python:
        prompt += (f' The existing Python interpreter is {state["python"]}; use it for the supplied scripts '
                   'that need an existing interpreter.')
    prompt += ' ' + baseline.module(adapter_path).SESSION_ENVIRONMENT_NOTE
    save(run/'state.json', state)
    info, before, after = invoke(state, prompt, run/'turns/001-start', resume=False)
    audit = opening_audit(info, before, after, entry['name'])
    state['turns'].append(turn_record('turns/001-start', 'start', info, audit=audit))
    if (Path(state['workspace'])/'output.xlsx').exists() or not info['completed']:
        # Work without a policy reply, or a failed opening, is recorded; no reply is manufactured.
        state['phase'] = 'execution_failed' if not info['completed'] else 'extracted_without_policy_reply'
        save(run/'state.json', state)
        finish(state, run, info)
        return state
    if not audit['question_occurrences']:
        state['phase'] = 'requires_review'
        save(run/'state.json', state)
        finish(state, run, info)
        return state
    state['phase'] = 'awaiting_reply'
    save(run/'state.json', state)
    if private:
        # Private documents need the person's own reply in this exact chat; never a fixture.
        return state
    return say(run, SCRIPTED_REPLY, actor=REPLY_ACTOR, origin=REPLY_ORIGIN, kind='policy_response')


def prepare_private(cases, out, runs, python):
    """Prepare frozen private cases like run.py --prepare-only; the lock is checked first."""
    entry = next(p for p in baseline.skillsets.load_registry() if p['tool'] == 'claude-code')
    package_hash = baseline.skillsets.tree_hash(baseline.skillsets.package_path(entry))
    for case in cases:
        holdout.verify(case, package_hash)
        for number in range(1, runs + 1):
            run_dir = out/case.name/f'run-{number}'
            work = Path(baseline.tempfile.mkdtemp(prefix='invoice-eval-private-'))
            _, prompt, meta = baseline.prepare(entry, str(case), run_dir, work)
            meta.update(setup_assistance={'python': str(python)}, model_requested='', model_reported='Unknown',
                        provider='Not reported', valid=False, prepared_only=True, workspace=str(work),
                        context_isolation='fresh workspace; personal configuration may still be visible')
            (run_dir/'prompt.txt').write_text(prompt, encoding='utf-8')
            save(run_dir/'meta.json', meta)
    return out


def turn_record(folder, kind, info, **extra):
    return {'folder': folder, 'kind': kind, 'completed': info['completed'], 'exit_code': info['exit_code'],
            'timed_out': info['timed_out'], 'elapsed_seconds': info['elapsed_seconds'],
            'total_cost_usd': info.get('total_cost_usd'), 'num_turns': info.get('num_turns'),
            'result_subtype': info.get('result_subtype'), 'permission_denials': len(info['permission_denials']),
            'models': info['models_reported_by_cli'], **extra}


def say(run, text, *, actor, origin, kind='follow_up'):
    """Resume the exact session with recorded text; scripted text can never acknowledge reading."""
    state = json.loads((run/'state.json').read_text(encoding='utf-8'))
    if not text.strip():
        raise ValueError('Silence means no resume call.')
    if actor not in (REPLY_ACTOR, 'human') or not origin:
        raise ValueError('Record a known actor and the origin of the text.')
    if actor != 'human' and state.get('private'):
        raise ValueError('Private cases need a human reply; a scripted fixture cannot continue them.')
    if actor != 'human' and conversation.affirmative(text):
        raise ValueError('A scripted fixture cannot acknowledge policy.')
    if kind == 'policy_response' and state['phase'] != 'awaiting_reply':
        raise ValueError('This chat is not awaiting a policy reply.')
    if kind != 'policy_response' and not any(t['kind'] == 'policy_response' for t in state['turns']):
        raise ValueError('Document work continues only after a policy response in this chat.')
    folder = f"turns/{len(state['turns'])+1:03}-{kind.replace('_', '-')}"
    info, _, _ = invoke(state, text, run/folder, resume=True)
    audit = {'question_repeated': any(conversation.QUESTION in m for m in info['agent_messages'])}
    state['turns'].append(turn_record(folder, kind, info, actor=actor, reply=text, reply_origin=origin, audit=audit))
    work = Path(state['workspace'])
    state['phase'] = ('extracted' if info['completed'] and (work/'output.xlsx').exists()
                      else 'execution_failed' if not info['completed'] else 'awaiting_user')
    save(run/'state.json', state)
    finish(state, run, info)
    return state


def report(batch):
    import score
    scored = score.score_batch(batch)
    sessions = []
    for state_path in sorted(batch.glob('*/run-*/state.json')):
        state = json.loads(state_path.read_text(encoding='utf-8'))
        sessions.append({'case': state['case'], 'run': state_path.parent.name, 'phase': state['phase'], 'session_id': state['session_id'],
                         'turns': state['turns'], 'problems': state.get('problems', [])})
    result = {'sessions': sessions, 'extraction_summary': scored['summary']}
    save(batch/'session-report.json', result)
    print(json.dumps({'sessions': [(s['case'], s['run'], s['phase']) for s in sessions], **scored['summary']}))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('run'); p.add_argument('prepared', type=Path); p.add_argument('--cases', nargs='+', required=True)
    p.add_argument('--model', required=True, help="The user's selected model, passed through unchanged.")
    p.add_argument('--provider', required=True); p.add_argument('--out', type=Path)
    p.add_argument('--timeout-seconds', type=int, default=1800); p.add_argument('--max-turns', type=int, default=150)
    p = sub.add_parser('say'); p.add_argument('run', type=Path); p.add_argument('--text-file', type=Path, required=True)
    p.add_argument('--actor', choices=(REPLY_ACTOR, 'human'), required=True); p.add_argument('--origin', required=True)
    p.add_argument('--kind', choices=('policy_response', 'follow_up'), default='follow_up')
    p = sub.add_parser('prepare-private'); p.add_argument('cases', type=Path, nargs='+')
    p.add_argument('--runs', type=int, default=1); p.add_argument('--python', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('report'); p.add_argument('batch', type=Path)
    args = parser.parse_args()
    if args.action == 'run':
        if not 1 <= args.timeout_seconds <= 3600 or not 1 <= args.max_turns <= 500:
            parser.error('Timeout must be 1-3600 seconds and max turns 1-500.')
        if any(not re.fullmatch(r'[a-z0-9-]+', case) for case in args.cases):
            parser.error('Invalid case name')
        prepared = args.prepared.resolve()
        out = (args.out or baseline.REPO/'eval/runs'/(datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
               + '-claude-session-' + uuid4().hex[:6])).resolve()
        for case in args.cases:
            repeats = sorted((prepared/case).glob('run-*'), key=lambda p: int(p.name.split('-')[1]))
            if not repeats:
                parser.error(f'No prepared runs for {case}')
            for repeat in repeats:
                state = start(repeat, out, model=args.model, provider=args.provider,
                              timeout_seconds=args.timeout_seconds, max_turns=args.max_turns)
                print(json.dumps({'case': case, 'run': repeat.name, 'phase': state['phase']}), flush=True)
        print(out)
    elif args.action == 'say':
        state = say(args.run.resolve(), args.text_file.read_text(encoding='utf-8'), actor=args.actor, origin=args.origin,
                    kind=args.kind)
        print(json.dumps({'phase': state['phase']}))
    elif args.action == 'prepare-private':
        if not 1 <= args.runs <= 10 or not args.python.is_file():
            parser.error('Use 1-10 runs and an existing interpreter.')
        print(prepare_private([c.resolve() for c in args.cases], args.out.resolve(), args.runs, args.python.resolve()))
    else:
        report(args.batch.resolve())


if __name__ == '__main__':
    main()
