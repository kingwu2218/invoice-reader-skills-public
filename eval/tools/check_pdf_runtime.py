"""Offline public-fixture PDF runtime regression; never scores LLM extraction.

Use --python for an existing environment or --uv for explicit managed setup.
Detailed execution records are local; keep --out under ignored eval/runs/.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def check(package, out, python=None, uv=False):
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    entry = package.resolve()/'scripts/pdf_runtime.py'
    prefix = ['uv', 'run', '--no-project', '--script', str(entry)] if uv else [python, str(entry)]
    calls = []
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')

    def invoke(*args):
        start = time.monotonic()
        r = subprocess.run([*prefix, *args], capture_output=True, text=True, encoding='utf-8',
                           errors='replace', env=env, timeout=240)
        calls.append(dict(arguments=list(args),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,
                          elapsed_seconds=round(time.monotonic()-start,2)))
        return r

    checks = {}
    try:
        p = invoke('probe', '--vision', 'available', '--ocr', 'off')
        capability = json.loads(p.stdout)
        checks['probe_usable'] = p.returncode == 0 and capability['pdf_rendering']['status'] == 'usable'
        names = ('pack', 'scan', 'ocr', 'mixed')
        files = [str(ROOT/f'eval/fixtures/coal-{n}.pdf') for n in names]
        r = invoke('prepare', *files, '--out', str(out/'pages'), '--vision', 'available', '--ocr', 'off', '--dpi', '72')
        report = json.loads((out/'pages/routes.json').read_text(encoding='utf-8'))
        checks['same_environment'] = all(report['capabilities'][k] == capability[k] for k in ('python', 'libraries'))
        checks['all_inputs_prepared'] = r.returncode == 0 and len(report['inputs']) == 4 and all(i['status']=='prepared' for i in report['inputs'])
        checks['all_routes'] = [[p['route'] for p in i['pages']] for i in report['inputs']] == [['A','A'],['B','B'],['C','C'],['A','B']]
        pages = [p for i in report['inputs'] for p in i['pages']]
        checks['all_eight_images'] = len(pages)==8 and all((out/'pages'/p['image']).is_file() for p in pages)
        checks['verification_stays_pending'] = all(p['visual_verification']=='pending' for p in pages)
        r = invoke('render', files[0], '--out', str(out/'recovery'), '--pages', '2', '--rotation', '90', '--crop', '10,20,30,40', '--dpi', '72')
        target = out/'recovery/page-0002.png'
        checks['recovery_rendered'] = r.returncode == 0 and target.is_file()
        before = hashlib.sha256(target.read_bytes()).hexdigest()
        r = invoke('render', files[0], '--out', str(out/'recovery'), '--pages', '2', '--dpi', '72')
        checks['recovery_no_overwrite'] = r.returncode != 0 and hashlib.sha256(target.read_bytes()).hexdigest()==before
        broken = out/'broken.pdf';broken.write_bytes(b'not a PDF')
        r = invoke('prepare', str(broken), files[0], '--out', str(out/'partial'), '--vision', 'available', '--ocr', 'off', '--dpi', '72')
        partial = json.loads((out/'partial/routes.json').read_text(encoding='utf-8'))
        checks['failed_input_retained_later_input_prepared'] = r.returncode==3 and [i['status'] for i in partial['inputs']]==['unprocessed','prepared']
    except Exception as exc:
        checks['execution_error'] = False
        calls.append({'error':str(exc)})
    result = dict(scope='Deterministic rendering/routing only; not extraction accuracy.', mode='managed_uv' if uv else 'existing_python',
                  checks=checks,passed=bool(checks) and all(checks.values()),calls=calls)
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    choice=parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--python');choice.add_argument('--uv',action='store_true')
    parser.add_argument('--package',type=Path,default=ROOT/'dist/codex/invoice-reader-openai')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=check(args.package,args.out,args.python,args.uv)
    print(json.dumps({k:result[k] for k in ('mode','checks','passed')}))
    sys.exit(0 if result['passed'] else 1)
