#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    'if (strtol(value, nullptr, 0))',
    'else if (x265_atobool(value, bError) == 0 && !bError)',
)
REQUIRED_SNIPPETS = (
    'OPT("deblock")',
    'bool bDeblockValueError = false;',
    'int deblockValue = parseOptionIntValue(value, bDeblockValueError);',
    'if (!bDeblockValueError)',
    'svtHevcParam->disableDlfFlag = deblockValue ? 0 : 1;',
    'int deblockEnabled = x265_atobool(value, bError);',
    'svtHevcParam->disableDlfFlag = deblockEnabled ? 0 : 1;',
)
REGION_START = 'OPT("deblock")'
REGION_END = 'OPT("sao")'


def get_last_region(text, start_marker, end_marker):
    start = text.rfind(start_marker)
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
    region = get_last_region(text, REGION_START, REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden SVT deblock parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing SVT deblock parse guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'OPT("deblock")',
                'bool bDeblockValueError = false;',
                'int deblockValue = parseOptionIntValue(value, bDeblockValueError);',
                'if (!bDeblockValueError)',
                'svtHevcParam->disableDlfFlag = deblockValue ? 0 : 1;',
                'else',
                'int deblockEnabled = x265_atobool(value, bError);',
                'if (!bError)',
                'svtHevcParam->disableDlfFlag = deblockEnabled ? 0 : 1;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'SVT deblock parsing must preserve the reviewed integer-first parse path before the boolean fallback mutates disableDlfFlag'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed SVT deblock parsing guardrails in common/param.cpp')
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

    print('SVT deblock parse usage validated')


if __name__ == '__main__':
    main()
