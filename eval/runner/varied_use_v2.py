"""Prospective v2 references with the unchanged varied-use execution/scoring engine.

Load the engine in its own module namespace: only the reference/protocol version
differs. The historical v1 module, its hashes, and other importers stay untouched.
Both this entry and the engine are archived and hashed by every new plan.
"""
import argparse
import importlib.util
import json
from pathlib import Path

VERSION = 'varied-use-v2'
_spec = importlib.util.spec_from_file_location('_varied_use_v2_engine', Path(__file__).with_name('varied_use.py'))
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)
engine.VERSION = VERSION


def plan(batch, workspace_root, model, provider, transport):
    return engine.plan(batch, workspace_root, model, provider, transport)


def load(batch, number):
    data, trial, folder = engine.load(batch, number)
    if data['protocol'] != VERSION: raise ValueError('Use the matching versioned runner for this plan.')
    return data, trial, folder


def execute(batch, number, action):
    load(batch, number)
    return engine.execute(batch, number, action)


def report(batch, destination):
    data = engine.read(batch/'plan.json')
    for trial in data['trials']: load(batch, trial['id'])
    return engine.report(batch, destination)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='action', required=True)
    s = sub.add_parser('plan'); s.add_argument('batch', type=Path); s.add_argument('--workspace-root', type=Path, required=True)
    s.add_argument('--model', required=True); s.add_argument('--provider', required=True)
    s.add_argument('--transport', choices=('default', 'https'), default='https')
    for action in ('start', 'reply'):
        s = sub.add_parser(action); s.add_argument('batch', type=Path); s.add_argument('--trial', type=int, required=True)
    s = sub.add_parser('report'); s.add_argument('batch', type=Path); s.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.action == 'plan': result = plan(a.batch, a.workspace_root, a.model, a.provider, a.transport)
    elif a.action == 'report': result = report(a.batch, a.out)
    else: result = execute(a.batch, a.trial, a.action)
    print(json.dumps(result, indent=2))
