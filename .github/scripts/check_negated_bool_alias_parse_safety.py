#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static const char* invertBooleanAliasValue(const char* value, bool& bError)',
    'value = invertBooleanAliasValue(value, bError);',
    'bValueWasNull = false;',
    'if (bError)\n        return X265_PARAM_BAD_VALUE;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if 'value = !value || x265_atobool(value, bError) ? "false" : "true";' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden negated bool alias regression: invalid alias values must not be inverted inline'))
    if text.count('value = invertBooleanAliasValue(value, bError);') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing negated bool alias guardrail in both param parsers'))
    if text.count('bValueWasNull = false;') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing negated bool alias null-value reset guardrail in main param parser'))
    if text.count('if (bError)\n        return X265_PARAM_BAD_VALUE;') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing negated bool alias early-return guardrail in both param parsers'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing negated bool alias guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check negated bool alias parse safety guardrails')
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

    print('Negated bool alias parse safety validated')


if __name__ == '__main__':
    main()
