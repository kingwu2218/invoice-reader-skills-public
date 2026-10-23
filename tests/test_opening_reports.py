import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eval/tools'))
import review_first_use_openings as reviewer


class OpeningReports(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.batch=Path(self.temp.name)

    def plan(self,grader):
        data={'trials':[{'id':1,'workspace':str(self.batch/'work')}],
              'opening_contract':grader.VERSION,'opening_grader_sha256':reviewer.digest(Path(grader.__file__)),
              'opening_dependency_hashes':{Path(g.__file__).name:reviewer.digest(Path(g.__file__)) for g in (reviewer.opening_v3,reviewer.workflow_audit)},
              'package_version':'test','artifact_hash':'test'}
        p=self.batch/'plan.json';p.write_text(json.dumps(data),encoding='utf-8');(self.batch/'plan.sha256').write_text(reviewer.digest(p))

    def test_old_contract_is_not_silently_upgraded(self):
        self.plan(reviewer.opening_v3);target=self.batch/'old.json';reviewer.review(self.batch,target)
        data=json.loads(target.read_text());self.assertEqual(data['version'],'codex-opening-v3');self.assertEqual(data['automatic_passes'],0)
        target=self.batch/'regrade.json';reviewer.review(self.batch,target,'codex-opening-v4')
        self.assertIn('not a prospectively frozen',json.loads(target.read_text())['timing'])

    def test_new_contract_freezes_and_preserves_outputs(self):
        self.plan(reviewer.opening_v4);target=self.batch/'new.json';reviewer.review(self.batch,target)
        self.assertIn('frozen in the pre-execution plan',json.loads(target.read_text())['timing'])
        with self.assertRaises(ValueError):reviewer.review(self.batch,target)

    def test_v5_requires_v4_dependency_and_preserves_v4_plans(self):
        self.plan(reviewer.opening_v5)
        target=self.batch/'missing-dependency.json';reviewer.review(self.batch,target)
        self.assertIn('not a prospectively frozen',json.loads(target.read_text())['timing'])
        plan=self.batch/'plan.json';data=json.loads(plan.read_text())
        data['opening_dependency_hashes']['opening_v4.py']=reviewer.digest(Path(reviewer.opening_v4.__file__))
        plan.write_text(json.dumps(data));(self.batch/'plan.sha256').write_text(reviewer.digest(plan))
        target=self.batch/'frozen.json';reviewer.review(self.batch,target)
        self.assertIn('frozen in the pre-execution plan',json.loads(target.read_text())['timing'])

    def test_v6_requires_all_dependencies(self):
        self.plan(reviewer.opening_v6)
        plan=self.batch/'plan.json';data=json.loads(plan.read_text())
        data['opening_dependency_hashes']['opening_v4.py']=reviewer.digest(Path(reviewer.opening_v4.__file__))
        plan.write_text(json.dumps(data));(self.batch/'plan.sha256').write_text(reviewer.digest(plan))
        target=self.batch/'missing-v5.json';reviewer.review(self.batch,target)
        self.assertIn('not a prospectively frozen',json.loads(target.read_text())['timing'])
        data['opening_dependency_hashes']['opening_v5.py']=reviewer.digest(Path(reviewer.opening_v5.__file__))
        plan.write_text(json.dumps(data));(self.batch/'plan.sha256').write_text(reviewer.digest(plan))
        target=self.batch/'v6-frozen.json';reviewer.review(self.batch,target)
        self.assertIn('frozen in the pre-execution plan',json.loads(target.read_text())['timing'])


    def test_v7_requires_v6_dependency(self):
        self.plan(reviewer.opening_v7)
        plan=self.batch/'plan.json';data=json.loads(plan.read_text())
        for module in (reviewer.opening_v4,reviewer.opening_v5):
            data['opening_dependency_hashes'][Path(module.__file__).name]=reviewer.digest(Path(module.__file__))
        plan.write_text(json.dumps(data));(self.batch/'plan.sha256').write_text(reviewer.digest(plan))
        target=self.batch/'missing-v6.json';reviewer.review(self.batch,target)
        self.assertIn('not a prospectively frozen',json.loads(target.read_text())['timing'])
        data['opening_dependency_hashes']['opening_v6.py']=reviewer.digest(Path(reviewer.opening_v6.__file__))
        plan.write_text(json.dumps(data));(self.batch/'plan.sha256').write_text(reviewer.digest(plan))
        target=self.batch/'v7-frozen.json';reviewer.review(self.batch,target)
        self.assertIn('frozen in the pre-execution plan',json.loads(target.read_text())['timing'])


    def test_v8_requires_v7_dependency(self):
        self.plan(reviewer.opening_v8)
        plan=self.batch/'plan.json';data=json.loads(plan.read_text())
        for module in (reviewer.opening_v4,reviewer.opening_v5,reviewer.opening_v6):
            data['opening_dependency_hashes'][Path(module.__file__).name]=reviewer.digest(Path(module.__file__))
        plan.write_text(json.dumps(data));(self.batch/'plan.sha256').write_text(reviewer.digest(plan))
        target=self.batch/'missing-v7.json';reviewer.review(self.batch,target)
        self.assertIn('not a prospectively frozen',json.loads(target.read_text())['timing'])
        data['opening_dependency_hashes']['opening_v7.py']=reviewer.digest(Path(reviewer.opening_v7.__file__))
        plan.write_text(json.dumps(data));(self.batch/'plan.sha256').write_text(reviewer.digest(plan))
        target=self.batch/'v8-frozen.json';reviewer.review(self.batch,target)
        self.assertIn('frozen in the pre-execution plan',json.loads(target.read_text())['timing'])


    def test_v9_requires_v8_dependency(self):
        self.plan(reviewer.opening_v9)
        plan=self.batch/'plan.json';data=json.loads(plan.read_text())
        for module in (reviewer.opening_v4,reviewer.opening_v5,reviewer.opening_v6,reviewer.opening_v7):
            data['opening_dependency_hashes'][Path(module.__file__).name]=reviewer.digest(Path(module.__file__))
        plan.write_text(json.dumps(data));(self.batch/'plan.sha256').write_text(reviewer.digest(plan))
        target=self.batch/'missing-v8.json';reviewer.review(self.batch,target)
        self.assertIn('not a prospectively frozen',json.loads(target.read_text())['timing'])
        data['opening_dependency_hashes']['opening_v8.py']=reviewer.digest(Path(reviewer.opening_v8.__file__))
        plan.write_text(json.dumps(data));(self.batch/'plan.sha256').write_text(reviewer.digest(plan))
        target=self.batch/'v9-frozen.json';reviewer.review(self.batch,target)
        self.assertIn('frozen in the pre-execution plan',json.loads(target.read_text())['timing'])


if __name__=='__main__':unittest.main()
