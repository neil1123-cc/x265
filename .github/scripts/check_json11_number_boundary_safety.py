#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/dynamicHDR10/json11/json11.cpp')
REQUIRED_SNIPPETS = (
    'auto current = [this]() -> char {',
    "return i < str.size() ? str[i] : '\\0';",
    'char ch = current();',
    "if (ch == '-') {",
    "if (ch == '0') {",
    "if (ch != '.' && ch != 'e' && ch != 'E'",
    "if (ch == '.') {",
    "if (ch == 'e' || ch == 'E') {",
    "if (ch == '+' || ch == '-') {",
)
FORBIDDEN_SNIPPETS = (
    "if (str[i] == '-')",
    "if (str[i] == '0')",
    "if (in_range(str[i], '0', '9'))",
    "else if (in_range(str[i], '1', '9'))",
    'return fail("invalid " + esc(str[i]) + " in number");',
    "if (str[i] == '.')",
    "if (str[i] == 'e' || str[i] == 'E')",
    "if (str[i] == '+' || str[i] == '-')",
)


def extract_parse_number(text):
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
    function_text = extract_parse_number(text)
    if not function_text:
        return [(TARGET.as_posix(), 0, 'missing Json parse_number() function')]

    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in function_text:
            failures.append((TARGET.as_posix(), 0, f'missing json11 number boundary guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in function_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden json11 number boundary regression: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check json11 number boundary safety guardrails')
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

    print('json11 number boundary safety validated')


if __name__ == '__main__':
    main()
