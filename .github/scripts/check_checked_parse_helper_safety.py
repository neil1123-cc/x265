#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    'int v = strtol(str, &end, 0);',
    'if (end == str || *end != \'\\0\')',
)
REQUIRED_SNIPPETS = (
    '#include <cerrno>',
    'if (!str)',
    'errno = 0;',
    'long parsed = strtol(str, &end, 0);',
    'if (errno == ERANGE || parsed < INT_MIN || parsed > INT_MAX || end == str || *end != \'\\0\')',
    'return (int)parsed;',
    'return 0.0;',
    'if (errno == ERANGE || end == str || *end != \'\\0\')',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden checked-parse helper regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing checked-parse helper guardrail: {snippet}'))
    if text.count('errno = 0;') < 2:
        failures.append((TARGET.as_posix(), 0, 'expected errno reset in both checked parse helpers'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check checked parse helper safety guardrails in common/param.cpp')
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

    print('Checked parse helper safety validated')


if __name__ == '__main__':
    main()
