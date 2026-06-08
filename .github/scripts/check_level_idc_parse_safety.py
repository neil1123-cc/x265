#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static bool parseTenthsOrIntegerLevel(const char* value, int& parsedLevel)',
    'double scaledLevel = 10 * decimalLevel;',
    'int roundedLevel = (int)(scaledLevel + .5);',
    'if (std::fabs(scaledLevel - roundedLevel) > 1e-6)',
    'parsedLevel = roundedLevel;',
    'if (!parseTenthsOrIntegerLevel(value, p->levelIdc))',
    'if (!parseTenthsOrIntegerLevel(value, p->dolbyProfile))',
    'if (!parseTenthsOrIntegerLevel(value, svtHevcParam->level))',
    'if (!parseTenthsOrIntegerLevel(value, svtHevcParam->dolbyVisionProfile))',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    function_start = text.find(REQUIRED_SNIPPETS[0])
    if function_start == -1:
        failures.append((TARGET.as_posix(), 0, 'missing level-idc parse guardrail: function definition'))
        return failures

    next_function = text.find('static bool parseFpsValue', function_start)
    function_text = text[function_start:next_function if next_function != -1 else None]
    if 'parsedLevel = (int)(10 * decimalLevel + .5);' in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden level-idc parse regression: unbounded fractional rounding'))

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing level-idc parse guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check level-idc parsing safety guardrails')
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

    print('Level-idc parse safety validated')


if __name__ == '__main__':
    main()
