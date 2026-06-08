#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("total-frames")',
    'OPT("frames")',
    'bool bFramesToBeEncodedError = false;',
    'int framesToBeEncoded = parseOptionIntValue(value, bFramesToBeEncodedError);',
    'bError |= bFramesToBeEncodedError;',
    'if (!bFramesToBeEncodedError)',
    'svtHevcParam->framesToBeEncoded = framesToBeEncoded;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if 'OPT("total-frames") svtHevcParam->framesToBeEncoded = x265_atoi(value, bError);' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden SVT total-frames regression: invalid values must not overwrite prior state'))
    if 'OPT("frames") svtHevcParam->framesToBeEncoded = x265_atoi(value, bError);' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden SVT frames regression: invalid values must not overwrite prior state'))
    if failures:
        return failures
    if text.count('bool bFramesToBeEncodedError = false;') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing SVT frames-to-be-encoded guardrail in both aliases'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing SVT frames-to-be-encoded guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT frames-to-be-encoded parse safety guardrails')
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

    print('SVT frames-to-be-encoded parse safety validated')


if __name__ == '__main__':
    main()
