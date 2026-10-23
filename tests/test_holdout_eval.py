import json
from pathlib import Path
import sys
import tempfile
import shutil
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'eval/runner'))
import holdout


class HoldoutEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.source=self.folder/'source.pdf';self.source.write_bytes(b'controlled test source')
        (self.folder/'case.toml').write_text('source = '+json.dumps(str(self.source))+'\n')
        (self.folder/'custom.md').write_text('fixed settings')
        (self.folder/'expected.json').write_text(json.dumps({'tables':{'test':{}},'raw_tables':{'test':{}}}))

    def freeze(self,**updates):
        args=dict(source_id='new',original_source_hash='new-hash',excluded_source_ids=['old'],
                  excluded_source_hashes=['old-hash'],artifact_hash='package')
        args.update(updates)
        return holdout.freeze(self.folder,**args)

    def test_source_novelty_and_no_overwrite(self):
        for changes in ({'source_id':'old'},{'original_source_hash':'old-hash'}):
            with self.assertRaisesRegex(ValueError,'already participated'):self.freeze(**changes)
        self.freeze()
        with self.assertRaisesRegex(ValueError,'already frozen'):self.freeze()

    def test_changed_answer_source_or_package_rejected(self):
        self.freeze();holdout.verify(self.folder,'package')
        with self.assertRaisesRegex(ValueError,'Package differs'):holdout.verify(self.folder,'new-package')
        self.source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed after freeze'):holdout.verify(self.folder,'package')

    def test_impossible_workbook_identity_rejected_before_model_run(self):
        expected={'tables':{'Line items':{'identity':['File','Nonexistent column','Line'],
                                         'columns':[], 'rows':[]}}, 'raw_tables':{'test':{}}}
        (self.folder/'expected.json').write_text(json.dumps(expected))
        with self.assertRaisesRegex(ValueError,'Unsupported Line items'):self.freeze()
        self.assertFalse((self.folder/'holdout-lock.json').exists())

    def test_unclear_abstention_does_not_reward_missing_record(self):
        row={'File':'source.pdf','Pages':'1','Document type':'Cheque','Document occurrence':'1',
             'Field key':'amount','Occurrence':'1','observation.status':'unclear'}
        expected={'raw_tables':{'Raw requested values':{'identity':[k for k in row if k!='observation.status'],'rows':[row]}}}
        doc={'document_id':'a','file':'source.pdf','pages':'1','document_type':'Cheque','fields':{},
             'custom_fields':{'amount':[{'status':'unclear','pages':'1'}]}}
        payload={'schema_version':1,'documents':[doc]}
        self.assertEqual(holdout.abstention(payload,expected)['abstention_rate'],1)
        doc['custom_fields']['amount'][0]={'status':'printed','value':'guessed','pages':'1','evidence':'unsupported'}
        self.assertEqual(holdout.abstention(payload,expected)['unsupported_filled'],1)
        doc['custom_fields']={}
        result=holdout.abstention(payload,expected)
        self.assertEqual(result['missing_or_ambiguous_observation'],1)
        self.assertEqual(result['abstention_rate'],0)

    def test_regression_preserves_old_lock_and_rejects_changed_source_or_review(self):
        self.freeze()
        original = (self.folder/'holdout-lock.json').read_bytes()
        target = self.folder/'regression'; target.mkdir()
        for name in ('case.toml','custom.md','expected.json'):
            shutil.copyfile(self.folder/name, target/name)
        review = target/'scope.json'; review.write_text('{"scope":"confirmed amounts only"}')
        lock = holdout.freeze_regression(target, previous_case=self.folder, artifact_hash='new-package',
                                         reference_status='mixed-owner-and-provisional', review_files=[review])
        self.assertEqual(lock['evaluation_kind'],'known-source-regression')
        self.assertEqual((self.folder/'holdout-lock.json').read_bytes(),original)
        holdout.verify(target,'new-package')
        with self.assertRaisesRegex(ValueError,'already frozen'):
            holdout.freeze_regression(target, previous_case=self.folder, artifact_hash='new-package', reference_status='owner-verified')
        review.write_text('changed')
        with self.assertRaisesRegex(ValueError,'changed after freeze'):holdout.verify(target,'new-package')

    def test_regression_cannot_substitute_a_different_pdf(self):
        self.freeze(); target=self.folder/'different'; target.mkdir()
        other=target/'other.pdf'; other.write_bytes(b'different source')
        (target/'case.toml').write_text('source = '+json.dumps(str(other))+'\n')
        with self.assertRaisesRegex(ValueError,'exact previously frozen source'):
            holdout.freeze_regression(target, previous_case=self.folder, artifact_hash='new-package', reference_status='owner-verified')
