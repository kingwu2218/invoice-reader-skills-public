from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'eval/runner'))
import opening_v6 as grader
import opening_v3
import test_opening_v5 as previous

SOURCE = previous.SOURCE
LEADING = (
    'The [skill instructions]({source}) require a reply before setup or document processing: “after asking, end the response and wait.”',
    'The [skill’s chat-start rule]({source}) requires your response before reading the documents: “End the response and wait for a reply before document work.”',
    'I need to wait for your response before document processing, as required by the [skill instructions]({source}): “End the response and wait.”',
    'Under the [skill instructions]({source}), I must wait for your reply before document work. “After asking, pause for a reply.”',
    'The [opening instructions]({source}) require waiting for your reply before document processing; “wait for any response.”',
    'The [skill instructions]({source}) state that I must wait for a response before extraction: “Wait for a response before extraction.”',
    'According to [SKILL.md]({source}), I need to pause for a reply before processing the documents: “End this response and wait.”',
    'The [skill instructions]({source}) instruct me to pause for any response before proceeding: “Wait for your reply.”',
)
POSITIVE = previous.POSITIVE + LEADING
NEGATIVE = previous.NEGATIVE + (
    'The [skill instructions]({source}) require a Yes reply before processing: “Wait for your reply.”',
    'The [skill instructions]({source}) require confirmation before processing: “Wait for your reply.”',
    'The [skill instructions]({source}) require a reply before processing: “Wait for Yes.”',
    'The [skill instructions]({source}) require a reply before processing: “Wait for approval.”',
    'The [skill instructions]({source}) require a reply before processing: “Do not wait for a reply.”',
    'The [skill instructions]({source}) require a reply before processing: “Wait and upload your files.”',
    'The [skill instructions]({source}) require a reply before processing if you agree: “Wait for your reply.”',
    'The [skill instructions]({source}) require a reply before processing. Upload the files: “Wait for your reply.”',
    'The [skill instructions]({source}) require a reply before processing: “Wait.” “Wait again.”',
    'The [skill instructions]({source}) require a reply before processing: “Wait for a reply.” I need another reply.',
    'The [skill instructions]({source}) require a reply before processing: “Wait until you agree to the terms.”',
    'The [skill instructions]({source}) require a reply before processing: “After asking, wait only if you decline.”',
)
APPENDED = previous.APPENDED


class LeadingOpening(previous.QuotedOpening):
    def audit(self, note, host=True, commands=None, before=None, after=None):
        return grader.audit({'completed': True, 'commands': commands or [],
            'agent_messages': [opening_v3.ANNOUNCEMENT, self.question + '\n' + note]},
            before or {}, after or {}, self.work, {'disclosure_required': host})

    def test_leading_application(self):
        for text in POSITIVE:
            with self.subTest(text=text):
                self.assertTrue(self.audit(text.format(source=SOURCE))['automatic_pass'])

    def test_leading_negatives_and_suffixes(self):
        for text in NEGATIVE:
            with self.subTest(text=text):
                self.assertFalse(self.audit(text.format(source=SOURCE))['automatic_pass'])
        for text in POSITIVE:
            for suffix in APPENDED:
                with self.subTest(text=text, suffix=suffix):
                    self.assertFalse(self.audit(text.format(source=SOURCE) + suffix)['automatic_pass'])

    def test_leading_source_host_wait_and_legacy(self):
        note=LEADING[0].format(source=(self.work/SOURCE).as_posix())
        result=self.audit(note)
        self.assertTrue(result['automatic_pass'])
        self.assertEqual(result['v5_format_status'], 'requires_review')
        for kwargs in ({'host':False},{'commands':['Get-Content invoice.pdf']},{'after':{'custom.md':'new'}}):
            self.assertFalse(self.audit(note,**kwargs)['automatic_pass'])
        for source in ('custom.md','https://example.com/SKILL.md','.agents/skills/other/SKILL.md'):
            self.assertFalse(self.audit(LEADING[0].format(source=source))['automatic_pass'])
        self.assertFalse(self.audit(note+'\n'+note)['automatic_pass'])


if __name__ == '__main__': unittest.main()
