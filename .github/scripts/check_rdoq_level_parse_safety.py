#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static bool parseBoolOrNumericInt(const char* value, int falseValue, int& parsedValue)',
    'int boolValue = x265_atobool(value, bLocalError);',
    'int intValue = parseOptionIntValue(value, bLocalError);',
    'parsedValue = intValue;',
    'bool bRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
    'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
    '|| bRdoqTextualTrue',
    '|| p->rdoqLevel < 0 || p->rdoqLevel > 2;',
    'CHECK(param->rdoqLevel < 0 || param->rdoqLevel > 2,',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    function_start = text.find('static bool parseBoolOrNumericInt(const char* value, int falseValue, int& parsedValue)')
    if function_start == -1:
        return [(TARGET.as_posix(), 0, 'missing rdoq parse guardrail: helper definition')]
    next_function = text.find('static bool parseBoolOrNumericDouble', function_start)
    function_text = text[function_start:next_function if next_function != -1 else None]
    if 'parsedValue = x265_atoi(value, bLocalError);' in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden rdoq parse regression: helper must not write parsedValue before numeric parse succeeds'))
    if text.count('bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)') != 2:
        failures.append((TARGET.as_posix(), 0, 'missing rdoq parse guardrail: both rdoq-level call sites'))
    if '|| p->rdoqLevel < 0 || p->rdoqLevel > 2;' in text and '|| bRdoqTextualTrue' not in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden rdoq parse regression: missing textual true rejection'))

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing rdoq parse guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check rdoq-level parse safety guardrails')
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

    print('RDOQ level parse safety validated')


if __name__ == '__main__':
    main()
