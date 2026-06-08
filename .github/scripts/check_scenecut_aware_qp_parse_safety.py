#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("scenecut-aware-qp")',
    'bool bSceneCutAwareQpError = false;',
    'int sceneCutAwareQp = parseOptionIntValue(value, bSceneCutAwareQpError);',
    'bError |= bSceneCutAwareQpError;',
    'if (!bSceneCutAwareQpError)',
    'p->bEnableSceneCutAwareQp = sceneCutAwareQp;',
)
FORBIDDEN_SNIPPET = 'OPT("scenecut-aware-qp") p->bEnableSceneCutAwareQp = x265_atoi(value, bError);'
EXPECTED_COUNT = 2


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if FORBIDDEN_SNIPPET in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden scenecut-aware-qp regression: invalid values must not overwrite prior state'))
        return failures
    for snippet in REQUIRED_SNIPPETS:
        count = text.count(snippet)
        if count < EXPECTED_COUNT:
            failures.append((TARGET.as_posix(), 0, f'missing scenecut-aware-qp guardrail occurrences for {snippet!r}: expected at least {EXPECTED_COUNT}, found {count}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scenecut-aware-qp parse safety guardrails')
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

    print('Scenecut-aware-qp parse safety validated')


if __name__ == '__main__':
    main()
