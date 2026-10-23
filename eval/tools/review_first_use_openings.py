"""Write a versioned opening report; never replace frozen opening results."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'eval/runner'))
import opening_v3
import opening_v4
import opening_v5
import opening_v6
import opening_v7
import opening_v8
import opening_v9
import workflow_audit


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))


def review(batch,destination,version=None):
    csv_path=destination.with_suffix('.csv')
    if destination.suffix!='.json' or destination.exists() or csv_path.exists():
        raise ValueError('Use new .json and .csv destinations.')
    if digest(batch/'plan.json')!=(batch/'plan.sha256').read_text(encoding='utf-8'):
        raise ValueError('Frozen plan changed.')
    plan=read(batch/'plan.json');rows=[]
    graders={g.VERSION:g for g in (opening_v3,opening_v4,opening_v5,opening_v6,opening_v7,opening_v8,opening_v9)}
    grader=graders[version or plan.get('opening_contract',opening_v3.VERSION)]
    for trial in plan['trials']:
        folder=batch/f"trial-{trial['id']}";result_path=folder/'start-result.json'
        row={'trial':trial['id'],'status':'not_recorded','automatic_pass':False}
        if result_path.exists():
            result=read(result_path);turn=folder/'start/turn.json';snap_path=folder/'start/snapshots.json'
            trace=folder/'start/session-trace.jsonl'
            if turn.exists() and snap_path.exists():
                snap=read(snap_path);host=grader.host_evidence(trace,result.get('session_id'))
                row.update(status='reviewed',**grader.audit(read(turn),snap['before'],snap['after'],trial['workspace'],host),
                           result_sha256=digest(result_path),turn_sha256=digest(turn),snapshots_sha256=digest(snap_path),
                           trace_sha256=digest(trace) if trace.exists() else None)
        rows.append(row)
    dependencies={Path(g.__file__).name:digest(Path(g.__file__)) for g in (opening_v3,workflow_audit)}
    if grader.VERSION in (opening_v5.VERSION,opening_v6.VERSION,opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION):dependencies['opening_v4.py']=digest(Path(opening_v4.__file__))
    if grader.VERSION in (opening_v6.VERSION,opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION):dependencies['opening_v5.py']=digest(Path(opening_v5.__file__))
    if grader.VERSION in (opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION):dependencies['opening_v6.py']=digest(Path(opening_v6.__file__))
    if grader.VERSION in (opening_v8.VERSION,opening_v9.VERSION):dependencies['opening_v7.py']=digest(Path(opening_v7.__file__))
    if grader.VERSION==opening_v9.VERSION:dependencies['opening_v8.py']=digest(Path(opening_v8.__file__))
    frozen=plan.get('opening_contract')==grader.VERSION and plan.get('opening_grader_sha256')==digest(Path(grader.__file__))
    if grader.VERSION in (opening_v4.VERSION,opening_v5.VERSION,opening_v6.VERSION,opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION):frozen=frozen and plan.get('opening_dependency_hashes')==dependencies
    report={'version':grader.VERSION,'contract_decision':'Owner permits one necessary Codex wait explanation with a source link, 2026-10-11; Versioned bounded recognition excludes additional confirmation and Yes-only conditions; v5 parses quote then application; v6 validates application then quote; v7 checks slash-drive sources; v8 recognises this-question-and-reply and before-I-can-begin prose; v9 accepts one reply/response without added requirements.',
            'timing':'Contract and grader hash frozen in the pre-execution plan.' if frozen else 'Additional grading after these openings were observed; not a prospectively frozen pass.',
            'package_version':plan['package_version'],'package_sha256':plan['artifact_hash'],
            'plan_sha256':digest(batch/'plan.json'),'grader_sha256':digest(Path(grader.__file__)),
            'grader_dependency_hashes':dependencies,
            'reviewer_sha256':digest(Path(__file__)),'planned_chats':len(rows),
            'automatic_passes':sum(r['automatic_pass'] for r in rows),'rows':rows}
    with destination.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    columns=['trial','status','strict_v2_format','format_status','observed_pause','allowed_disclosure','automatic_pass']
    with csv_path.open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    return {'planned_chats':len(rows),'automatic_passes':report['automatic_passes']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('batch',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--grader',choices=(opening_v3.VERSION,opening_v4.VERSION,opening_v5.VERSION,opening_v6.VERSION,opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION))
    args=parser.parse_args();print(json.dumps(review(args.batch,args.out,args.grader)))
