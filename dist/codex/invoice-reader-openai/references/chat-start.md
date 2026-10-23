# Policy question in each chat

At the first skill invocation in each new chat, ask exactly, in English:

> Have you read the Readme about the data policy for your model?

Offer these replies (as choices when supported, otherwise plain text):

- Yes, I have read it.
- No, but I will read it before I upload any confidential data

A brief skill-use announcement may precede the question. End the response and wait for a reply before document work. Loading the skill and its policy instructions is allowed while waiting; document reading, rendering/OCR, setup, custom.md creation and extraction start after a reply. Until the reply, do not list or search folders and do not open any file outside this skill, including custom.md and the company profile: file and folder names can themselves be confidential.

Any user reply satisfies this workflow step, including either option, No, uncertainty or other wording. Continue the requested task without requiring Yes, testing policy understanding or asking for another confirmation. Follow any actual task changes or stop requests in that reply. Silence or an unsubmitted default option is not a reply; do not fabricate one. If the user asks about the policy, answer using the README and family policy reference without demanding an affirmative response.

Keep only chat-local state: not yet asked, awaiting reply, or response received. Do not equate response received with verified reading, a promise, legal consent or permission to upload additional files to another service. Preserve the actual wording if recording it; never relabel No or uncertainty as having read the policy. This is a reminder of the user's responsibility to read the guidance before uploading confidential data.

Ask once per chat. Another batch in that chat does not repeat it. A new chat asks again even with the same files, workspace, custom.md or company profile. `Confirmed by user: yes` in custom.md concerns extraction requirements only. Do not persist policy-response state across chats; retain documented state through compaction within the same chat.

Keep provider/account limitations intact. A non-recommended or unknown model follows the same question and adds no model-specific confirmation or model switch.
