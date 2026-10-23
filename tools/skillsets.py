"""Compose one family prompt, a tool adapter and the shared runtime."""
import hashlib
import json
import re
import shutil
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE, SKILLS, DIST = ROOT / 'core', ROOT / 'skills', ROOT / 'dist'
README = ROOT / 'README.md'
TABLE_START, TABLE_END = '<!-- sets:start -->', '<!-- sets:end -->'
NAME_RULE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
IGNORED = {'__pycache__', '.DS_Store'}


def load_registry():
    with (ROOT / 'registry.toml').open('rb') as stream:
        registry = tomllib.load(stream)
    families = {}
    for family in registry['family']:
        name = family['name']
        if not NAME_RULE.fullmatch(name) or name in families:
            raise ValueError('Family names must be unique lowercase names')
        families[name] = family
    packages, seen, automatic = [], set(), set()
    for package in registry['package']:
        family = families[package['family']]
        tool, name = package['tool'], package['name']
        if not all(NAME_RULE.fullmatch(value) for value in (tool, name)):
            raise ValueError('Invalid tool or package name')
        if (tool, name) in seen:
            raise ValueError('Duplicate package')
        seen.add((tool, name))
        if package['invocation'] not in ('manual', 'automatic'):
            raise ValueError('Invalid invocation policy')
        if package['invocation'] == 'automatic':
            if tool in automatic:
                raise ValueError('Only one automatic package per tool')
            if family['status'] != 'supported' or not family['last_eval']:
                raise ValueError('Automatic packages require an evaluated supported family')
            automatic.add(tool)
        with (ROOT / 'adapters' / tool / 'adapter.toml').open('rb') as stream:
            adapter = tomllib.load(stream)
        if adapter['invocation_format'] not in ('codex', 'claude', 'grok', 'file', 'cursor'):
            raise ValueError('Unknown adapter invocation format')
        if adapter['invocation_format'] == 'file' and package['invocation'] != 'manual':
            raise ValueError('File-path adapters require manual invocation outside discovery directories')
        packages.append({**family, **package, 'adapter': adapter})
    return packages


def core_version():
    text = (CORE / 'CHANGELOG.md').read_text(encoding='utf-8')
    return re.search(r'^## (\d+\.\d+\.\d+)', text, re.MULTILINE)[1]


def _copy_tree(source, target, exclude=()):
    for path in sorted(source.rglob('*')):
        if path.relative_to(source).parts[0] in exclude:
            continue
        if any(part in IGNORED for part in path.relative_to(source).parts):
            continue
        if path.is_file():
            out = target / path.relative_to(source)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, out)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8'))


def package_path(entry):
    return DIST / entry['tool'] / entry['name']


def compose_prompt(source):
    """Expand local authoring parts into one complete installed entrypoint."""
    text = (source / 'SKILL.md').read_text(encoding='utf-8')
    marker = re.compile(r'^<!-- include: (prompt/[a-z0-9-]+\.md) -->$', re.MULTILINE)
    names = marker.findall(text)
    parts = source / 'prompt'
    if not names and not parts.exists() and '<!-- include:' not in text:
        return text
    available = {p.relative_to(source).as_posix() for p in parts.rglob('*') if p.is_file()}
    if len(names) != len(set(names)) or set(names) != available:
        raise ValueError('Prompt parts must each be included exactly once')
    def expand(match):
        path = source / match[1]
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError('Unsafe prompt part path')
        content = path.read_text(encoding='utf-8').strip()
        if not content or '<!-- include:' in content or content.startswith('---'):
            raise ValueError('Prompt parts must be nonempty bodies without nested includes or frontmatter')
        return content
    composed = marker.sub(expand, text)
    if '<!-- include:' in composed:
        raise ValueError('Invalid prompt include directive')
    return composed


def render_set(entry, target):
    if target.exists() and any(target.iterdir()):
        raise ValueError(f'Build destination is not empty: {target}')
    text = compose_prompt(SKILLS / entry['family'])
    _copy_tree(CORE / 'scripts', target / 'scripts')
    _copy_tree(CORE / 'references', target / 'references')
    _copy_tree(SKILLS / entry['family'], target, exclude={'prompt'})
    _copy_tree(ROOT / 'adapters' / entry['tool'] / 'resources', target)
    shutil.copyfile(ROOT / 'LICENSE', target / 'LICENSE')
    skill = target / 'SKILL.md'
    text = text.replace('name: invoice-reader', 'name: ' + entry['name'], 1)
    manual = entry['invocation'] == 'manual'
    if entry['adapter']['invocation_format'] in ('claude', 'grok', 'cursor') and manual:
        text = text.replace('\n---\n', '\ndisable-model-invocation: true\n---\n', 1)
    _write(skill, text)
    if entry['adapter']['invocation_format'] == 'codex':
        _write(target / 'agents' / 'openai.yaml',
               'policy:\n  allow_implicit_invocation: ' + str(not manual).lower() + '\n')
    metadata = {k: entry[k] for k in ('name', 'family', 'tool', 'version', 'recommended_model',
                                    'provider', 'status', 'last_eval')}
    metadata['core_version'] = core_version()
    _write(target / 'scripts' / 'data' / 'set.toml',
           ''.join(f'{key} = {json.dumps(value)}\n' for key, value in metadata.items()))


def tree_hash(folder):
    digest = hashlib.sha256()
    for path in sorted(p for p in folder.rglob('*') if p.is_file()):
        if any(part in IGNORED for part in path.relative_to(folder).parts):
            continue
        digest.update(path.relative_to(folder).as_posix().encode())
        digest.update(b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def readme_with_table(packages):
    lines = ['| Family | Tool | Package | Recommended model | Version | Status | Last eval |',
             '|---|---|---|---|---|---|---|']
    for entry in packages:
        lines.append(f"| {entry['family']} | {entry['adapter']['label']} | `{entry['name']}` | "
                     f"{('`'+entry['recommended_model']+'`') if entry['recommended_model'] else 'Pending evaluation'} | {entry['version']} | {entry['status']} | "
                     f"{entry['last_eval'] or 'Not evaluated'} |")
    text = README.read_text(encoding='utf-8')
    start, end = text.index(TABLE_START) + len(TABLE_START), text.index(TABLE_END)
    return text[:start] + '\n' + '\n'.join(lines) + '\n' + text[end:]
