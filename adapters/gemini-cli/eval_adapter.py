"""Preparation-only Gemini CLI adapter; live telemetry is not yet qualified."""
COMMAND = 'gemini'
INSTALL_DIR = '.invoice-reader/packages'


def command(executable, model, prompt, images=()):
    if images:
        raise ValueError('Page attachment integration is not validated for this adapter.')
    args = [executable]
    if model:
        args += ['--model', model]  # Explicit benchmark selection, never skill metadata.
    return args + ['-p', prompt]


def analyse(stdout):
    # Do not mistake a plausible JSON response for qualified live evidence.
    return {'completed': False, 'models_reported_by_cli': [], 'usage': {},
            'error': 'Preparation-only adapter: use an interactive smoke test; staged live evaluation is not implemented.'}
