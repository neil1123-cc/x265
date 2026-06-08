#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static bool parseBoolOrNamedValue(const char* value, const char* const* names, int& parsedValue)',
    'int boolValue = x265_atobool(value, bLocalError);',
    'parsedValue = boolValue;',
    'int namedValue = parseName(value, names, bLocalError);',
    'parsedValue = namedValue;',
    'OPT("interlace")',
    'bool bInterlaceBoolError = false;',
    'int interlaceBoolValue = x265_atobool(value, bInterlaceBoolError);',
    'bError |= !parseBoolOrNamedValue(value, x265_interlace_names, p->interlaceMode)',
    '|| (!bInterlaceBoolError && interlaceBoolValue)',
    '|| p->interlaceMode < 0 || p->interlaceMode > 2;',
    'CHECK(param->interlaceMode < 0 || param->interlaceMode > 2,',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    function_start = text.find('static bool parseBoolOrNamedValue(const char* value, const char* const* names, int& parsedValue)')
    if function_start == -1:
        return [(TARGET.as_posix(), 0, 'missing interlace parse guardrail: helper definition')]
    next_function = text.find('static bool parseBoolOrNumericInt', function_start)
    function_text = text[function_start:next_function if next_function != -1 else None]
    if 'parsedValue = x265_atobool(value, bLocalError);' in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden interlace parse regression: helper must not write parsedValue before bool parse succeeds'))
    if 'parsedValue = parseName(value, names, bLocalError);' in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden interlace parse regression: helper must not write parsedValue before named parse succeeds'))
    if 'OPT("interlace")\n    {\n        bError |= !parseBoolOrNamedValue(value, x265_interlace_names, p->interlaceMode);\n    }' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden interlace parse regression: missing immediate range guard'))
    if '|| p->interlaceMode < 0 || p->interlaceMode > 2;' in text and '|| (!bInterlaceBoolError && interlaceBoolValue)' not in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden interlace parse regression: missing bool-true rejection'))

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing interlace parse guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check interlace parse safety guardrails')
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

    print('Interlace parse safety validated')


if __name__ == '__main__':
    main()
