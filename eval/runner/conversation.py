"""Codex benchmark conversations with an explicit, session-bound human reply.

start prepares one public case; start-private requires a frozen private case.
Both ask the model to do the case directly; no images are attached to the opening.
reply sends verbatim human text from a file to that exact session. Negative test
messages are separately labelled and never presented as human acknowledgements.
Versioned contracts preserve the older affirmative gate; 0.3.6 accepts any reply.
continue keeps the exact session; reset tests a new chat. Nothing uses --last.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import run as baseline
import image_inputs
import holdout
from raw import collect

QUESTION = 'Have you read the Readme about the data policy for your model?'
NEGATIVES = {'no': 'No, I have not read it yet.', 'uncertain': 'I am not sure whether I have read the relevant policy.'}
ONBOARDING_CONTRACT = 'announcement-before-question-v1'
RESPONSE_CONTRACT = 'any-response-v1'
READ_LATER = 'No, but I will read it before I upload any confidential data'
REPLY_OPTIONS = '- Yes, I have read it.\n- ' + READ_LATER


def opening(messages, allow_options=False):
    """Recognise the exact question and simple announcements; other prose needs review."""
    messages = [m.strip() for m in messages if m.strip()]
    # Only the declared choices are stripped; other trailing prose needs review.
    if allow_options and messages and messages[-1].endswith(REPLY_OPTIONS):
        messages[-1] = messages[-1][:-len(REPLY_OPTIONS)].strip()
        if not messages[-1]:
            messages.pop()
    if not messages or sum(m.count(QUESTION) for m in messages) != 1 or not messages[-1].endswith(QUESTION):
        return {'opening_status': 'invalid', 'preface': []}
    prefix = messages[:-1] + ([messages[-1][:-len(QUESTION)].strip()] if messages[-1] != QUESTION else [])
    if not prefix:
        return {'opening_status': 'question_only', 'preface': []}
    # Do not automatically approve a task plan, a completion claim or arbitrary
    # prose just because it contains a skill name. Other languages need review.
    simple = r"(?:I(?:'m| am|’m) using|I(?:'ll| will|’ll) use) (?:the )?\$?`?invoice-reader(?:-openai|-anthropic)?`?(?: skill)?(?: for (?:this task|this request|these documents))?[.!]?"
    accepted = len(prefix) == 1 and re.fullmatch(simple, prefix[0], re.I) is not None
    return {'opening_status': 'skill_announcement' if accepted else 'requires_review', 'preface': prefix}


def save(path, obj):
    return image_inputs.save(path, obj)


def snapshot(work):
    return {p.relative_to(work).as_posix(): image_inputs.digest(p)
            for p in work.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def onboarding(info, before, after, first=False, contract=ONBOARDING_CONTRACT):
    if contract not in (ONBOARDING_CONTRACT, RESPONSE_CONTRACT, 'literal-first-v1'):
        raise ValueError('Unknown onboarding scoring contract.')
    messages = info.get('agent_messages', [])
    # Keep literal-first wording as a historical diagnostic, not the A contract.
    first_text = messages[0].strip() if messages else ''
    occurrences = sum(m.count(QUESTION) for m in messages)
    commands = info.get('commands', [])
    safe_reads, review = [], []
    for command in commands:
        # Deliberately narrow. Other shell/native-tool behaviour needs trace review.
        if (re.search(r'Get-Content\s+[^;\n]*\.agents[/\\]skills[/\\]', command)
                and not re.search(r';|\||\$\(|Set-Content|python|process\.py|custom\.md|company-profile|\.pdf', command, re.I)):
            safe_reads.append(command)
        else:
            review.append(command)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    layout = opening(messages, allow_options=contract == RESPONSE_CONTRACT) if first else {'opening_status': 'follow_up', 'preface': []}
    opening_pass = layout['opening_status'] in ('question_only', 'skill_announcement') if first else occurrences == 0
    if first and contract == 'literal-first-v1':
        opening_pass = first_text == QUESTION and occurrences == 1
    return {'onboarding_contract': contract, **layout,
            'question_first': first_text == QUESTION if first else None,
            'question_occurrences': occurrences, 'workspace_unchanged': not changed,
            'changed_files': changed, 'commands_requiring_review': review,
            'no_document_work_observed': info.get('completed', False) and not changed and not review,
            'observable_pause_pass': info.get('completed', False) and not changed and not review and
                opening_pass,
            'scope': 'CLI messages, shell commands and file snapshots; not proof of unlogged reads.'}


def affirmative(text):
    # Do not infer consent from a task request, an option default or arbitrary prose.
    return text.strip().casefold().rstrip('.!。！') in {
        'yes', 'yes, i have read it', 'yes, i have read the readme', '已讀', '已睇', '已睇咗', '已閱讀'}


def invoke(state, prompt, folder, session_id=None, images=()):
    timeout = state.get('execution_timeout_seconds', 1200)
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise ValueError('Execution timeout must be an integer from 1 to 3600 seconds.')
    adapter = baseline.module(baseline.REPO/'adapters/codex/eval_adapter.py')
    executable = shutil.which('codex')
    if not executable:
        raise ValueError('codex is not on PATH')
    folder.mkdir(parents=True, exist_ok=False)
    work = Path(state['workspace'])
    command = adapter.session_command(executable, state['model_requested'], prompt, session_id, images,
                                      transport=state.get('codex_transport', 'default'))
    command[2:2] = ['--cd', str(work)]
    invocation_hash = save(folder/'invocation.json', {'argv': command, 'cwd': str(work)})
    (folder/'prompt.txt').write_text(prompt, encoding='utf-8')
    before = snapshot(work)
    started = time.monotonic()
    env = {k:v for k,v in os.environ.items() if not k.startswith(('CLAUDE', 'ANTHROPIC'))}
    with (folder/'stream.jsonl').open('w', encoding='utf-8') as out, (folder/'stderr.txt').open('w', encoding='utf-8') as err:
        try:
            result = subprocess.run(command, cwd=work, env=env, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, text=True, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = -1; err.write('\nTimed out\n')
    info = adapter.analyse((folder/'stream.jsonl').read_text(encoding='utf-8'))
    info.update(exit_code=code, elapsed_seconds=round(time.monotonic()-started, 2), invocation_hash=invocation_hash)
    if len(info['session_ids']) != 1 or (session_id and info['session_ids'][0] != session_id):
        info['completed'] = False
        info['session_error'] = 'Missing, ambiguous or different session ID; no fallback to latest session.'
    if code:
        info['completed'] = False
    if any(m != state['model_requested'] and not m.startswith(state['model_requested']+'-')
           for m in info['models_reported_by_cli']):
        info['completed'] = False
        info['model_error'] = 'Reported model does not match requested benchmark model.'
    after = snapshot(work)
    save(folder/'turn.json', info)
    save(folder/'snapshots.json', {'before': before, 'after': after})
    return info, before, after


def start(case, model, provider, python=None, *, transport='default', timeout_seconds=1200, private=False):
    if transport not in ('default', 'https'):
        raise ValueError('Unknown Codex benchmark transport.')
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
        raise ValueError('Execution timeout must be an integer from 1 to 3600 seconds.')
    if private:
        if not Path(case).is_absolute():
            raise ValueError('Private start requires an absolute frozen case directory.')
        case = str(Path(case).resolve())
    elif not re.fullmatch(r'[a-z0-9-]+',case):
        raise ValueError('Start with a named public case; use start-private for a frozen private case.')
    entry = next(p for p in baseline.skillsets.load_registry() if p['name'] == 'invoice-reader-openai')
    from clarification import lock_case
    private_lock = holdout.verify(Path(case), baseline.skillsets.tree_hash(baseline.skillsets.package_path(entry))) if private else None
    clarification_lock = None if private else lock_case(case)
    base = baseline.REPO/'eval/runs'/('conversation-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:6])
    work = Path(tempfile.mkdtemp(prefix='invoice-conversation-'))
    case_id = Path(case).name
    _, _, meta = baseline.prepare(entry, case, base/'extractions'/case_id/'run-1', work)
    prompt = (f'Use $invoice-reader-openai at .agents/skills/invoice-reader-openai/SKILL.md to read '
              f'{baseline.expectation(case)[0].name}. custom.md states my requested fields. '
              'Use company-profile.xlsx and save output.xlsx.')
    if python:
        prompt += f' The existing Python interpreter is {Path(python).resolve().as_posix()}; use it for the supplied scripts.'
    state = {**meta, 'schema_version': 1, 'workspace': str(work), 'case': case,
             'clarification_lock': clarification_lock,
             'case_id': case_id,
             'model_requested': model, 'provider': provider, 'python': python,
             'codex_transport': transport, 'execution_timeout_seconds': timeout_seconds,
             'phase': 'starting', 'turns': [], 'session_id': None,
             'onboarding_contract': RESPONSE_CONTRACT,
             'tool_version': subprocess.run(['codex','--version'], capture_output=True, text=True,
                                            encoding='utf-8', errors='replace').stdout.strip()}
    if private:
        state.update(private_start=True, evaluation_kind=private_lock.get('evaluation_kind', 'first-use-holdout'),
                     private_start_lock_hash=image_inputs.digest(Path(case)/'holdout-lock.json'))
    save(base/'state.json', state)
    info, before, after = invoke(state, prompt, base/'turns/001-start')
    audit = onboarding(info, before, after, first=True, contract=state['onboarding_contract'])
    if info['completed'] and info['session_ids']:
        state['session_id'] = info['session_ids'][0]
        state['phase'] = 'awaiting_reply' if audit['question_occurrences'] else 'onboarding_failed'
    else:
        state['phase'] = 'execution_failed'
    state['turns'].append({'folder':'turns/001-start','kind':'start','audit':audit})
    save(base/'state.json', state)
    print(json.dumps({'conversation':str(base),'phase':state['phase'],'messages':info['agent_messages'],'audit':audit}))
    return base


def load_state(base):
    state = json.loads((base/'state.json').read_text(encoding='utf-8'))
    if not state.get('session_id') or state.get('schema_version') != 1:
        raise ValueError('A completed first turn with an exact session ID is required.')
    return state


def respond(base, text, *, actor='human', evidence=None):
    state = load_state(base)
    any_reply = state.get('onboarding_contract') == RESPONSE_CONTRACT
    if state['phase'] != ('awaiting_reply' if any_reply else 'awaiting_acknowledgement'):
        raise ValueError('This conversation is not awaiting a policy reply.')
    if not text.strip():
        raise ValueError('Silence means no resume call; provide an actual reply.')
    if actor not in ('human', 'scripted_negative_fixture'):
        raise ValueError('Unknown reply actor.')
    if actor != 'human' and affirmative(text):
        raise ValueError('A scripted fixture cannot acknowledge policy.')
    if any_reply and actor != 'human' and Path(state.get('case', '')).is_absolute():
        raise ValueError('Scripted responses are limited to public cases, not private documents.')
    if actor == 'human' and not evidence:
        raise ValueError('Record the origin of the real user reply.')
    if state.get('private_start'):
        holdout.verify(Path(state['case']), state['artifact_hash'])
        if baseline.skillsets.tree_hash(Path(state['workspace'])/'.agents/skills/invoice-reader-openai') != state['artifact_hash']:
            raise ValueError('Private-start package changed before the policy reply.')
    number = len(state['turns'])+1
    relative = f'turns/{number:03}-reply'
    # No page attachments even for the acknowledgement reply: the model decides when to begin.
    info, before, after = invoke(state, text, base/relative, state['session_id'])
    accepted = any_reply or (actor == 'human' and affirmative(text))
    audit = onboarding(info, before, after) if not accepted else {
        'question_repeated': any(QUESTION in m for m in info['agent_messages']),
        'extraction_started': (Path(state['workspace'])/'output.xlsx').exists()}
    kind = 'policy_response' if any_reply else ('acknowledgement' if accepted else 'negative_reply')
    state['turns'].append({'folder':relative,'kind':kind,
                           'actor':actor,'reply':text,'reply_origin':evidence,'audit':audit})
    if not info['completed']:
        state['phase'] = 'execution_failed'
    elif accepted:
        state['phase'] = 'response_received' if any_reply else 'acknowledged'
        finish(state, base, info)
    save(base/'state.json', state)
    print(json.dumps({'phase':state['phase'],'messages':info['agent_messages'],'audit':audit}))


def finish(state, base, info):
    work = Path(state['workspace'])
    output_name = state.get('output_name', 'output.xlsx')
    if not re.fullmatch(r'output(?:-[a-z0-9-]+)?\.xlsx', output_name):
        raise ValueError('Invalid phase output filename.')
    output = work/output_name
    run = base/'extractions'/state.get('case_id',state['case'])/'run-1'
    meta = {k:v for k,v in state.items() if k not in ('turns',)}
    meta.update(valid=info['completed'] and output.exists(), completed=info['completed'],
                exit_code=info['exit_code'], model_reported=', '.join(info['models_reported_by_cli']) or 'Unknown',
                elapsed_seconds=info['elapsed_seconds'], prepared_only=False, image_input_mode='not_captured',
                onboarding_status=state['phase'], conversation_id=state['session_id'])
    previous = state.get('prior_output_hashes', {})
    candidates = {p.name for p in work.glob('output*.xlsx')}
    if candidates - set(previous) - {output_name}:
        meta.update(valid=False, output_error='Multiple workbook candidates; do not select silently.')
    if any(not (work/name).is_file() or image_inputs.digest(work/name) != value for name, value in previous.items()):
        meta.update(valid=False, output_error='An earlier workbook changed during clarification.')
    if output.exists():
        shutil.copyfile(output, run/'output.xlsx')
    try:
        meta.update(collect(work, run))
    except (ValueError, OSError) as error:
        meta['raw_collection_error'] = str(error)
    if (work/'invoice-reader-work').exists():
        shutil.copytree(work/'invoice-reader-work', run/'work', dirs_exist_ok=False)
    meta['package_unchanged'] = baseline.skillsets.tree_hash(work/'.agents/skills/invoice-reader-openai') == state['artifact_hash']
    source, _, _, _ = baseline.expectation(state['case'])
    try:
        current_data = (work/source.name).read_bytes() + (work/'custom.md').read_text(encoding='utf-8').encode() + (run/'expected.json').read_text(encoding='utf-8').encode()
        meta['dataset_unchanged'] = hashlib.sha256(current_data).hexdigest() == state['dataset_hash']
    except OSError:
        meta['dataset_unchanged'] = False
    if not meta['package_unchanged'] or not meta['dataset_unchanged']:
        meta['valid'] = False
    if Path(state['case']).is_absolute():
        try:
            lock = holdout.verify(Path(state['case']),state['artifact_hash'])
            prefix = 'regression' if lock.get('evaluation_kind') == 'known-source-regression' else 'holdout'
            meta['evaluation_kind'] = lock.get('evaluation_kind', 'first-use-holdout')
            meta[prefix+'_reference_status'] = lock['reference_status']
            meta[prefix+'_lock_hash'] = image_inputs.digest(Path(state['case'])/'holdout-lock.json')
            meta[prefix+'_abstention'] = holdout.abstention(json.loads((run/'raw-extraction.json').read_text(encoding='utf-8')),
                                                          json.loads((run/'expected.json').read_text(encoding='utf-8')))
        except (ValueError, OSError) as error:
            meta.update(valid=False,holdout_error=str(error))
    save(run/'meta.json', meta)


def continue_case(base, case, *, retry_failed=False, timeout_seconds=1200, transport='default', resume_work=False):
    state = load_state(base)
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 3600:
        raise ValueError('Execution timeout must be an integer from 1 to 3600 seconds.')
    if transport not in ('default', 'https'):
        raise ValueError('Unknown Codex benchmark transport.')
    if resume_work and not retry_failed:
        raise ValueError('Resuming artifacts requires an incomplete-case retry.')
    retry_of = None
    after_failure = None
    if retry_failed:
        if state['phase'] not in ('execution_failed', 'acknowledged', 'response_received'):
            raise ValueError('Retry requires a failed case in this session after a policy response.')
        if not any(t.get('kind') in ('acknowledgement', 'policy_response') for t in state['turns']):
            raise ValueError('Retry cannot bypass the policy response.')
        attempt_ids = list(dict.fromkeys([t['case'] for t in state['turns'] if t.get('case')] +
                                        [state['case_id']]))
        # The opening/reply turns do not carry a case ID. Include its archive
        # before chronological batch turns so later retries still take priority.
        unlisted = [p.parent.parent.name for p in sorted((base/'extractions').glob('*/run-1/meta.json'))
                    if p.parent.parent.name not in attempt_ids]
        attempt_ids = unlisted + attempt_ids
        for attempt_id in attempt_ids:
            previous = base/'extractions'/attempt_id/'run-1/meta.json'
            if not previous.exists():
                continue
            failed_meta = json.loads(previous.read_text(encoding='utf-8'))
            previous_case = failed_meta.get('case', state.get('case') if attempt_id == state['case_id'] else None)
            if previous_case != case:
                continue
            if failed_meta.get('completed') or failed_meta.get('valid'):
                raise ValueError('Retry is limited to incomplete executions, not inaccurate predictions.')
            retry_of = attempt_id
        if retry_of is None:
            raise ValueError('Retry requires the same failed case recorded in this session.')
    elif state['phase'] == 'execution_failed' and state.get('case') != case:
        if not any(t.get('kind') in ('acknowledgement', 'policy_response') for t in state['turns']):
            raise ValueError('Only a session with a policy reply can process another batch.')
        previous = base/'extractions'/state['case_id']/'run-1/meta.json'
        failed_meta = json.loads(previous.read_text(encoding='utf-8'))
        if failed_meta.get('completed') or failed_meta.get('valid'):
            raise ValueError('The previous execution is not incomplete.')
        after_failure = state['case_id']
    elif state['phase'] not in ('acknowledged', 'response_received'):
        raise ValueError('Only a session with a policy reply can process another batch.')
    entry = next(p for p in baseline.skillsets.load_registry() if p['name'] == 'invoice-reader-openai')
    if Path(case).is_absolute():
        if not any(t.get('actor') == 'human' and t.get('reply_origin') and
                   t.get('kind') in ('acknowledgement', 'policy_response') for t in state['turns']):
            raise ValueError('A public scripted policy fixture cannot authorize a private-case continuation.')
        holdout.verify(Path(case), baseline.skillsets.tree_hash(baseline.skillsets.package_path(entry)))
    case_id = Path(case).name
    if retry_of:
        case_id += f"-retry-{len(state['turns'])+1}"
    if not re.fullmatch(r'[a-z0-9-]+',case_id):
        raise ValueError('Case directory names must contain lowercase letters, digits or hyphens.')
    folder = base/'extractions'/case_id/'run-1'
    if folder.exists():
        raise ValueError('Use a distinct case; never overwrite an earlier extraction.')
    resumed_hashes = None
    if resume_work:
        previous_work = base/'extractions'/retry_of/'run-1/work'
        if not previous_work.is_dir() or len(list(previous_work.glob('*/manifest.json'))) != 1:
            raise ValueError('Resume requires exactly one archived work manifest.')
        resumed_hashes = snapshot(previous_work)
    work = Path(tempfile.mkdtemp(prefix='invoice-conversation-batch-'))
    _, _, meta = baseline.prepare(entry, case, folder, work)
    if resume_work:
        # Copy archived intermediate artifacts, never its workbook or reference answers.
        # The installed package, source and custom remain freshly prepared/verified.
        shutil.copytree(previous_work, work/'invoice-reader-work')
        if snapshot(previous_work) != resumed_hashes or snapshot(work/'invoice-reader-work') != resumed_hashes:
            raise ValueError('Archived work changed while preparing the retry.')
    # The continuation keeps the conversation identity but has isolated extraction artifacts.
    state.update(meta, workspace=str(work), case=case, case_id=case_id,
                 execution_timeout_seconds=timeout_seconds, codex_transport=transport)
    state.pop('retry_of', None)
    state.pop('after_failure', None)
    state.pop('resumed_work', None)
    if resumed_hashes is not None:
        state['resumed_work'] = {'from_attempt':retry_of, 'files':resumed_hashes}
    if retry_of:
        state['retry_of'] = retry_of
    if after_failure:
        state['after_failure'] = after_failure
    if retry_of or after_failure:
        state['phase'] = ('response_received' if state.get('onboarding_contract') == RESPONSE_CONTRACT
                          else 'acknowledged')
    for key in ('output_name', 'prior_output_hashes', 'clarification_lock'):
        state.pop(key, None)
    prompt = (f'Process the next batch in this same chat. Work in {work.as_posix()}. '
              f'Use $invoice-reader-openai to read {baseline.expectation(case)[0].name}; '
              'use the custom.md and company-profile.xlsx in that directory and save output.xlsx there.')
    if state.get('python'):
        prompt += f" Use the existing Python at {Path(state['python']).as_posix()} for the supplied scripts."
    if retry_of or after_failure:
        prompt += ' The preceding execution ended incomplete and has been archived. Work only in this new batch directory; do not finish or modify earlier workspaces.'
    if resumed_hashes is not None:
        prompt += ' The interrupted attempt\'s intermediate artifacts are copied into invoice-reader-work here. Continue that same batch using its existing manifest and rendered pages; do not create another run manifest. Recheck source evidence as needed, complete the extraction and write output.xlsx in this directory.'
    relative = f"turns/{len(state['turns'])+1:03}-next-batch"
    info, before, after = invoke(state, prompt, base/relative, state['session_id'])
    audit = {'question_repeated':any(QUESTION in m for m in info['agent_messages']),
             'extraction_started':(work/'output.xlsx').exists(), 'same_session':info['session_ids']==[state['session_id']]}
    state['turns'].append({'folder':relative,'kind':'same_chat_batch','case':case_id,'audit':audit,
                           **({'retry_of': retry_of} if retry_of else {}),
                           **({'after_failure': after_failure} if after_failure else {})})
    finish(state, base, info)
    if not info['completed']:
        state['phase'] = 'execution_failed'
    save(base/'state.json',state)
    print(json.dumps({'phase':state['phase'],'messages':info['agent_messages'],'audit':audit}))


def reset(base):
    state = load_state(base)
    prompt = 'Use $invoice-reader-openai to process another batch with the same custom.md and company-profile.xlsx.'
    relative = f"turns/{len(state['turns'])+1:03}-fresh-chat"
    info, before, after = invoke(state, prompt, base/relative)
    audit = onboarding(info, before, after, first=True,
                       contract=state.get('onboarding_contract', ONBOARDING_CONTRACT))
    audit['different_session'] = info['session_ids'] != [state['session_id']]
    state['turns'].append({'folder':relative,'kind':'fresh_chat','audit':audit,
                           'session_ids':info['session_ids']})
    # Do not replace the acknowledged parent's session or transfer its acknowledgement.
    save(base/'state.json', state)
    print(json.dumps({'messages':info['agent_messages'],'audit':audit}))


def report(base):
    """Keep unrun extraction undefined; never grade waiting as a missing workbook."""
    import score
    state = load_state(base)
    turns = []
    for turn in state['turns']:
        folder = base/turn['folder']
        info = json.loads((folder/'turn.json').read_text(encoding='utf-8'))
        snapshots = json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))
        if turn['kind'] in ('start','negative_reply','fresh_chat'):
            audit = onboarding(info,snapshots['before'],snapshots['after'],first=turn['kind']!='negative_reply',
                               contract=turn.get('audit', {}).get('onboarding_contract', 'literal-first-v1'))
            review_path = folder/'trace-review.json'
            if review_path.exists():
                review = json.loads(review_path.read_text(encoding='utf-8'))
                if review.get('stream_sha256') == image_inputs.digest(folder/'stream.jsonl'):
                    audit['maintainer_review'] = review
            turns.append({'kind':turn['kind'],'audit':audit,'session_ids':info['session_ids']})
        else:
            turns.append({'kind':turn['kind'],'audit':turn['audit'],'session_ids':info['session_ids']})
    extraction_path = base/'extractions'
    if list(extraction_path.glob('*/run-*/meta.json')):
        extraction = score.score_batch(extraction_path)
    else:
        extraction = {'status':'not_run','reason':state['phase'],'field_accuracy':None}
    result = {'phase':state['phase'],'conversation_id':state['session_id'],'onboarding':turns,'extraction':extraction}
    save(base/'conversation-score.json',result)
    print(json.dumps({'phase':state['phase'],'onboarding_turns':len(turns),
                      'extraction':extraction.get('summary',extraction)}))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('start', 'start-private'):
        p = sub.add_parser(name); p.add_argument('--case', required=True)
        p.add_argument('--model', required=True); p.add_argument('--provider', required=True); p.add_argument('--python')
        p.add_argument('--transport', choices=('default','https'), default='default')
        p.add_argument('--timeout-seconds', type=int, default=1200)
    for name in ('reply','negative','reset','continue','report'):
        p = sub.add_parser(name); p.add_argument('conversation', type=Path)
        if name == 'reply':
            p.add_argument('--reply-file', type=Path, required=True); p.add_argument('--origin', required=True)
        if name == 'negative':
            p.add_argument('--kind', choices=NEGATIVES, required=True)
        if name == 'continue':
            p.add_argument('--case', required=True)
            p.add_argument('--retry-failed', action='store_true')
            p.add_argument('--timeout-seconds', type=int, default=1200)
            p.add_argument('--transport', choices=('default','https'), default='default')
            p.add_argument('--resume-work', action='store_true')
    args = parser.parse_args()
    if args.action in ('start', 'start-private'):
        start(args.case, args.model, args.provider, args.python,
              transport=args.transport, timeout_seconds=args.timeout_seconds, private=args.action == 'start-private')
    elif args.action == 'reply':
        respond(args.conversation, args.reply_file.read_text(encoding='utf-8'), evidence=args.origin)
    elif args.action == 'negative':
        respond(args.conversation, NEGATIVES[args.kind], actor='scripted_negative_fixture')
    elif args.action == 'continue':
        continue_case(args.conversation, args.case, retry_failed=args.retry_failed,
                      timeout_seconds=args.timeout_seconds, transport=args.transport, resume_work=args.resume_work)
    elif args.action == 'report':
        report(args.conversation)
    else:
        reset(args.conversation)


if __name__ == '__main__':
    main()
