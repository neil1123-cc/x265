#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("rskip-edge-threshold")',
    'bool bEdgeVarThresholdError = false;',
    'int edgeVarThreshold = parseOptionIntValue(value, bEdgeVarThresholdError);',
    'bError |= bEdgeVarThresholdError;',
    'if (!bEdgeVarThresholdError)',
    'p->edgeVarThreshold = edgeVarThreshold / 100.0f;',
)
FORBIDDEN_SNIPPET = 'OPT("rskip-edge-threshold") p->edgeVarThreshold = x265_atoi(value, bError) / 100.0f;'
EXPECTED_COUNT = 2


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if FORBIDDEN_SNIPPET in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden rskip-edge-threshold regression: invalid values must not overwrite prior state'))
        return failures
    for snippet in REQUIRED_SNIPPETS:
        count = text.count(snippet)
        if count < EXPECTED_COUNT:
            failures.append((TARGET.as_posix(), 0, f'missing rskip-edge-threshold guardrail occurrences for {snippet!r}: expected at least {EXPECTED_COUNT}, found {count}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check rskip-edge-threshold parse safety guardrails')
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

    print('Rskip-edge-threshold parse safety validated')


if __name__ == '__main__':
    main()
