import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'eval/runner'))
import opening_v9 as grader
import opening_v3
import workflow_audit
import test_opening_v8 as previous

SOURCE = previous.SOURCE
path_cases = previous.path_cases
ADDED = (
    'The [skill’s chat-start rules]({source}) require one reply before setup and processing.',
    'The [skill instructions]({source}) require one response before document work.',
    'The [skill instructions]({source}) require this question and one reply before processing.',
    'The [skill instructions]({source}) require waiting for one reply before extraction.',
    'The [skill instructions]({source}) say “Wait for a reply.” This requires one reply before I can begin setup and processing.',
    'Under the [skill instructions]({source}), I must wait for one response before document work.',
)
POSITIVE = previous.POSITIVE + ADDED
NEGATIVE = previous.NEGATIVE + (
    'The [skill instructions]({source}) require one more reply before processing.',
    'The [skill instructions]({source}) require one additional reply before processing.',
    'The [skill instructions]({source}) require another reply before processing.',
    'The [skill instructions]({source}) require one Yes reply before processing.',
    'The [skill instructions]({source}) require one affirmative response before processing.',
    'The [skill instructions]({source}) require one reply before processing. Please confirm again.',
    'The [skill instructions]({source}) require one reply before processing if you agree.',
    'The [skill instructions]({source}) require only one reply before processing.',
    'The [skill instructions]({source}) require one reply before processing and uploading files.',
    'The [skill instructions]({source}) require one reply before processing, followed by another reply.',
    'The [skill instructions]({source}) say “Wait.” This requires one reply before I can begin processing. Only Yes permits it.',
    'The [skill instructions]({source}) require one response before processing. Reading verified.',
)
APPENDED = previous.APPENDED


class OneReply(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='confirmation-');self.addCleanup(self.temp.cleanup)
        self.work=Path(self.temp.name)

    def audit(self,note,host=True,commands=None,after=None):
        text='\n'.join((workflow_audit.QUESTION,*workflow_audit.CHOICES,note))
        return grader.audit({'completed':True,'commands':commands or [],'agent_messages':[opening_v3.ANNOUNCEMENT,text]},
                            {},after or {},self.work,{'disclosure_required':host})

    def test_language_matrix_preserves_all_previous_cases(self):
        sources=[SOURCE]
        if os.name=='nt':sources.append('/'+(self.work/SOURCE).as_posix())
        for source in sources:
            for text in POSITIVE:
                with self.subTest(source=source,text=text):
                    self.assertTrue(grader.disclosure(text.format(source=source),self.work)[0])
                    for suffix in APPENDED:
                        self.assertFalse(grader.disclosure(text.format(source=source)+suffix,self.work)[0])
            for text in NEGATIVE:
                with self.subTest(source=source,text=text):
                    self.assertFalse(grader.disclosure(text.format(source=source),self.work)[0])

    def test_new_wording_paths_host_wait_and_original_grade(self):
        note=ADDED[0].format(source=SOURCE)
        self.assertTrue(self.audit(note)['automatic_pass'])
        self.assertEqual(self.audit(note)['v8_format_status'],'requires_review')
        for source,accepted in path_cases(self.work):
            with self.subTest(source=source):
                self.assertEqual(self.audit(ADDED[0].format(source=source))['automatic_pass'],accepted)
        for kwargs in ({'host':False},{'commands':['Get-Content invoice.pdf']},{'after':{'custom.md':'new'}}):
            self.assertFalse(self.audit(note,**kwargs)['automatic_pass'])
        self.assertFalse(self.audit(note+'\n'+note)['automatic_pass'])
        malformed='\n'.join((workflow_audit.QUESTION,'Yes',workflow_audit.CHOICES[1],note))
        self.assertFalse(grader.audit({'completed':True,'commands':[],'agent_messages':[malformed]}, {},{},self.work,{'disclosure_required':True})['automatic_pass'])

    def test_new_wording_rejects_resolved_source_escape(self):
        original=Path.resolve;root=self.work/'.agents/skills/invoice-reader-openai'
        for redirect in (root,root/'SKILL.md',root/'references/chat-start.md'):
            def resolve(path,*args,**kwargs):
                return self.work/'outside'/path.name if path==redirect else original(path,*args,**kwargs)
            with self.subTest(redirect=redirect),patch.object(Path,'resolve',resolve):
                source=(root/'references/chat-start.md' if redirect.name=='chat-start.md' else root/'SKILL.md').as_posix()
                self.assertFalse(self.audit(ADDED[0].format(source=source))['automatic_pass'])

    def test_rewrite_preserves_link_and_quote(self):
        line='The [one reply]('+SOURCE+') says “wait for one reply.” This requires one reply before processing.'
        with patch.object(grader.opening_v8,'disclosure',side_effect=[(False,'unsupported_application_clause'),(False,'unsupported_source_label')]) as check:
            self.assertFalse(grader.disclosure(line,self.work)[0])
            rewritten=check.call_args_list[1].args[0]
            self.assertIn('[one reply]('+SOURCE+')',rewritten)
            self.assertIn('“wait for one reply.”',rewritten)
            self.assertTrue(rewritten.endswith('requires a reply before processing.'))


if __name__=='__main__':unittest.main()
