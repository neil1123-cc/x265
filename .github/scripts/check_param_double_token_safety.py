#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static bool parseOptionDoubleToken(const char* token, size_t length, double& value)',
    'if (length >= 32)',
    'std::from_chars_result parsed = std::from_chars(token, token + length, doubleValue);',
    'if (parsed.ec == std::errc() && parsed.ptr == token + length && std::isfinite(doubleValue))',
    'value = doubleValue;',
    'return false;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    function_start = text.find('static bool parseOptionDoubleToken(const char* token, size_t length, double& value)')
    if function_start == -1:
        failures.append((TARGET.as_posix(), 0, 'missing param double token guardrail: function definition'))
        return failures

    next_function = text.find('static bool parseTenthsOrIntegerLevel', function_start)
    function_text = text[function_start:next_function if next_function != -1 else None]
    if 'value = x265_atof(number, bLocalError);\n    return !bLocalError;' in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden param double token regression: return !bLocalError;'))
    for snippet in (
        'char number[32];',
        'std::memcpy(number, token, length);',
        'double doubleValue = x265_atof(number, bLocalError);',
    ):
        if snippet in function_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden param double token regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing param double token guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check param double token helper safety guardrails')
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

    print('Param double token safety validated')


if __name__ == '__main__':
    main()
