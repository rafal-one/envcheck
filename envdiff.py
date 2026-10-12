#!/usr/bin/env python3
"""envdiff: compare .env files and find undocumented/unused variables.

Usage:
  envdiff.py [--example .env.example] [--env .env] [--src DIR ...] [--json]
Exit code 1 if problems are found (handy for CI / pre-commit).
"""
import argparse, json, os, re, sys

LINE = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$')
USE = [re.compile(p) for p in (
    r'os\.environ(?:\.get)?\s*[\[(]\s*[\'"]([A-Z_][A-Z0-9_]*)',
    r'os\.getenv\(\s*[\'"]([A-Z_][A-Z0-9_]*)',
    r'process\.env\.([A-Z_][A-Z0-9_]*)',
    r'process\.env\[\s*[\'"]([A-Z_][A-Z0-9_]*)',
    r'\$\{?([A-Z_][A-Z0-9_]*)\}?',
    r'ENV\[\s*[\'"]([A-Z_][A-Z0-9_]*)',
    r'os\.Getenv\(\s*"([A-Z_][A-Z0-9_]*)"',
)]
EXT = {'.py', '.js', '.ts', '.tsx', '.jsx', '.mjs', '.rb', '.go', '.sh', '.yml', '.yaml'}
SKIP = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build'}


def parse_env(path):
    """Return {name: value} (values stripped of quotes/inline comments)."""
    out = {}
    with open(path, encoding='utf-8') as f:
        for raw in f:
            if raw.lstrip().startswith('#'):
                continue
            m = LINE.match(raw.rstrip('\n'))
            if not m:
                continue
            v = m.group(2).strip()
            if v and v[0] in '"\'' and v.count(v[0]) >= 2:
                v = v[1:v.index(v[0], 1)]
            else:
                v = re.split(r'\s+#', v)[0].strip()
            out[m.group(1)] = v
    return out


def used_vars(dirs):
    found = set()
    for d in dirs:
        for root, subs, files in os.walk(d):
            subs[:] = [s for s in subs if s not in SKIP]
            for fn in files:
                if os.path.splitext(fn)[1] not in EXT:
                    continue
                try:
                    with open(os.path.join(root, fn), encoding='utf-8') as fh:
                        text = fh.read()
                except (UnicodeDecodeError, OSError):
                    continue
                for rx in USE:
                    found.update(rx.findall(text))
    return found


def check(example, env, src_dirs):
    ex = parse_env(example)
    res = {'missing_in_env': [], 'undocumented_in_env': [], 'empty_in_env': [],
           'unused_in_code': [], 'used_but_undocumented': []}
    if env and os.path.exists(env):
        e = parse_env(env)
        res['missing_in_env'] = sorted(set(ex) - set(e))
        res['undocumented_in_env'] = sorted(set(e) - set(ex))
        res['empty_in_env'] = sorted(k for k, v in e.items() if v == '' and k in ex)
    if src_dirs:
        used = used_vars(src_dirs)
        res['unused_in_code'] = sorted(set(ex) - used)
        res['used_but_undocumented'] = sorted(
            v for v in used - set(ex) if '_' in v and v not in os.environ)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--example', default='.env.example')
    ap.add_argument('--env', default='.env')
    ap.add_argument('--src', action='append', default=[])
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if not os.path.exists(a.example):
        print(f'error: {a.example} not found', file=sys.stderr)
        return 2
    res = check(a.example, a.env, a.src)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        for k, v in res.items():
            if v:
                print(f'{k.replace("_", " ")}: {", ".join(v)}')
    bad = any(res[k] for k in ('missing_in_env', 'undocumented_in_env', 'empty_in_env', 'unused_in_code'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
