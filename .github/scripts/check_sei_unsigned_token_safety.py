#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/sei.h')
FORBIDDEN_SNIPPETS = (
    'if (end == cursor || parsed > UINT_MAX)',
)
REQUIRED_SNIPPETS = (
    '#include <cerrno>',
    'static bool parseSeiUnsignedToken(const char*& cursor, uint32_t& value)',
    'if (!cursor || !*cursor)',
    "if (*cursor == '-')",
    'errno = 0;',
    'char* end = nullptr;',
    'unsigned long parsed = std::strtoul(cursor, &end, 10);',
    'if (errno == ERANGE || end == cursor || parsed > UINT_MAX)',
    'cursor = end;',
    'value = (uint32_t)parsed;',
    'return true;',
)
REGION_START = 'static bool parseSeiUnsignedToken(const char*& cursor, uint32_t& value)'
REGION_END = 'static bool consumeSeiLiteral(const char*& cursor, const char* literal)'


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
            failures.append((TARGET.as_posix(), 0, f'forbidden SEI unsigned token regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        haystack = text if snippet == '#include <cerrno>' else region
        if snippet not in haystack:
            failures.append((TARGET.as_posix(), 0, f'missing SEI unsigned token guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS if snippet != '#include <cerrno>'):
        if not has_in_order(
            region,
            (
                'if (!cursor || !*cursor)',
                "if (*cursor == '-')",
                'errno = 0;',
                'char* end = nullptr;',
                'unsigned long parsed = std::strtoul(cursor, &end, 10);',
                'if (errno == ERANGE || end == cursor || parsed > UINT_MAX)',
                'cursor = end;',
                'value = (uint32_t)parsed;',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseSeiUnsignedToken must reject negative, empty, and overflowed tokens before advancing cursor or publishing the parsed value'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SEI unsigned token parsing safety guardrails')
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

    print('SEI unsigned token safety validated')


if __name__ == '__main__':
    main()
