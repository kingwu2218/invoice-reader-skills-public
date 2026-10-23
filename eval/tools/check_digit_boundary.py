"""Score supplied transcriptions and injected errors; never call a model.

python eval/tools/check_digit_boundary.py --out eval/runs/digit-boundary-controls
"""
import argparse
from contextlib import redirect_stdout
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

from make_digit_boundary_case import ROOT, NAME, FILE, control_payload
sys.path.insert(0,str(ROOT/'eval/runner'))
sys.path.insert(0,str(ROOT/'tools'))
import raw
import score
import process
import skillsets


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(out):
    scenario=ROOT/'eval/scenarios'/NAME
    paths=[ROOT/'eval/fixtures'/FILE,scenario/'case.toml',scenario/'custom.md',scenario/'expected.json']
    locked={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    expected=json.loads((scenario/'expected.json').read_text())
    out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for mode in ('correct','added-digit','removed-digit','guessed-total','guessed-custom'):
        folder=out/mode;folder.mkdir()
        data=control_payload()
        if mode=='added-digit':data['documents'][0]['fields']['total']='1684'
        if mode=='removed-digit':data['documents'][1]['fields']['total']='684'
        if mode=='guessed-total':data['documents'][2]['fields']['total']='8684'
        if mode=='guessed-custom':data['documents'][2]['custom_fields']['labelled_total'][0]['value']='8684'
        source=folder/'extraction.json';source.write_text(json.dumps(data,indent=2),encoding='utf-8')
        before=digest(source)
        manifest=folder/'manifest.json'
        manifest.write_text(json.dumps({'version':1,'inputs':[{'file':FILE,'extraction':'extraction.json'}]}),encoding='utf-8')
        log=io.StringIO()
        with redirect_stdout(log):
            code=process.main(['--manifest',str(manifest),'--custom',str(scenario/'custom.md'),
                               '--out',str(folder/'output.xlsx')])
        (folder/'processor.txt').write_text(log.getvalue(),encoding='utf-8')
        rejected=mode=='guessed-custom'
        if code!=(2 if rejected else 0) or digest(source)!=before:
            raise ValueError('Unexpected processing result or changed supplied transcription.')
        if rejected and (folder/'output.xlsx').exists():raise ValueError('Invalid custom guess produced a workbook.')
        results={'raw':raw.score(data,expected['raw_tables'],score.score_table),
                 'workbook':None if rejected else score.score_workbook(folder/'output.xlsx',expected)}
        row={'control':mode,'model_execution':False,'processor_exit_code':code,
             'workbook_status':'rejected-invalid-input' if rejected else 'created',
             'raw_sha256':before,'workbook_sha256':None if rejected else digest(folder/'output.xlsx')}
        for layer,result in results.items():
            if result is None:
                row.update({f'{layer}_{o}':None for o in score.OUTCOMES})
                row[f'{layer}_denominator']=None;row[f'{layer}_rate']=None
                continue
            counts=result['cells'];denominator=sum(counts[o] for o in score.OUTCOMES if o!='correct_blank')
            row.update({f'{layer}_{o}':counts[o] for o in score.OUTCOMES})
            row[f'{layer}_denominator']=denominator
            row[f'{layer}_rate']=counts['correct']/denominator
            if mode=='correct' and (result['details'] or any(result['checks'].values()) or
                    any(t.get('missing',0) or t.get('extra',0) for t in result['tables'].values())):
                raise ValueError('Correct control failed scoring or structure checks.')
        if mode!='correct' and not results['raw']['details']:raise ValueError('Injected error escaped raw scoring.')
        rows.append(row)
    if locked!={p.relative_to(ROOT).as_posix():digest(p) for p in paths}:raise ValueError('Frozen fixture changed.')
    result={'evaluation_kind':'deterministic-supplied-transcription-controls','case':NAME,
            'source_pages':3,'model_runs':0,'model_requested':None,'model_reported':None,'provider':None,
            'fixture_sha256':locked,'processor_sha256':digest(ROOT/'core/scripts/process.py'),
            'packages':{p['name']:{'version':p['version'],'sha256':skillsets.tree_hash(skillsets.package_path(p))}
                        for p in skillsets.load_registry()},'rows':rows,
            'limitations':['Supplied transcriptions and deliberate mutations; not recognition or prompt accuracy.',
                           'Three synthetic printed raster pages in one content group, reused across five controls.',
                           'Correct blanks excluded; raw and workbook cells are correlated checks.']}
    (out/'accuracy-matrix.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    with (out/'accuracy-matrix.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({'controls':len(rows),'injected_errors_detected':len(rows)-1,'model_runs':0}))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    run(parser.parse_args().out)
