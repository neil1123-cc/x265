#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/dynamicHDR10/json11/json11.cpp')
REQUIRED_SNIPPETS = (
    '#include <charconv>',
    'static inline bool parse_short_json_int(const char* begin, const char* end, int& value) {',
    'std::from_chars_result parsed = std::from_chars(begin, end, value);',
    'return parsed.ec == std::errc() && parsed.ptr == end;',
    'int intValue = 0;',
    'if (parse_short_json_int(str.c_str() + start_pos, str.c_str() + i, intValue))',
    'return intValue;',
    "if (ch != '.' && ch != 'e' && ch != 'E'",
)
FORBIDDEN_SNIPPETS = (
    'return static_cast<int>(std::strtol(str.c_str() + start_pos, nullptr, 10));',
)


def extract_parse_number_region(text):
    marker = 'Json parse_number() {'
    start = text.find(marker)
    if start < 0:
        return ''

    brace_depth = 0
    body_started = False
    for index in range(start, len(text)):
        char = text[index]
        if char == '{':
            brace_depth += 1
            body_started = True
        elif char == '}':
            brace_depth -= 1
            if body_started and brace_depth == 0:
                return text[start:index + 1]
    return ''


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region = extract_parse_number_region(text)
    if not region:
        return [(TARGET.as_posix(), 0, 'missing parse_number() function')]

    failures = []
    for snippet in REQUIRED_SNIPPETS[:4]:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing json11 short-int guardrail: {snippet}'))
    for snippet in REQUIRED_SNIPPETS[4:]:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing json11 short-int guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden json11 short-int regression: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check json11 short integer parse safety guardrails')
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

    print('json11 short integer parse safety validated')


if __name__ == '__main__':
    main()
