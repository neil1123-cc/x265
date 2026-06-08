#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.h')
REQUIRED_SNIPPETS = (
    'VideoDesc* m_srcFormat;',
    'VideoDesc* m_dstFormat;',
    'if (m_srcFormat)',
    'delete m_srcFormat;',
    'm_srcFormat = nullptr;',
    'if (m_dstFormat)',
    'delete m_dstFormat;',
    'm_dstFormat = nullptr;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ABR scaler VideoDesc ownership guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR scaler VideoDesc ownership guardrails')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('ABR scaler VideoDesc ownership validated')


if __name__ == '__main__':
    main()
