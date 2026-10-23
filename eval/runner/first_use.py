"""Public first-use chats: model creates custom.md and extraction, outside the repo.

plan freezes three chats and their references. start/reply/followup reserve one
attempt each; failed or inaccurate outputs are never overwritten or retried.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import conversation
import raw
import score
import workflow_audit
import opening_v3
import opening_v4
import opening_v5
import opening_v6
import opening_v7
import opening_v8
import opening_v9
from custom_fields import read_fields

REPO = conversation.baseline.REPO
VERSION = 'first-use-v1'
OPENING_GRADER = opening_v9
OPENING_GRADERS = {module.VERSION:module for module in (opening_v3,opening_v4,opening_v5,opening_v6,opening_v7,opening_v8,opening_v9)}


def opening_dependencies(version=None):
    modules = (opening_v3,workflow_audit)
    if (version or OPENING_GRADER.VERSION) in (opening_v5.VERSION,opening_v6.VERSION,opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION): modules += (opening_v4,)
    if (version or OPENING_GRADER.VERSION) in (opening_v6.VERSION,opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION): modules += (opening_v5,)
    if (version or OPENING_GRADER.VERSION) in (opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION): modules += (opening_v6,)
    if (version or OPENING_GRADER.VERSION) in (opening_v8.VERSION,opening_v9.VERSION): modules += (opening_v7,)
    if (version or OPENING_GRADER.VERSION) == opening_v9.VERSION: modules += (opening_v8,)
    return {Path(module.__file__).name:digest(Path(module.__file__)) for module in modules}

PURPOSES = {
    'payment': 'I need a payment follow-up list. Use the column names "Invoice number" and "Payment due date". Take the invoice number from the invoice itself, not an invoice reference printed on a supporting certificate. Keep dates as printed. Treat both requested fields as optional; leave missing information blank.',
    'energy': 'I need to compare certificate results. Use the column names "Energy Level of Coal" and "Moisture". Keep every sample, its printed sample label and unit; do not convert units. Treat both requested fields as optional; leave missing information blank.',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, default=str)


def package():
    entry = next(e for e in conversation.baseline.skillsets.load_registry() if e['name']=='invoice-reader-openai')
    return entry, conversation.baseline.skillsets.package_path(entry)


def expected(purpose, source):
    text = (REPO/'eval/workflows'/VERSION/(purpose+'.json')).read_text(encoding='utf-8')
    return json.loads(text.replace('coal-ocr.pdf', source))


def prompt(purpose, source='coal-ocr.pdf', output='output.xlsx'):
    return (f'Use $invoice-reader-openai to read {source}. {PURPOSES[purpose]} '
            f'Create custom.md for these requirements and save {output}. '
            'I do not need sales/purchase direction, so proceed without a company profile. '
            'Keep the standard document sheets too. Please handle the setup and processing for me.')


def plan(batch, workspace_root, model, provider, transport):
    workspace_root = workspace_root.resolve()
    if workspace_root.is_relative_to(REPO.resolve()) or REPO.resolve().is_relative_to(workspace_root):
        raise ValueError('Use a new workspace root outside the repository and its ancestors.')
    if batch.exists() or workspace_root.exists():
        raise ValueError('Batch and workspace root must both be new; preserve previous evidence.')
    if not model.strip() or not provider.strip() or transport not in ('default','https'):
        raise ValueError('Explicit benchmark model, provider/account route and valid transport required.')
    entry, source_package = package()
    hashes = {p.relative_to(REPO).as_posix():digest(p) for p in
              [REPO/'eval/fixtures/coal-ocr.pdf',REPO/'eval/fixtures/coal-scan.pdf',
               REPO/'eval/workflows'/VERSION/'payment.json',REPO/'eval/workflows'/VERSION/'energy.json']}
    batch.mkdir(parents=True)
    workspace_root.mkdir(parents=True)
    trials=[]
    for number, purpose in enumerate(('payment','energy','payment'),1):
        work=workspace_root/f'chat-{number}';work.mkdir()
        installed=work/'.agents/skills/invoice-reader-openai'
        shutil.copytree(source_package,installed)
        shutil.copyfile(REPO/'eval/fixtures/coal-ocr.pdf',work/'coal-ocr.pdf')
        trial=batch/f'trial-{number}';trial.mkdir()
        save_new(trial/'expected.json',expected(purpose,'coal-ocr.pdf'))
        if number==1:save_new(trial/'followup-expected.json',expected(purpose,'coal-scan.pdf'))
        trials.append({'id':number,'purpose':purpose,'workspace':str(work),
                       'prompt':prompt(purpose),'followup':number==1,
                       'initial_snapshot':conversation.snapshot(work)})
    data={'schema_version':1,'protocol':VERSION,'opening_contract':OPENING_GRADER.VERSION,
          'opening_grader_sha256':digest(Path(OPENING_GRADER.__file__)),
          'opening_dependency_hashes':opening_dependencies(),'package_version':entry['version'],
          'artifact_hash':conversation.baseline.skillsets.tree_hash(source_package),'fixture_hashes':hashes,
          'model_requested':model,'provider':provider,'transport':transport,'trials':trials,
          'harness_hashes':{name:digest(REPO/name) for name in ('eval/runner/first_use.py','eval/runner/workflow_audit.py','eval/runner/opening_v3.py','eval/runner/opening_v4.py','eval/runner/opening_v5.py','eval/runner/opening_v6.py','eval/runner/opening_v7.py','eval/runner/opening_v8.py','eval/runner/opening_v9.py','eval/runner/raw.py','eval/runner/score.py','eval/runner/conversation.py','adapters/codex/eval_adapter.py') if (REPO/name).exists()},
          'reply_actor':'scripted_negative_fixture','reply':conversation.READ_LATER,
          'tool_version':subprocess.run(['codex','--version'],capture_output=True,text=True,encoding='utf-8',errors='replace').stdout.strip(),
          'scope':'Three fresh CLI sessions; public known sources, model-created settings, no prefilled profile/extraction, no answer files in model workspaces. Existing host tooling/auth retained; global host instructions may remain visible.'}
    save_new(batch/'plan.json',data)
    (batch/'plan.sha256').write_text(digest(batch/'plan.json'))
    return {'batch':str(batch),'trials':len(trials),'workspace_root':str(workspace_root)}


def load(batch, number):
    if digest(batch/'plan.json')!=(batch/'plan.sha256').read_text(encoding='utf-8'):raise ValueError('Frozen plan changed.')
    data=json.loads((batch/'plan.json').read_text(encoding='utf-8'))
    grader=OPENING_GRADERS.get(data.get('opening_contract'))
    if grader and data.get('opening_grader_sha256')!=digest(Path(grader.__file__)):
        raise ValueError('Frozen opening grader changed.')
    if data.get('opening_dependency_hashes') is not None and data['opening_dependency_hashes']!=opening_dependencies(data.get('opening_contract')):
        raise ValueError('Frozen opening grader dependency changed.')
    if any(digest(REPO/name)!=value for name,value in data['fixture_hashes'].items()):raise ValueError('Frozen references changed.')
    if conversation.baseline.skillsets.tree_hash(package()[1])!=data['artifact_hash']:raise ValueError('Package changed.')
    trial=next(t for t in data['trials'] if t['id']==number)
    folder=batch/f'trial-{number}'
    for name,source in [('expected.json','coal-ocr.pdf'),('followup-expected.json','coal-scan.pdf')]:
        if name=='expected.json' or trial['followup']:
            if json.loads((folder/name).read_text(encoding='utf-8'))!=expected(trial['purpose'],source):raise ValueError('Frozen trial reference changed.')
    return data,trial,folder


def capture_trace(session_id, target):
    root=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'sessions'
    matches=list(root.rglob('*'+session_id+'*.jsonl'))
    if len(matches)!=1:return {'status':'unavailable','reason':'Exact session trace is missing or ambiguous.'}
    path=matches[0]
    with path.open(encoding='utf-8') as stream:
        meta=json.loads(stream.readline())
    if meta.get('type')!='session_meta' or meta.get('payload',{}).get('id')!=session_id:
        return {'status':'unavailable','reason':'Trace session identity mismatch.'}
    shutil.copyfile(path,target/'session-trace.jsonl')
    with (target/'session-trace.jsonl').open(encoding='utf-8') as stream:
        evidence=workflow_audit.image_evidence(stream)
    evidence['trace_sha256']=digest(target/'session-trace.jsonl')
    return evidence


def execute(batch, number, action):
    data,trial,folder=load(batch,number)
    work=Path(trial['workspace'])
    # Reserving an action is permanent, even if a transport or process fails.
    save_new(folder/(action+'-attempt.json'),{'action':action,'protocol':VERSION})
    result={'action':action,'status':'incomplete','model_reported':'Unknown'}
    try:
        session=None
        if action=='start':
            if conversation.snapshot(work)!=trial['initial_snapshot']:raise ValueError('Initial workspace changed.')
            text=trial['prompt']
        else:
            initial=json.loads((folder/'start-result.json').read_text(encoding='utf-8'))
            session=initial['session_id']
            if action=='reply':
                audit=initial['opening_v2']
                if not audit['observed_pause'] or not audit['exact_question_once'] or not audit['both_exact_choices_once']:
                    raise ValueError('Opening needs trace review; no automatic reply was sent.')
                text=data['reply']
            elif action=='followup':
                if not trial['followup']:raise ValueError('This trial has no planned second batch.')
                prior=json.loads((folder/'reply-result.json').read_text(encoding='utf-8'))
                if not prior.get('extraction',{}).get('output_present'):raise ValueError('No initial workbook to preserve.')
                shutil.copyfile(REPO/'eval/fixtures/coal-scan.pdf',work/'coal-scan.pdf')
                text=('Please process the new coal-scan.pdf as a second batch using the same requirements in custom.md. '
                      'Save output-second.xlsx and preserve the earlier workbook. Continue without a company profile.')
            else:raise ValueError('Unknown action.')
        state={'workspace':str(work),'model_requested':data['model_requested'],
               'codex_transport':data['transport'],'execution_timeout_seconds':1200}
        before_manifests={str(p.resolve()):digest(p) for p in (work/'invoice-reader-work').glob('*/manifest.json')}
        prior_outputs={p.name:digest(p) for p in work.glob('*.xlsx')}
        custom_before=digest(work/'custom.md') if (work/'custom.md').exists() else None
        info,before,after=conversation.invoke(state,text,folder/action,session)
        result.update(status='recorded',completed=info['completed'],exit_code=info['exit_code'],
                      elapsed_seconds=info['elapsed_seconds'],session_ids=info['session_ids'],
                      model_reported=', '.join(info['models_reported_by_cli']) or 'Unknown',
                      policy_question_count=sum(m.count(conversation.QUESTION) for m in info['agent_messages']))
        if len(info['session_ids'])==1:
            result['session_id']=info['session_ids'][0]
            result['image_evidence']=capture_trace(result['session_id'],folder/action)
        if action=='start':
            result['opening_legacy']=conversation.onboarding(info,before,after,first=True,contract=conversation.RESPONSE_CONTRACT)
            result['opening_v2']=workflow_audit.onboarding(info,before,after,work)
            if data.get('opening_contract') in OPENING_GRADERS:
                result['opening_v3']=opening_v3.audit(info,before,after,work,
                    opening_v3.host_evidence(folder/action/'session-trace.jsonl',result.get('session_id')))
                if data['opening_contract'] in (opening_v4.VERSION,opening_v5.VERSION,opening_v6.VERSION,opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION):
                    result['opening_v4']=opening_v4.audit(info,before,after,work,
                        opening_v4.host_evidence(folder/action/'session-trace.jsonl',result.get('session_id')))
                if data['opening_contract'] in (opening_v5.VERSION,opening_v6.VERSION,opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION):
                    result['opening_v5']=opening_v5.audit(info,before,after,work,
                        opening_v5.host_evidence(folder/action/'session-trace.jsonl',result.get('session_id')))
                if data['opening_contract'] in (opening_v6.VERSION,opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION):
                    result['opening_v6']=opening_v6.audit(info,before,after,work,
                        opening_v6.host_evidence(folder/action/'session-trace.jsonl',result.get('session_id')))
                if data['opening_contract'] in (opening_v7.VERSION,opening_v8.VERSION,opening_v9.VERSION):
                    result['opening_v7']=opening_v7.audit(info,before,after,work,
                        opening_v7.host_evidence(folder/action/'session-trace.jsonl',result.get('session_id')))
                if data['opening_contract'] in (opening_v8.VERSION,opening_v9.VERSION):
                    result['opening_v8']=opening_v8.audit(info,before,after,work,
                        opening_v8.host_evidence(folder/action/'session-trace.jsonl',result.get('session_id')))
                if data['opening_contract']==opening_v9.VERSION:
                    result['opening_v9']=opening_v9.audit(info,before,after,work,
                        opening_v9.host_evidence(folder/action/'session-trace.jsonl',result.get('session_id')))
        else:
            result['reply_actor']=data['reply_actor'] if action=='reply' else 'scripted_public_followup'
            result['same_session']=info['session_ids']==[session]
            result['prior_outputs_unchanged']=all((work/n).exists() and digest(work/n)==h for n,h in prior_outputs.items())
            result['custom_reused_unchanged']=(digest(work/'custom.md')==custom_before) if action=='followup' and (work/'custom.md').exists() else None
            result['extraction']=evaluate(work,folder,action,before_manifests)
        result['package_unchanged']=conversation.baseline.skillsets.tree_hash(work/'.agents/skills/invoice-reader-openai')==data['artifact_hash']
        result['original_source_unchanged']=digest(work/'coal-ocr.pdf')==data['fixture_hashes']['eval/fixtures/coal-ocr.pdf']
    except Exception as exc:
        result['error']=f'{type(exc).__name__}: {exc}'
    save_new(folder/(action+'-result.json'),result)
    return result


def counts(result):
    cells=result['cells']; denominator=sum(cells[x] for x in score.OUTCOMES if x!='correct_blank')
    return {'correct':cells['correct'],'denominator':denominator,'correct_blank':cells['correct_blank'],
            'cells':dict(cells),'tables':result['tables'],'checks':dict(result['checks'])}


def evaluate(work,folder,action,before_manifests):
    dest=folder/(action+'-artifacts');dest.mkdir()
    output=work/('output-second.xlsx' if action=='followup' else 'output.xlsx')
    exp=json.loads((folder/('followup-expected.json' if action=='followup' else 'expected.json')).read_text(encoding='utf-8'))
    result={'output_present':output.exists(),'custom_created':(work/'custom.md').is_file()}
    if output.exists():
        shutil.copyfile(output,dest/output.name); result['workbook_sha256']=digest(output)
        r=score.score_workbook(output,exp);result['workbook']=counts(r)
        save_new(dest/'workbook-score.json',r)
    try:
        fields=read_fields(work/'custom.md');shutil.copyfile(work/'custom.md',dest/'custom.md')
        result['custom_fields']=[{'label':f['label'],'values':f['values'],'required':f['required']} for f in fields]
        manifests=[p for p in (work/'invoice-reader-work').glob('*/manifest.json') if str(p.resolve()) not in before_manifests]
        if len(manifests)!=1:raise ValueError('Expected exactly one new manifest for this batch; none selected heuristically.')
        manifest=manifests[0]
        payload,coverage=raw.read_manifest(manifest)
        conversation.save(dest/'raw-extraction.json',{'schema_version':1,**payload})
        result['raw_coverage']=coverage; result['raw_manifest']=manifest.relative_to(work).as_posix()
        r=raw.score(payload,exp['raw_tables'],score.score_table,{f['key']:f['label'] for f in fields})
        result['raw']=counts(r);save_new(dest/'raw-score.json',r)
        shutil.copytree(manifest.parent,dest/'run-evidence',ignore=shutil.ignore_patterns('__pycache__'))
    except (ValueError,OSError) as exc:result['raw_error']=str(exc)
    return result


def report(batch, destination):
    """Public aggregate only; detailed traces/paths stay in the local batch."""
    csv_path=destination.with_suffix('.csv')
    if destination.suffix.lower()!='.json' or destination.exists() or csv_path.exists():
        raise ValueError('Use a new .json report destination and matching unused .csv path.')
    data=json.loads((batch/'plan.json').read_text(encoding='utf-8'))
    rows=[]; openings=[]
    for trial in data['trials']:
        _,_,folder=load(batch,trial['id'])
        start_path=folder/'start-result.json'
        start=json.loads(start_path.read_text(encoding='utf-8')) if start_path.exists() else {}
        audit=start.get('opening_v2',{})
        openings.append({'trial':trial['id'],'completed':start.get('completed',False),
                         'legacy_status':start.get('opening_legacy',{}).get('opening_status'),
                         'opening_v3':start.get('opening_v3'),
                         'opening_v4':start.get('opening_v4'),
                         'opening_v5':start.get('opening_v5'),
                         'opening_v6':start.get('opening_v6'),
                         'opening_v7':start.get('opening_v7'),
                         'opening_v8':start.get('opening_v8'),
                         'opening_v9':start.get('opening_v9'),
                         **{k:audit.get(k) for k in ('exact_question_once','both_exact_choices_once','format_status','observed_pause','automatic_pass')},
                         'installed_instruction_reads_observed':bool(audit.get('observed_pause')) and bool(start.get('opening_legacy',{})) and bool(
                             json.loads((folder/'start/turn.json').read_text(encoding='utf-8')).get('commands')),
                         'evidence_sha256':digest(start_path) if start_path.exists() else None})
        previous_calls=set()
        for action in (('reply','followup') if trial['followup'] else ('reply',)):
            path=folder/(action+'-result.json')
            r=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            extraction=r.get('extraction',{})
            calls=r.get('image_evidence',{}).get('calls',[])
            images=sum(c['returned_images'] for c in calls if c['call_id'] not in previous_calls)
            previous_calls.update(c['call_id'] for c in calls)
            source='coal-scan.pdf' if action=='followup' else 'coal-ocr.pdf'
            coverage=extraction.get('raw_coverage',[])
            coverage_ok=len(coverage)==1 and coverage[0].get('file')==source and coverage[0].get('status')=='Processed'
            labels=['Invoice number','Payment due date'] if trial['purpose']=='payment' else ['Energy Level of Coal','Moisture']
            fields=extraction.get('custom_fields',[])
            custom_ok=[f['label'] for f in fields]==labels and all(not f['required'] for f in fields)
            source_path=Path(trial['workspace'])/source
            source_ok=source_path.exists() and digest(source_path)==data['fixture_hashes']['eval/fixtures/'+source]
            complete=all((r.get('completed'),r.get('same_session'),r.get('package_unchanged'),source_ok,
                          extraction.get('output_present'),extraction.get('custom_created'),coverage_ok,custom_ok,
                          r.get('prior_outputs_unchanged'),r.get('policy_question_count')==0))
            row={'trial':trial['id'],'phase':action,'purpose':trial['purpose'],'source':source,
                 'status':r.get('status','not_recorded'),'core_delivery_complete':complete,
                 'same_session':r.get('same_session'),'policy_questions_after_reply':r.get('policy_question_count'),
                 'coverage_matches_request':coverage_ok,'custom_matches_requested_labels':custom_ok,
                 'custom_reused_unchanged':r.get('custom_reused_unchanged'),
                 'prior_outputs_unchanged':r.get('prior_outputs_unchanged'),'package_unchanged':r.get('package_unchanged'),
                 'source_unchanged':source_ok,'new_tool_returned_images':images,
                 'elapsed_seconds':r.get('elapsed_seconds'),'model_reported':r.get('model_reported','Unknown'),
                 'result_sha256':digest(path) if path.exists() else None,
                 'workbook_sha256':extraction.get('workbook_sha256'),
                 'trace_sha256':r.get('image_evidence',{}).get('trace_sha256')}
            for layer in ('raw','workbook'):
                layer_data=extraction.get(layer,{})
                for key in ('correct','denominator','correct_blank'):row[layer+'_'+key]=layer_data.get(key)
                row[layer+'_checks']=layer_data.get('checks')
                row[layer+'_tables']=layer_data.get('tables')
            if r.get('error'):row['error_type']=r['error'].split(':',1)[0]
            rows.append(row)
    totals={}
    for layer in ('raw','workbook'):
        scored=[r for r in rows if r[layer+'_denominator'] is not None]
        totals[layer]={'scored_batches':len(scored),**{key:sum(r[layer+'_'+key] for r in scored) if scored else None
                       for key in ('correct','denominator','correct_blank')}}
    result={'protocol':VERSION,'workflow_grader':workflow_audit.VERSION,'planned_chats':len(data['trials']),
            'planned_batches':len(rows),'completed_batches':sum(r['core_delivery_complete'] for r in rows),
            'package_version':data['package_version'],'package_sha256':data['artifact_hash'],
            'requested_model':data['model_requested'],'provider':data['provider'],'tool_version':data['tool_version'],
            'plan_sha256':digest(batch/'plan.json'),'fixture_hashes':data['fixture_hashes'],
            'execution_harness_hashes':data['harness_hashes'],
            'reporter_sha256':digest(Path(__file__)),'openings':openings,'rows':rows,'totals':totals,
            'scope':data['scope'],
            'limitations':['Known synthetic content; same source reused across purposes/formats.',
                           'Opening text requiring review remains separate from core delivery completion.',
                           'Image returns are observed tool evidence, not proof of attention.',
                           'Requested model is not verified runtime identity.']}
    save_new(destination,result)
    columns=[k for k in rows[0] if not k.endswith(('_tables','_checks'))]
    with csv_path.open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    return {'planned_batches':len(rows),'completed_batches':result['completed_batches'],'totals':totals}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    s=sub.add_parser('plan');s.add_argument('batch',type=Path);s.add_argument('--workspace-root',type=Path,required=True)
    s.add_argument('--model',required=True);s.add_argument('--provider',required=True);s.add_argument('--transport',choices=('default','https'),default='https')
    for action in ('start','reply','followup'):
        s=sub.add_parser(action);s.add_argument('batch',type=Path);s.add_argument('--trial',type=int,required=True)
    s=sub.add_parser('report');s.add_argument('batch',type=Path);s.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.action=='plan':r=plan(a.batch,a.workspace_root,a.model,a.provider,a.transport)
    elif a.action=='report':r=report(a.batch,a.out)
    else:r=execute(a.batch,a.trial,a.action)
    print(json.dumps(r,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
