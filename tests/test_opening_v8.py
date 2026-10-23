import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'eval/runner'))
import opening_v8 as grader
import opening_v3
import test_opening_v7 as previous

SOURCE = previous.SOURCE
path_cases = previous.path_cases
ADDED = (
    'The [skill instructions]({source}) require this question and a reply before setup or document processing.',
    'The [skill’s chat-start rule]({source}) says to “End the response and wait for a reply before document work.” This requires a reply before I can begin setup and processing.',
    'The [skill instructions]({source}) require this question and your response before reading the documents.',
    'The [skill instructions]({source}) require this question and any reply before processing: “after asking, end the response and wait.”',
    'The [skill instructions]({source}) say “Wait for your reply.” This rule requires your response before I can start extraction.',
    'The [skill instructions]({source}) require “Wait for a reply.” That requires a reply before I can begin document work.',
)
POSITIVE = previous.POSITIVE + ADDED
NEGATIVE = previous.NEGATIVE + (
    'The [skill instructions]({source}) require this question and a Yes reply before processing.',
    'The [skill instructions]({source}) require this question and your confirmation before processing.',
    'The [skill instructions]({source}) require another question and a reply before processing.',
    'The [skill instructions]({source}) require this question and another reply before processing.',
    'The [skill instructions]({source}) require this question and a reply before processing, if you agree.',
    'The [skill instructions]({source}) require this question and a reply before processing. Please confirm again.',
    'The [skill instructions]({source}) say “Wait.” This requires an affirmative reply before I can begin processing.',
    'The [skill instructions]({source}) say “Wait.” This requires a reply before I can begin processing if you agree.',
    'The [skill instructions]({source}) say “Wait.” This requires a reply before I can begin processing and uploading your files.',
    'The [skill instructions]({source}) say “Wait.” This requires a reply before I can begin processing. I need another reply.',
    'The [skill instructions]({source}) say “Wait.” This requires a reply before I cannot begin processing.',
    'The [skill instructions]({source}) say “Wait.” This requires a reply before I can only begin processing.',
)
APPENDED = previous.APPENDED


class QuestionAndCapability(previous.SourceLinks):
    def audit(self, note, host=True, commands=None, before=None, after=None):
        return grader.audit({'completed': True, 'commands': commands or [],
            'agent_messages': [opening_v3.ANNOUNCEMENT, self.question + '\n' + note]},
            before or {}, after or {}, self.work, {'disclosure_required': host})

    def test_new_forms_and_negative_conditions_in_both_path_spellings(self):
        sources=[SOURCE]
        if os.name == 'nt': sources.append('/'+(self.work/SOURCE).as_posix())
        for source in sources:
            for text in POSITIVE:
                with self.subTest(source=source, text=text):
                    self.assertTrue(self.audit(text.format(source=source))['automatic_pass'])
                    for suffix in APPENDED:
                        self.assertFalse(self.audit(text.format(source=source)+suffix)['automatic_pass'])
            for text in NEGATIVE:
                with self.subTest(source=source, text=text):
                    self.assertFalse(self.audit(text.format(source=source))['automatic_pass'])

    def test_new_forms_preserve_paths_host_wait_and_previous_grade(self):
        for text in ADDED[:2]:
            note=text.format(source=SOURCE)
            self.assertEqual(self.audit(note)['v7_format_status'],'requires_review')
            for source,accepted in path_cases(self.work):
                with self.subTest(source=source):
                    self.assertEqual(self.audit(text.format(source=source))['automatic_pass'],accepted)
            for kwargs in ({'host':False},{'commands':['Get-Content invoice.pdf']},{'after':{'custom.md':'new'}}):
                self.assertFalse(self.audit(note,**kwargs)['automatic_pass'])

    def test_rewrite_does_not_change_link_or_quoted_instruction(self):
        # Observe the second validation call, using a mock only for the initial
        # unsupported verdict; actual acceptance is exercised in the tests above.
        note='The [before I can begin]({source}) says “require this question and a reply before I can begin”. This requires a reply before I can begin processing.'
        line=note.format(source=SOURCE)
        with patch.object(grader.opening_v7,'disclosure',side_effect=[(False,'unsupported_application_clause'),(False,'unsupported_source_label')]) as check:
            self.assertFalse(grader.disclosure(line,self.work)[0])
            rewritten=check.call_args_list[1].args[0]
            self.assertIn('[before I can begin]('+SOURCE+')',rewritten)
            self.assertIn('“require this question and a reply before I can begin”',rewritten)
            self.assertTrue(rewritten.endswith('before I begin processing.'))


if __name__ == '__main__': unittest.main()
