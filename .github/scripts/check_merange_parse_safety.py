#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
EXPECTED_COUNT = 2
REQUIRED_SNIPPETS = (
    'OPT("merange")',
    'bool bSearchRangeError = false;',
    'int searchRange = parseOptionIntValue(value, bSearchRangeError);',
    'bError |= bSearchRangeError;',
    'if (!bSearchRangeError)',
    'p->searchRange = searchRange;',
)
FORBIDDEN_SNIPPET = 'OPT("merange") p->searchRange = x265_atoi(value, bError);'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if FORBIDDEN_SNIPPET in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden merange regression: invalid values must not overwrite prior state'))
        return failures
    for snippet in REQUIRED_SNIPPETS:
        count = text.count(snippet)
        if count < EXPECTED_COUNT:
            failures.append((TARGET.as_posix(), 0, f'missing merange guardrail ({count}/{EXPECTED_COUNT}): {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check merange parse safety guardrails')
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

    print('Merange parse safety validated')


if __name__ == '__main__':
    main()
