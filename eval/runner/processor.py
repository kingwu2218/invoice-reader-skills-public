"""Deterministic amount-dash regression matrix; no model invocation or source PDFs.

Usage: python eval/runner/processor.py
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

import score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import skillsets
CASE = ROOT/'eval/processor-cases/amount-dash-v1'
MIXED = ROOT/'eval/processor-cases/amount-dash-v3'
SCRIPTS = ROOT/'core/scripts'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    batch = ROOT/'eval/runs'/('processor-dash-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:6])
    script_hashes = {p.relative_to(SCRIPTS).as_posix(): digest(p) for p in SCRIPTS.rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts}
    artifact = hashlib.sha256(json.dumps(script_hashes, sort_keys=True).encode()).hexdigest()
    cases = [('default-missing-origin', None, CASE/'extraction.json', CASE/'expected-unknown.json')]
    cases += [(mode, mode, CASE/'extraction.json', CASE/f'expected-{mode}.json')
              for mode in ('unknown', 'end-mark', 'negative')]
    cases += [('mixed-'+mode, None, MIXED/f'extraction-{source}.json', MIXED/f'expected-{mode}.json')
              for mode, source in [('auto', 'mixed'), ('end-mark', 'end-mark'), ('negative', 'negative')]]
    for name, mode, source, reference in cases:
        folder = batch/name/'run-1'; folder.mkdir(parents=True)
        shutil.copyfile(source, folder/'extraction.json')
        shutil.copyfile(CASE/'custom.md', folder/'custom.md')
        shutil.copyfile(reference, folder/'expected.json')
        fixed = {name:digest(folder/name) for name in ('extraction.json','custom.md','expected.json')}
        command = [sys.executable,str(SCRIPTS/'process.py'),'--extraction',str(folder/'extraction.json'),
                   '--custom',str(folder/'custom.md'),'--out',str(folder/'output.xlsx')]
        if mode is not None:
            command.extend(['--amount-dash', mode])
        result = subprocess.run(command,capture_output=True,text=True)
        (folder/'stdout.txt').write_text(result.stdout,encoding='utf-8')
        (folder/'stderr.txt').write_text(result.stderr,encoding='utf-8')
        intact = all(digest(folder/name)==value for name,value in fixed.items())
        unchanged = all(digest(SCRIPTS/name)==value for name,value in script_hashes.items())
        meta = {'valid':result.returncode==0 and (folder/'output.xlsx').exists() and intact and unchanged,
                'evaluation_type':'deterministic-processor','model_requested':'Not applicable',
                'model_reported':'Not applicable','provider':'Local Python; no model call','tool':'python',
                'scenario':'amount-dash-v3/'+name,'category':'supplied-transcription','content_group':'invented-amount-dash',
                'artifact_version':skillsets.core_version(), 'artifact_hash':artifact,
                'script_hashes':script_hashes,'input_hashes':fixed,
                'dataset_hash':hashlib.sha256(json.dumps(fixed,sort_keys=True).encode()).hexdigest(),
                'amount_dash':mode or 'auto','amount_dash_selection':mode or 'default',
                'reference_source':reference.relative_to(ROOT).as_posix(),
                'raw_input_unchanged':intact,'scripts_unchanged':unchanged,
                'exit_code':result.returncode,'invocation':command,'python_version':sys.version,
                'image_input_mode':'not_captured','note':'No visual/model accuracy measured. Raw JSON is supplied input.'}
        (folder/'meta.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    report = score.score_batch(batch)
    failed = any(not r['valid'] or r.get('details') or any(r.get('checks',{}).values()) or
                 r.get('flags',{}).get('false_negative',0) or r.get('flags',{}).get('false_positive',0)
                 for r in report['runs'])
    print(json.dumps({'batch':str(batch),'summary':report['summary'],'passed':not failed}))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(run())
