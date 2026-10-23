"""Versioned public scripted replies within an existing benchmark conversation.

python eval/runner/clarification.py CONVERSATION --phase first
Answers/replies are frozen at conversation start and never exposed before their turn.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import conversation
import run as baseline
from image_inputs import digest, save


def lock_case(case):
    if not re.fullmatch(r'[a-z0-9-]+', case):
        return None
    folder = baseline.REPO/'eval/scenarios'/case
    if not (folder/'clarification.json').exists():
        return None
    plan = json.loads((folder/'clarification.json').read_text(encoding='utf-8'))
    if plan.get('version') != 1 or not isinstance(plan.get('phases'), list) or not plan['phases']:
        raise ValueError('Invalid clarification fixture.')
    names = ['clarification.json', 'case.toml', 'custom.md', 'expected.json']
    ids, outputs = set(), {'output.xlsx'}
    for phase in plan['phases']:
        if (set(phase) != {'id','expected','output','reply'} or
                not re.fullmatch(r'[a-z0-9-]+', phase['id']) or phase['id'] in ids or
                not re.fullmatch(r'expected-[a-z0-9-]+\.json', phase['expected']) or
                not re.fullmatch(r'output-[a-z0-9-]+\.xlsx', phase['output']) or phase['output'] in outputs or
                not isinstance(phase['reply'], str) or not phase['reply'].strip()):
            raise ValueError('Invalid, duplicate or unsafe clarification phase.')
        ids.add(phase['id']); outputs.add(phase['output']); names.append(phase['expected'])
    source = baseline.expectation(case)[0]
    return {'files': {name: digest(folder/name) for name in names}, 'source_sha256': digest(source)}


def followup(base, phase_id):
    state = conversation.load_state(base)
    if state['phase'] != 'response_received' or not state.get('clarification_lock'):
        raise ValueError('Requires a policy response and a public fixture locked before model execution.')
    if lock_case(state['case']) != state['clarification_lock']:
        raise ValueError('Clarification source/references/replies changed since start.')
    folder = baseline.REPO/'eval/scenarios'/state['case']
    plan = json.loads((folder/'clarification.json').read_text(encoding='utf-8'))
    done = [t['clarification_phase'] for t in state['turns'] if t['kind'] == 'scripted_clarification']
    if len(done) >= len(plan['phases']) or [p['id'] for p in plan['phases'][:len(done)]] != done:
        raise ValueError('Clarification sequence already complete or inconsistent.')
    phase = plan['phases'][len(done)]
    if phase['id'] != phase_id:
        raise ValueError('Reply phases must run once, in frozen order.')
    work = Path(state['workspace'])
    if baseline.skillsets.tree_hash(work/'.agents/skills/invoice-reader-openai') != state['artifact_hash']:
        raise ValueError('Installed package changed before reply.')
    source = baseline.expectation(state['case'])[0]
    if digest(work/source.name) != state['clarification_lock']['source_sha256'] or digest(work/'custom.md') != state['clarification_lock']['files']['custom.md']:
        raise ValueError('Source or settings changed before reply.')
    previous = {p.name: digest(p) for p in work.glob('output*.xlsx')}
    allowed_previous = {'output.xlsx'} | {p['output'] for p in plan['phases'][:len(done)]}
    if set(previous) - allowed_previous:
        raise ValueError('Unexpected workbook candidates before reply; adjudicate rather than selecting silently.')
    output = phase['output']
    if output in previous:
        raise ValueError('Phase output already exists; do not overwrite.')
    state.update(case_id=state['case']+'-'+phase_id, output_name=output, prior_output_hashes=previous)
    run = base/'extractions'/state['case_id']/'run-1'
    run.mkdir(parents=True, exist_ok=False)
    expected_text = (folder/phase['expected']).read_text(encoding='utf-8')
    (run/'expected.json').write_text(expected_text, encoding='utf-8')
    (run/'custom.md').write_bytes((work/'custom.md').read_bytes())
    state['dataset_hash'] = hashlib.sha256((work/source.name).read_bytes() + (work/'custom.md').read_text(encoding='utf-8').encode() + expected_text.encode()).hexdigest()
    prompt = phase['reply'] + f' Save the updated workbook as {output}; preserve earlier workbooks and reuse the existing run manifest.'
    relative = f"turns/{len(state['turns'])+1:03}-clarification-{phase_id}"
    # Persist the declared scripted actor before execution. No real-user reply is invented.
    save(run/'reply-provenance.json', {'actor':'scripted_public_fixture', 'phase':phase_id,
                                      'reply':phase['reply'], 'plan_sha256':state['clarification_lock']['files']['clarification.json']})
    info, before, after = conversation.invoke(state, prompt, base/relative, state['session_id'])
    audit = {'question_repeated':any(conversation.QUESTION in m for m in info['agent_messages']),
             'same_session':info['session_ids'] == [state['session_id']],
             'prior_workbooks_unchanged':all(after.get(k) == v for k,v in previous.items())}
    state['turns'].append({'folder':relative,'kind':'scripted_clarification','clarification_phase':phase_id,
                           'actor':'scripted_public_fixture','reply':phase['reply'],'audit':audit})
    conversation.finish(state, base, info)
    if not info['completed']:
        state['phase'] = 'execution_failed'
    save(base/'state.json', state)
    print(json.dumps({'phase':phase_id,'messages':info['agent_messages'],'audit':audit}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('conversation', type=Path); parser.add_argument('--phase', required=True)
    args = parser.parse_args()
    followup(args.conversation, args.phase)
