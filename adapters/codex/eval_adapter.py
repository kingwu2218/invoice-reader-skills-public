"""Codex CLI eval adapter. The maintainer explicitly selects the benchmark model."""
import json
import re

COMMAND = 'codex'
INSTALL_DIR = '.agents/skills'


def command(executable, model, prompt, images=()):
    args = [executable, 'exec', '--model', model, '--approve-for-me',
            '--skip-git-repo-check', '--ephemeral', '--ignore-user-config', '--json']
    for image in images:
        args.extend(['--image', str(image)])
    return args + ['--', prompt]


def session_command(executable, model, prompt, session_id=None, images=(), transport='default'):
    """Persist only this benchmark conversation; resume an exact ID, never --last."""
    args = [executable, 'exec', '--approve-for-me', '--ignore-user-config', '--json', '--skip-git-repo-check']
    if transport not in ('default', 'https'):
        raise ValueError('Unknown Codex benchmark transport.')
    if transport == 'https':
        # An explicit diagnostic fallback, keeping the same ChatGPT endpoint/auth.
        # Built-in provider IDs cannot be overridden in current Codex versions.
        args += ['-c', 'model_provider="openai-https"', '-c',
                 'model_providers.openai-https={name="OpenAI",'
                 'base_url="https://chatgpt.com/backend-api/codex",requires_openai_auth=true,'
                 'supports_websockets=false,wire_api="responses"}']
    if session_id:
        args += ['resume']
    args += ['--model', model]
    for image in images:
        args += ['--image', str(image)]
    return args + ['--'] + ([session_id] if session_id else []) + [prompt]


def analyse(stdout):
    models, completed, failed = set(), False, False
    usage = {}
    sessions, messages, commands = set(), [], []
    transport_retries = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event.get('model'), str):
            models.add(event['model'])
        if event.get('type') == 'thread.started' and isinstance(event.get('thread_id'), str):
            sessions.add(event['thread_id'])
        item = event.get('item', {})
        if event.get('type') == 'item.completed':
            if item.get('type') == 'agent_message':
                messages.append(item.get('text', ''))
            elif item.get('type') == 'command_execution':
                commands.append(item.get('command', ''))
        if event.get('type') == 'error':
            message = event.get('message', '')
            # CLI emits transient reconnection notices as error events. They
            # are recoverable only before a later successful turn completion.
            if (not completed and isinstance(message, str) and
                    re.fullmatch(r'Reconnecting\.\.\. \d+/\d+ \(stream disconnected before completion: .+\)', message)):
                transport_retries.append(message)
            else:
                failed = True
        failed |= event.get('type') == 'turn.failed'
        completed |= event.get('type') == 'turn.completed'
        if isinstance(event.get('usage'), dict):
            usage = event['usage']
    return {'models_reported_by_cli': sorted(models), 'completed': completed and not failed, 'usage': usage,
            'session_ids': sorted(sessions), 'agent_messages': messages, 'commands': commands,
            'transport_retries': transport_retries}
