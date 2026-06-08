#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)',
    'int maxIndexedValue = indexOffset;',
    'for (const char* const* name = names; name && *name; name++, maxIndexedValue++) {}',
    'int indexedValue = parseOptionIntValue(value, bLocalError);',
    'if (!bLocalError && indexedValue >= indexOffset && indexedValue <= maxIndexedValue)',
    'parsedValue = indexedValue;',
    'bError |= !parseIndexedNameOrNumber(value, logLevelNames, -1, p->logLevel);',
    'bError |= !parseIndexedNameOrNumber(value, logLevelNames, -1, p->logfLevel);',
)
FORBIDDEN_SNIPPETS = (
    'if (!bLocalError)\n        return true;',
    'parsedValue = x265_atoi(value, bLocalError);',
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
        failures.append((TARGET.as_posix(), 0, 'missing log level parse guardrail: function definition'))
        return failures

    next_function = text.find('static bool parseBoolOrIntValue', function_start)
    function_text = text[function_start:next_function if next_function != -1 else None]
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in function_text:
            failures.append((TARGET.as_posix(), 0, 'forbidden log level parse regression: unbounded numeric acceptance'))

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing log level parse guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check log level parsing safety guardrails')
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

    print('Log level parse safety validated')


if __name__ == '__main__':
    main()
