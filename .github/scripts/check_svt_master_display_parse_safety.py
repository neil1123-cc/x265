#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("master-display")',
    'bool bMasterDisplayError = false;',
    'uint8_t useMasteringDisplayColorVolume = parseOptionUint8Value(value, bMasterDisplayError);',
    'bError |= bMasterDisplayError;',
    'if (!bMasterDisplayError)',
    'svtHevcParam->useMasteringDisplayColorVolume = useMasteringDisplayColorVolume;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if 'OPT("master-display") svtHevcParam->useMasteringDisplayColorVolume = parseOptionUint8Token(value, std::strlen(value), bError);' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden SVT master-display regression: invalid values must not overwrite prior state'))
        return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing SVT master-display guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT master-display parse safety guardrails')
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

    print('SVT master-display parse safety validated')


if __name__ == '__main__':
    main()
