import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eval/runner'))
import first_use
import raw


class FirstUse(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name);self.repo=base/'repo';self.work=base/'external';self.batch=self.repo/'eval/runs/test'
        (self.repo/'eval/fixtures').mkdir(parents=True)
        for name in ('coal-ocr.pdf','coal-scan.pdf'):(self.repo/'eval/fixtures'/name).write_bytes(b'public-test')
        shutil.copytree(ROOT/'eval/workflows/first-use-v1',self.repo/'eval/workflows/first-use-v1')
        self.package=self.repo/'package';self.package.mkdir();(self.package/'SKILL.md').write_text('test skill')
        self.patch=patch.object(first_use,'REPO',self.repo);self.patch.start();self.addCleanup(self.patch.stop)
        self.pkg=patch.object(first_use,'package',return_value=({'version':'test'},self.package));self.pkg.start();self.addCleanup(self.pkg.stop)
        self.version=patch.object(first_use.subprocess,'run',return_value=SimpleNamespace(stdout='test-cli'));self.version.start();self.addCleanup(self.version.stop)

    def plan(self):return first_use.plan(self.batch,self.work,'selected','provider','https')

    def test_no_prefilled_settings_answers_or_profile(self):
        self.plan()
        for work in self.work.iterdir():
            self.assertEqual({p.name for p in work.iterdir()},{'.agents','coal-ocr.pdf'})
        data=json.loads((self.batch/'plan.json').read_text())
        self.assertEqual(len(data['trials']),3)
        self.assertEqual(data['opening_contract'],'codex-opening-v9')
        for t in data['trials']:
            for answer in ('COAL-001','105.00','6,200','expected.json'):
                self.assertNotIn(answer,t['prompt'])

    def test_repository_workspace_and_existing_folders_rejected(self):
        with self.assertRaises(ValueError):first_use.plan(self.batch,self.repo/'test','m','p','https')
        self.work.mkdir()
        with self.assertRaises(ValueError):self.plan()
        self.assertFalse(self.batch.exists())

    def test_reference_drift_and_failed_attempt_cannot_be_replaced(self):
        self.plan()
        with patch.object(first_use.conversation,'invoke',side_effect=RuntimeError('failed transport')) as invoke:
            self.assertEqual(first_use.execute(self.batch,1,'start')['status'],'incomplete')
            with self.assertRaises(FileExistsError):first_use.execute(self.batch,1,'start')
            self.assertEqual(invoke.call_count,1)
        (self.batch/'trial-2/expected.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'reference changed'):first_use.load(self.batch,2)

    def test_raw_label_identity_does_not_depend_on_model_key(self):
        payload={'documents':[{'file':'public.pdf','pages':'1','document_type':'Invoice',
                'fields':{},'custom_fields':{'chosen_key':[{'status':'printed','value':'ABC','pages':'1','evidence':'ABC'}]}}]}
        old=raw.tables(payload)['Raw requested values'][0]
        self.assertNotIn('Field',old)
        labelled=raw.tables(payload,{'chosen_key':'Invoice number'})['Raw requested values'][0]
        self.assertEqual(labelled['Field'],'Invoice number');self.assertEqual(labelled['observation.value'],'ABC')
        definition={'Raw requested values':{'identity':['File','Pages','Field','Occurrence'],
            'columns':[{'label':'observation.value','kind':'text'}],
            'rows':[{'File':'public.pdf','Pages':'1','Field':'Invoice number','Occurrence':'1','observation.value':'ABC'}]}}
        good=raw.score(payload,definition,first_use.score.score_table,{'chosen_key':'Invoice number'})
        wrong=raw.score(payload,definition,first_use.score.score_table,{'chosen_key':'Wrong label'})
        self.assertEqual(good['cells']['correct'],1)
        self.assertEqual(wrong['cells']['correct'],0)
        self.assertEqual(wrong['tables']['Raw requested values'].get('matched',0),0)

    def test_unexecuted_report_keeps_missing_scores_undefined(self):
        self.plan()
        target=self.batch/'public.json'
        result=first_use.report(self.batch,target)
        self.assertEqual(result['completed_batches'],0)
        self.assertEqual(result['planned_batches'],4)
        for layer in ('raw','workbook'):
            self.assertIsNone(result['totals'][layer]['denominator'])
            self.assertEqual(result['totals'][layer]['scored_batches'],0)
        published=json.loads(target.read_text(encoding='utf-8'))
        self.assertTrue(all(not row['installed_instruction_reads_observed'] for row in published['openings']))
        self.assertNotIn(str(self.work),target.read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):first_use.report(self.batch,target)

    def test_existing_csv_is_not_partially_overwritten(self):
        self.plan()
        target=self.batch/'public.json';target.with_suffix('.csv').write_text('earlier evidence')
        with self.assertRaises(ValueError):first_use.report(self.batch,target)
        self.assertFalse(target.exists())

    def test_changed_opening_grader_cannot_continue_frozen_plan(self):
        self.plan()
        actual_digest=first_use.digest
        def changed(path):
            if Path(path)==Path(first_use.OPENING_GRADER.__file__):return 'changed-grader'
            return actual_digest(path)
        with patch.object(first_use,'digest',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'opening grader changed'):first_use.load(self.batch,1)

    def test_changed_opening_dependency_cannot_continue_frozen_plan(self):
        self.plan()
        with patch.object(first_use,'opening_dependencies',return_value={'workflow_audit.py':'changed'}):
            with self.assertRaisesRegex(ValueError,'dependency changed'):first_use.load(self.batch,1)


if __name__=='__main__':unittest.main()
