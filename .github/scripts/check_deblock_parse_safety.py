#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("deblock")',
    'int tcOffset = 0;',
    'int betaOffset = 0;',
    'bool bLocalError = !parseOptionIntPair(value, *separator, tcOffset, betaOffset);',
    'if (!bLocalError)',
    'p->deblockingFilterTCOffset = tcOffset;',
    'p->deblockingFilterBetaOffset = betaOffset;',
    'int offset = parseOptionIntToken(value, std::strlen(value), bLocalError);',
    'p->bEnableLoopFilter = atobool(value);',
)
FORBIDDEN_SNIPPETS = (
    'p->deblockingFilterTCOffset = parseOptionIntToken(value, leftLength, bLocalError);',
    'p->deblockingFilterBetaOffset = parseOptionIntToken(separator + 1, rightLength, bLocalError);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    if 'OPT("deblock")' not in text:
        return [(TARGET.as_posix(), 0, 'missing deblock option block')]

    block_start = text.index('OPT("deblock")')
    block_end = text.find('OPT("sao")', block_start)
    deblock_block = text[block_start:block_end if block_end != -1 else block_start + 1400]
    failures = []
    for forbidden in FORBIDDEN_SNIPPETS:
        if forbidden in deblock_block:
            failures.append((TARGET.as_posix(), 0, 'forbidden deblock regression: invalid values must not partially overwrite deblock state'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in deblock_block:
            failures.append((TARGET.as_posix(), 0, f'missing deblock guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check deblock parse safety guardrails')
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

    print('Deblock parse safety validated')


if __name__ == '__main__':
    main()
