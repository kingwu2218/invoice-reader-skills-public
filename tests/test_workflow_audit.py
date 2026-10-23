import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'eval/runner'))
import workflow_audit as audit


class WorkflowAudit(unittest.TestCase):
    def test_markdown_and_numbered_choices_preserve_exact_content(self):
        result = audit.opening(['**'+audit.QUESTION+'**\n1. '+audit.CHOICES[0]+'\n2. '+audit.CHOICES[1]])
        self.assertEqual(result['format_status'], 'question_only')

    def test_missing_changed_and_repeated_choices_fail(self):
        for choices in ([audit.CHOICES[0]], list(audit.CHOICES)*2, ['Yes', audit.CHOICES[1]]):
            self.assertEqual(audit.opening([audit.QUESTION+'\n'+'\n'.join(choices)])['format_status'], 'invalid')

    def test_repeated_question_fails_and_extra_prose_needs_review(self):
        text=audit.QUESTION+'\n'+'\n'.join(audit.CHOICES)
        self.assertEqual(audit.opening([text, audit.QUESTION])['format_status'], 'invalid')
        r=audit.opening([text+'\nOnly Yes allows me to continue.'])
        self.assertTrue(r['exact_question_once']); self.assertEqual(r['format_status'], 'requires_review')

    def test_static_combined_reads_only(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix="Get-Content -LiteralPath '.agents/skills/invoice-reader-openai/"
            safe=prefix+"SKILL.md'; "+prefix+"references/chat-start.md'"
            self.assertTrue(audit.instruction_reads_only(safe,directory))
            self.assertTrue(audit.instruction_reads_only('"pwsh.exe" -Command "'+safe+'"',directory))
            self.assertFalse(audit.instruction_reads_only('Remove-Item invoice.pdf; pwsh.exe -Command "'+safe+'"',directory))
            self.assertFalse(audit.instruction_reads_only('unknown.exe -Command "'+safe+'"',directory))
            for cmd in (safe+'; Get-Content custom.md', prefix+"../../../custom.md'",
                        safe+' | Write-Output', prefix+"references/$name.md'", safe+'; Remove-Item file.pdf',
                        prefix+"scripts/process.py'", 'Get-ChildItem', 'Get-Content source.pdf'):
                self.assertFalse(audit.instruction_reads_only(cmd,directory),cmd)

    def test_workspace_changes_and_noninstruction_commands_block_pass(self):
        info={'completed':True,'agent_messages':[audit.QUESTION+'\n'+'\n'.join(audit.CHOICES)],'commands':[]}
        self.assertFalse(audit.onboarding(info,{}, {'custom.md':'hash'},Path.cwd())['automatic_pass'])
        info['commands']=['Get-Content invoice.pdf']
        self.assertFalse(audit.onboarding(info,{}, {},Path.cwd())['observed_pause'])

    def test_pixels_require_bound_tool_output(self):
        def event(payload):return json.dumps({'type':'response_item','payload':payload})
        call=event({'type':'custom_tool_call','name':'exec','call_id':'c','input':'image((await tools.view_image({path:"p.png"})).image_url)'})
        output=event({'type':'custom_tool_call_output','call_id':'c','output':[{'type':'input_image','image_url':'data:image/png;base64,test'}]})
        self.assertEqual(audit.image_evidence([call,output])['returned_images'],1)
        self.assertEqual(audit.image_evidence([output])['status'],'unavailable')
        ledger=event({'type':'message','content':[{'type':'input_image','image_url':'claimed'}]})
        self.assertEqual(audit.image_evidence([call,ledger])['returned_images'],0)


if __name__=='__main__':unittest.main()
