#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
    'uint32_t parsedNumerator = 0;',
    'uint32_t parsedDenominator = 0;',
    "if (parseOptionUintPair(value, '/', parsedNumerator, parsedDenominator) && parsedNumerator > 0 && parsedDenominator > 0)",
    'numerator = parsedNumerator;',
    'denominator = parsedDenominator;',
    'if (!value || !parseOptionDoubleToken(value, std::strlen(value), fps) || fps <= 0 || fps > INT_MAX)',
    'if (bLocalError || integerFps <= 0)',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    function_start = text.find('static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)')
    if function_start == -1:
        failures.append((TARGET.as_posix(), 0, 'missing fps parse guardrail: function definition'))
        return failures

    next_function = text.find('static bool parseIndexedNameOrNumber', function_start)
    function_text = text[function_start:next_function if next_function != -1 else None]
    if "if (parseOptionUintPair(value, '/', numerator, denominator))" in function_text:
        failures.append((TARGET.as_posix(), 0, "forbidden fps parse regression: missing positive numerator/denominator guard"))
    if "if (parseOptionUintPair(value, '/', numerator, denominator) && numerator > 0 && denominator > 0)" in function_text:
        failures.append((TARGET.as_posix(), 0, "forbidden fps parse regression: direct fps pair writes"))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing fps parse guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check fps parsing safety guardrails')
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

    print('FPS parse safety validated')


if __name__ == '__main__':
    main()
