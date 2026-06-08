#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static bool parseBoolOrIntValue(const char* value, int& parsedValue)',
    'int boolValue = x265_atobool(value, bLocalError);',
    'parsedValue = boolValue;',
    'int intValue = parseOptionIntValue(value, bLocalError);',
    'parsedValue = intValue;',
    'OPT("scenecut")',
    'bool bScenecutTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
    'bError |= !parseBoolOrIntValue(value, p->scenecutThreshold)',
    '|| bScenecutTextualTrue',
    '|| p->scenecutThreshold < 0;',
    'OPT("b-adapt")',
    'bool bBAdaptTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
    'bError |= !parseBoolOrIntValue(value, p->bFrameAdaptive)',
    '|| bBAdaptTextualTrue',
    '|| p->bFrameAdaptive < 0 || p->bFrameAdaptive > 2;',
    'CHECK(param->bFrameAdaptive < 0 || param->bFrameAdaptive > 2,',
    'CHECK(param->scenecutThreshold < 0,',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    function_start = text.find('static bool parseBoolOrIntValue(const char* value, int& parsedValue)')
    if function_start == -1:
        return [(TARGET.as_posix(), 0, 'missing bool-or-int guardrail: function definition')]
    next_function = text.find('static bool parseBoolOrNamedValue', function_start)
    function_text = text[function_start:next_function if next_function != -1 else None]
    if 'parsedValue = x265_atobool(value, bLocalError);' in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden bool-or-int regression: helper must not write parsedValue before bool parse succeeds'))
    if 'parsedValue = x265_atoi(value, bLocalError);' in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden bool-or-int regression: helper must not write parsedValue before numeric parse succeeds'))
    if '|| p->scenecutThreshold < 0;' in text and '|| bScenecutTextualTrue' not in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden bool-or-int regression: missing scenecut bool-true rejection'))
    if '|| p->bFrameAdaptive < 0 || p->bFrameAdaptive > 2;' in text and '|| bBAdaptTextualTrue' not in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden bool-or-int regression: missing b-adapt bool-true rejection'))

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing bool-or-int guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check bool-or-int parse safety guardrails')
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

    print('Bool-or-int parse safety validated')


if __name__ == '__main__':
    main()
