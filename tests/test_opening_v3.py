import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'eval/runner'))
import opening_v3 as grader
import workflow_audit as strict


class CodexOpening(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.work=Path(self.temp.name)
        self.question='\n'.join((strict.QUESTION,*strict.CHOICES))
        self.note='The [skill instructions](.agents/skills/invoice-reader-openai/SKILL.md) require a reply before setup or processing.'

    def audit(self,text,required=True):
        return grader.audit({'completed':True,'commands':[],'agent_messages':[text]}, {},{},self.work,{'disclosure_required':required})

    def test_allowed_disclosure_keeps_original_review_visible(self):
        r=self.audit(grader.ANNOUNCEMENT+'\n'+self.question+'\n'+self.note)
        self.assertTrue(r['automatic_pass']);self.assertEqual(r['strict_v2_format'],'requires_review')
        self.assertEqual(r['format_status'],'host_disclosure')

    def test_disclosure_needs_host_evidence_and_correct_source(self):
        self.assertFalse(self.audit(self.question+'\n'+self.note,False)['automatic_pass'])
        for target in ('https://example.com/SKILL.md','custom.md','.agents/skills/another/SKILL.md','.agents/skills/invoice-reader-openai/scripts/process.py'):
            note=self.note.replace('.agents/skills/invoice-reader-openai/SKILL.md',target)
            self.assertFalse(self.audit(self.question+'\n'+note)['automatic_pass'])

    def test_extra_confirmation_second_explanation_and_coercion_fail(self):
        for extra in ('\nProceed?', '\n'+self.note, ' Only Yes allows me to continue.', ' Please confirm again.'):
            self.assertFalse(self.audit(self.question+'\n'+self.note+extra)['automatic_pass'])
        self.assertFalse(self.audit(self.question+'\n'+self.note.replace('a reply','Yes'))['automatic_pass'])

    def test_order_repetition_and_changed_choices_fail(self):
        for text in (self.note+'\n'+self.question,self.question+'\n'+strict.QUESTION,
                     self.question.replace(strict.CHOICES[0],'Yes'),self.question+'\n'+grader.ANNOUNCEMENT):
            self.assertFalse(self.audit(text)['automatic_pass'])
        self.assertTrue(self.audit(self.question)['automatic_pass'])

    def test_quoted_wait_rule_and_actual_instruction_reads(self):
        note='The skill’s [chat response rules](.agents/skills/invoice-reader-openai/references/chat-start.md) require: “End the response and wait for a reply before document work.”'
        self.assertTrue(self.audit(self.question+'\n'+note)['automatic_pass'])
        info={'completed':True,'commands':['Get-Content invoice.pdf'],'agent_messages':[self.question+'\n'+self.note]}
        self.assertFalse(grader.audit(info,{},{},self.work,{'disclosure_required':True})['automatic_pass'])
        info['commands']=[]
        self.assertFalse(grader.audit(info,{}, {'custom.md':'new'},self.work,{'disclosure_required':True})['automatic_pass'])

    def test_host_rule_requires_matching_session_metadata(self):
        trace=self.work/'trace.jsonl'
        trace.write_text(json.dumps({'type':'session_meta','payload':{'id':'s','base_instructions':{'text':grader.HOST_RULE}}}),encoding='utf-8')
        self.assertTrue(grader.host_evidence(trace,'s')['disclosure_required'])
        self.assertFalse(grader.host_evidence(trace,'other')['disclosure_required'])
        trace.write_text(json.dumps({'type':'response_item','payload':{'id':'s','base_instructions':grader.HOST_RULE}}),encoding='utf-8')
        self.assertFalse(grader.host_evidence(trace,'s')['disclosure_required'])


if __name__=='__main__':unittest.main()
