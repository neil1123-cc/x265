#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("sao")',
    'int bEnableSao = x265_atobool(value, bError);',
    'if (!bError)',
    'svtHevcParam->enableSaoFlag = (uint8_t)bEnableSao;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if 'OPT("sao") svtHevcParam->enableSaoFlag = (uint8_t)x265_atobool(value, bError);' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden SVT SAO regression: parse result must be separated from state updates'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing SVT SAO guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT SAO parse safety guardrails')
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

    print('SVT SAO parse safety validated')


if __name__ == '__main__':
    main()
