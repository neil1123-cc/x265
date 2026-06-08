#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static void assignParsedOptionLevels(const int parsed[3], int count, int target[3])',
    'OPT("hme-search")',
    'bool bLocalError = false;',
    'parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);',
    'parsed[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bLocalError);',
    'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
    'bError |= bLocalError;',
    'if (!bLocalError)',
    'p->bEnableHME = true;',
    'OPT("hme-range")',
    'int parsed[3];',
    'for (int level = 0; level < 3; level++)',
    'parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);',
    'assignParsedOptionLevels(parsed, 3, p->hmeRange);',
)
FORBIDDEN_SNIPPETS = (
    'p->hmeSearchMethod[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bError);',
    'p->hmeRange[level] = x265_atoi(number, bLocalError);',
    'parsed[level] = x265_atoi(number, bLocalError);',
    'else\n                bError = true;\n            p->bEnableHME = true;',
    'if (splitCommaOption(value, range, rangeLengths, 3) != 3)\n                bError = true;',
)
REGION_START = 'OPT("hme-search")'
REGION_END = 'OPT("vbv-live-multi-pass")'


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
            failures.append((TARGET.as_posix(), 0, 'forbidden HME parse regression: invalid values must not partially mutate arrays or force-enable HME'))
            return failures
    required_scope = text
    for snippet in REQUIRED_SNIPPETS:
        haystack = required_scope if snippet.startswith('static void assignParsedOptionLevels') else region
        if snippet not in haystack:
            failures.append((TARGET.as_posix(), 0, f'missing HME parse guardrail: {snippet}'))
    if all((snippet in required_scope if snippet.startswith('static void assignParsedOptionLevels') else snippet in region) for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'OPT("hme-search")',
                'bool bLocalError = false;',
                'if (count == 1 || count == 3)',
                'if (bNumeric)',
                'int parsed[3];',
                'parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);',
                'if (!bLocalError)',
                'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                'parsed[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bLocalError);',
                'if (!bLocalError)',
                'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                'bError |= bLocalError;',
                'if (!bLocalError)',
                'p->bEnableHME = true;',
                'OPT("hme-range")',
                'bool bLocalError = false;',
                'if (splitCommaOption(value, range, rangeLengths, 3) != 3)',
                'bLocalError = true;',
                'int parsed[3];',
                'for (int level = 0; level < 3; level++)',
                'parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);',
                'if (!bLocalError)',
                'assignParsedOptionLevels(parsed, 3, p->hmeRange);',
                'bError |= bLocalError;',
                'if (!bLocalError)',
                'p->bEnableHME = true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HME search/range parsing must finish staged token parsing and gated array assignment before enabling HME for the current parameter set'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check HME parse safety guardrails')
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

    print('HME parse safety validated')


if __name__ == '__main__':
    main()
