#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'char *buf = strdup(value);',
    'if (!buf)',
    'bError = 1;',
    'return 0;',
    'for (char* scan = buf; scan && *scan; )',
)
FORBIDDEN_SNIPPETS = (
    'char *buf = strdup(value);\n        char *tok;\n        bError = 0;\n        cpu = 0;\n        for (char* scan = buf; scan && *scan; )',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden parseCpuName strdup regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing parseCpuName strdup guardrail: {snippet}'))

    strdup_pos = text.find('char *buf = strdup(value);')
    nullcheck_pos = text.find('if (!buf)')
    scan_pos = text.find('for (char* scan = buf; scan && *scan; )')
    if -1 not in (strdup_pos, nullcheck_pos, scan_pos) and not (strdup_pos < nullcheck_pos < scan_pos):
        failures.append((TARGET.as_posix(), 0, 'parseCpuName must check strdup failure before scanning tokens'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check parseCpuName strdup safety guardrails')
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

    print('parseCpuName strdup safety validated')


if __name__ == '__main__':
    main()
