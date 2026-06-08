#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("log2-max-poc-lsb")',
    'bool bLog2MaxPocLsbError = false;',
    'int log2MaxPocLsb = parseOptionIntValue(value, bLog2MaxPocLsbError);',
    'bError |= bLog2MaxPocLsbError;',
    'if (!bLog2MaxPocLsbError)',
    'p->log2MaxPocLsb = log2MaxPocLsb;',
)
FORBIDDEN_SNIPPET = 'OPT("log2-max-poc-lsb") p->log2MaxPocLsb = x265_atoi(value, bError);'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if FORBIDDEN_SNIPPET in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden log2-max-poc-lsb regression: invalid values must not overwrite prior state'))
        return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing log2-max-poc-lsb guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check log2-max-poc-lsb parse safety guardrails')
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

    print('Log2-max-poc-lsb parse safety validated')


if __name__ == '__main__':
    main()
