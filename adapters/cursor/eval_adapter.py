"""Cursor adapter for the shared xAI prompt.

Print-mode arguments follow the Cursor CLI parameter and output-format docs
reviewed on 2026-10-11. This adapter never passes --model or an effort flag.
A successful result event is completion telemetry, not accuracy or verified identity.
"""
import json

COMMAND = 'agent'
INSTALL_DIR = '.cursor/skills'


def command(executable, model, prompt, images=()):
    if images:
        raise ValueError('CLI page attachment is not validated. Inspect rendered PNGs with the image tool after the policy reply.')
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('Cursor print mode requires a prompt.')
    # The shared preparer passes a requested model. It stays metadata and is not a CLI override.
    del model
    return [executable, '-p', '--output-format', 'stream-json', '--trust', prompt]


def _events(stdout):
    events = []
    for line in str(stdout or '').splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            item = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def _text(message):
    content = message.get('content') if isinstance(message, dict) else None
    if not isinstance(content, list):
        return ''
    return ''.join(part.get('text', '') for part in content
                   if isinstance(part, dict) and part.get('type') == 'text')


def analyse(stdout):
    events = _events(stdout)
    inits = [event for event in events if event.get('type') == 'system' and event.get('subtype') == 'init']
    results = [event for event in events if event.get('type') == 'result']
    success = [event for event in results if event.get('subtype') == 'success' and event.get('is_error') is False]
    session_ids = []
    for event in inits + results:
        session_id = event.get('session_id')
        if isinstance(session_id, str) and session_id and session_id not in session_ids:
            session_ids.append(session_id)
    models = []
    for event in inits:
        reported = event.get('model')
        if isinstance(reported, str) and reported and reported not in models:
            models.append(reported)
    messages = [_text(event.get('message')) for event in events if event.get('type') == 'assistant']
    messages = [message for message in messages if message]
    tools = []
    image_tool_returned_content = False
    for event in events:
        if event.get('type') != 'tool_call':
            continue
        call = event.get('tool_call') if isinstance(event.get('tool_call'), dict) else {}
        name = next(iter(call), None) if call else None
        record = {'subtype': event.get('subtype'), 'tool': name, 'call_id': event.get('call_id')}
        if name == 'readToolCall':
            body = call.get('readToolCall') if isinstance(call.get('readToolCall'), dict) else {}
            args = body.get('args') if isinstance(body.get('args'), dict) else {}
            path = str(args.get('path') or '')
            record['path'] = path
            result = body.get('result') if isinstance(body.get('result'), dict) else {}
            success_body = result.get('success') if isinstance(result.get('success'), dict) else {}
            content = success_body.get('content')
            record['result_kind'] = 'text' if isinstance(content, str) else ('absent' if content is None else type(content).__name__)
            # Documented read results are text. A path or transcript is not image content.
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')) and isinstance(content, (bytes, bytearray)):
                image_tool_returned_content = True
        tools.append(record)
    same_session = not inits or inits[0].get('session_id') == (session_ids[0] if session_ids else None)
    completed = len(success) == 1 and len(session_ids) == 1 and same_session
    usage = {}
    if completed and isinstance(success[0].get('duration_ms'), int):
        usage = {'duration_ms': success[0]['duration_ms']}
    return {'completed': completed, 'models_reported_by_cli': models, 'usage': usage,
            'session_ids': session_ids, 'agent_messages': messages, 'tool_calls': tools,
            'api_key_source': inits[0].get('apiKeySource') if inits else None,
            'image_tool_returned_content': image_tool_returned_content,
            'error': None if completed else 'Cursor stream did not end with one successful result and one session ID.'}
