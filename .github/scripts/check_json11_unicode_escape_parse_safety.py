#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/dynamicHDR10/json11/json11.cpp')
REQUIRED_SNIPPETS = (
    'static inline int decode_hex_digit(char ch) {',
    "if (in_range(ch, '0', '9'))",
    "if (in_range(ch, 'a', 'f'))",
    'long codepoint = 0;',
    'codepoint = (codepoint << 4) | decode_hex_digit(esc[j]);',
    'i += 4;',
    '&& in_range(codepoint, 0xDC00, 0xDFFF)',
)
FORBIDDEN_SNIPPETS = (
    'long codepoint = strtol(esc.data(), nullptr, 16);',
    'long codepoint = std::strtol(esc.data(), nullptr, 16);',
)


def extract_parse_string_region(text):
    marker = 'string parse_string() {'
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
    region = extract_parse_string_region(text)
    if not region:
        return [(TARGET.as_posix(), 0, 'missing parse_string() function')]

    failures = []
    helper_snippets = REQUIRED_SNIPPETS[:3]
    region_snippets = REQUIRED_SNIPPETS[3:]
    for snippet in helper_snippets:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing json11 unicode escape guardrail: {snippet}'))
    if 'bad \\\\u escape: ' not in region:
        failures.append((TARGET.as_posix(), 0, 'missing json11 unicode escape guardrail: bad \\\\u escape: '))
    for snippet in region_snippets:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing json11 unicode escape guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden json11 unicode escape regression: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check json11 unicode escape parse safety guardrails')
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

    print('json11 unicode escape parse safety validated')


if __name__ == '__main__':
    main()
