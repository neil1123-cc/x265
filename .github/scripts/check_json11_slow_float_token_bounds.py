#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/dynamicHDR10/json11/json11.cpp')
GLOBAL_REQUIRED_SNIPPETS = (
    'static inline double parse_token_bounded_json_double(const char* begin, const char* end) {',
    'string token(begin, end);',
    'char* parse_end = nullptr;',
    'double value = std::strtod(token.c_str(), &parse_end);',
    'return parse_end == token.c_str() + token.size() ? value : 0.0;',
)
REGION_REQUIRED_SNIPPETS = (
    'return parse_token_bounded_json_double(str.c_str() + start_pos, str.c_str() + i);',
)
FORBIDDEN_SNIPPETS = (
    'return std::strtod(str.c_str() + start_pos, nullptr);',
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
    for snippet in GLOBAL_REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing json11 slow-float guardrail: {snippet}'))
    for snippet in REGION_REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing json11 slow-float guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden json11 slow-float regression: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check json11 slow float token-bound guardrails')
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

    print('json11 slow float token bounds validated')


if __name__ == '__main__':
    main()
