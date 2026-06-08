#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("svt-hierarchical-level")',
    'bool bHierarchicalLevelsError = false;',
    'int hierarchicalLevels = parseOptionIntValue(value, bHierarchicalLevelsError);',
    'bError |= bHierarchicalLevelsError;',
    'if (!bHierarchicalLevelsError)',
    'svtHevcParam->hierarchicalLevels = hierarchicalLevels;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if 'OPT("svt-hierarchical-level") svtHevcParam->hierarchicalLevels = x265_atoi(value, bError);' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden SVT hierarchical-level regression: invalid values must not overwrite prior state'))
        return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing SVT hierarchical-level guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT hierarchical-level parse safety guardrails')
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

    print('SVT hierarchical-level parse safety validated')


if __name__ == '__main__':
    main()
