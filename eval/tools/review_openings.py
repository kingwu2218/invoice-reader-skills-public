"""Add versioned diagnostics to a public repeat batch without changing old scores."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'eval/runner'))
import conversation
import workflow_audit


def review(batch, destination):
    plan=json.loads((batch/'plan.json').read_text(encoding='utf-8'))
    results=[]
    for trial in plan['trials']:
        path=batch/f"trial-{trial['id']:03}"/'outcome.json'
        if not path.exists():
            results.append({'trial':trial['id'],'status':'not_started'});continue
        outcome=json.loads(path.read_text(encoding='utf-8'))
        if not outcome.get('conversation'):
            results.append({'trial':trial['id'],'status':'no_completed_start'});continue
        base=Path(outcome['conversation'])
        state=json.loads((base/'state.json').read_text(encoding='utf-8'))
        if state.get('private_start') or Path(state['case']).is_absolute():
            raise ValueError('This diagnostic is restricted to named public scenarios.')
        turn=base/'turns/001-start'
        info=json.loads((turn/'turn.json').read_text(encoding='utf-8'))
        snap=json.loads((turn/'snapshots.json').read_text(encoding='utf-8'))
        audit=workflow_audit.onboarding(info,snap['before'],snap['after'],state['workspace'])
        results.append({'trial':trial['id'],'status':'reviewed' if info['completed'] else 'no_completed_start',
                        'legacy_status':outcome.get('opening',{}).get('opening_status'),
                        'v2':audit,'turn_sha256':conversation.image_inputs.digest(turn/'turn.json'),
                        'snapshots_sha256':conversation.image_inputs.digest(turn/'snapshots.json')})
    result={'version':workflow_audit.VERSION,'scope':'Additional diagnostics; historical artifacts and scores unchanged.',
            'plan_sha256':conversation.image_inputs.digest(batch/'plan.json'),'trials':results}
    with destination.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    return {'trials':len(results),'started':sum(r['status']=='reviewed' for r in results),
            'v2_formats':dict(Counter(r['v2']['format_status'] for r in results if r['status']=='reviewed')),
            'observed_pauses':sum(r.get('v2',{}).get('observed_pause',False) for r in results)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('batch',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(review(a.batch,a.out)))
