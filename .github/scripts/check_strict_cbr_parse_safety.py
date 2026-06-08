#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("strict-cbr")',
    'bool bStrictCbrError = false;',
    'int bStrictCbr = x265_atobool(value, bStrictCbrError);',
    'bError |= bStrictCbrError;',
    'if (!bStrictCbrError)',
    'p->rc.bStrictCbr = bStrictCbr;',
    'p->rc.pbFactor = 1.0;',
)
FORBIDDEN_SNIPPETS = (
    'p->rc.bStrictCbr = atobool(value);',
    'OPT("strict-cbr")\n    {\n        p->rc.bStrictCbr = atobool(value);\n        p->rc.pbFactor = 1.0;\n    }',
)
REGION_START = 'OPT("strict-cbr")'
REGION_END = 'OPT("sar")'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region = get_region(text, REGION_START, REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, 'forbidden strict-cbr regression: invalid values must not mutate strict-cbr or pbFactor'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing strict-cbr guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'OPT("strict-cbr")',
                'bool bStrictCbrError = false;',
                'int bStrictCbr = x265_atobool(value, bStrictCbrError);',
                'bError |= bStrictCbrError;',
                'if (!bStrictCbrError)',
                'p->rc.bStrictCbr = bStrictCbr;',
                'p->rc.pbFactor = 1.0;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'strict-cbr parsing must keep the bool parse gate ahead of strict-cbr publication and pbFactor forcing'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check strict-cbr parse safety guardrails')
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

    print('Strict-cbr parse safety validated')


if __name__ == '__main__':
    main()
