"""Claude Code CLI eval adapter; use a fresh workspace and restricted tool list."""
import json

COMMAND = 'claude'
INSTALL_DIR = '.claude/skills'
# v1 (2026-10-10 baseline) also allowed PowerShell; v2 is Bash-only (see session_allowed);
# v3 adds the environment note below to the first prompt, chosen by the project owner after
# Sonnet stopped on denied combined commands. The package and its instructions are unchanged.
# v3.1 also allows the supplied interpreter path written without quotes.
SESSION_HARNESS = 'claude-session-v3.1'
# Evaluator-provided environment facts, like the interpreter path; never document content.
SESSION_ENVIRONMENT_NOTE = (
    'Evaluation environment: commands are not prompted for approval. A Bash call is pre-approved only when it '
    'runs exactly one of the skill scripts, with uv run or the interpreter named here, and a literal path, with no cd, '
    '&&, ;, pipes, shell variables or echo; ordinary file reads and writes in this folder are allowed. A denied combined '
    'command does not mean other commands are blocked: run each script as its own call. This is evaluator-provided '
    'environment information, not document content.')
# Every script the package's tool.md tells the agent to run. uv runs the
# PEP 723 scripts; an existing interpreter runs the PDF capability/route helpers.
SCRIPTS = ('check_setup.py', 'new_profile.py', 'new_custom.py', 'new_run.py', 'render_pages.py', 'process.py',
           'reading_capabilities.py', 'pdf_routes.py')


def command(executable, model, prompt):
    allowed = ['Read', 'Glob', 'Grep', 'Write', 'Edit']
    for script in ('check_setup.py', 'new_profile.py', 'new_custom.py', 'new_run.py', 'render_pages.py', 'process.py'):
        for shell in ('Bash', 'PowerShell'):
            allowed.append(f'{shell}(uv run *invoice-reader-*scripts*{script}*)')
    return [executable, '-p', prompt, '--model', model, '--output-format', 'stream-json', '--verbose',
            '--permission-mode', 'dontAsk', '--allowedTools', *allowed,
            '--disallowedTools', 'Write(./.claude/**)', 'Edit(./.claude/**)', 'WebFetch', 'WebSearch',
            '--no-session-persistence', '--max-turns', '60']


def session_allowed(python=None):
    """Workspace-scoped writes and the package's own scripts; reads outside the workspace stay denied.

    Bash only: in non-interactive mode Claude Code matched no allow rule against a PowerShell
    `& "<interpreter>" script.py` call (checked with CLI 2.1.286), so the PDF helpers were denied there.
    """
    allowed = ['Write(./**)', 'Edit(./**)']
    # The supplied path may be written with either separator; no other interpreter is allowed.
    spellings = sorted({python.replace('\\', '/'), python.replace('/', '\\')}) if python else []
    for script in SCRIPTS:
        allowed.append(f'Bash(uv run *invoice-reader-*scripts*{script}*)')
        allowed.extend(f'Bash("{path}" *invoice-reader-*scripts*{script}*)' for path in spellings)
        # The same interpreter written without quotes is an equally literal single command
        # when its path has no spaces (v3 denied it, which stopped or rerouted Sonnet runs).
        allowed.extend(f'Bash({path} *invoice-reader-*scripts*{script}*)' for path in spellings if ' ' not in path)
    return allowed


def session_command(executable, model, prompt, session_id, resume=False, python=None, max_turns=150):
    """One persisted benchmark chat: fix its ID on the first turn and resume that exact ID, never --continue.

    Project/local settings only, so personal skills, plugins and memory do not join the
    evaluated context. The user's selected model is passed through unchanged.
    """
    if not session_id:
        raise ValueError('An explicit session ID is required.')
    args = [executable, '-p', prompt, '--model', model, '--output-format', 'stream-json', '--verbose',
            '--setting-sources', 'project,local', '--permission-mode', 'dontAsk',
            '--allowedTools', *session_allowed(python),
            '--disallowedTools', 'Write(./.claude/**)', 'Edit(./.claude/**)', 'WebFetch', 'WebSearch', 'Agent', 'Task',
            'PowerShell',
            '--max-turns', str(max_turns)]
    return args + (['--resume', session_id] if resume else ['--session-id', session_id])


def analyse(stdout):
    models, completed = set(), False
    sessions, messages, tools, denials, transport = set(), [], [], [], []
    result = {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event.get('session_id'), str):
            sessions.add(event['session_id'])
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            result['init_model'] = event.get('model')
            result['skills_visible'] = event.get('skills', [])
        if event.get('type') == 'assistant':
            message = event.get('message', {})
            if message.get('model') == '<synthetic>':
                # CLI-inserted notice (e.g. "Connection lost mid-response"), not a model's output.
                # The run cannot be shown complete; keep it out of messages and model identity.
                transport.extend(b.get('text', '') for b in message.get('content', []) if b.get('type') == 'text')
                continue
            models.add(message.get('model', 'unknown'))
            for block in message.get('content', []):
                if block.get('type') == 'text' and block.get('text', '').strip():
                    messages.append(block['text'])
                elif block.get('type') == 'tool_use':
                    tools.append({'name': block.get('name'), 'input': block.get('input')})
        if event.get('type') == 'result':
            completed = event.get('subtype') == 'success' and not event.get('is_error')
            denials = event.get('permission_denials') or []
            result.update(result_subtype=event.get('subtype'), num_turns=event.get('num_turns'),
                          total_cost_usd=event.get('total_cost_usd'), usage=event.get('usage'),
                          duration_ms=event.get('duration_ms'))
    if transport:
        completed = False
        result['transport_error'] = transport
    return {'models_reported_by_cli': sorted(models), 'completed': completed, **result,
            'session_ids': sorted(sessions), 'agent_messages': messages, 'tool_uses': tools,
            'permission_denials': denials}
