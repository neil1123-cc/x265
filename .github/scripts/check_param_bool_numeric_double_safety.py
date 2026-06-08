#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static bool parseBoolOrNumericDouble(const char* value, double falseValue, double& parsedValue)',
    'bLocalError = false;\n    double doubleValue = x265_atof(value, bLocalError);',
    'double doubleValue = x265_atof(value, bLocalError);',
    'if (!bLocalError && std::isfinite(doubleValue))',
    'parsedValue = doubleValue;',
    'return false;',
    'OPT("psy-rd")',
    'bool bPsyRdTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
    'bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRd)',
    '|| bPsyRdTextualTrue;',
    'OPT("psy-rdoq")',
    'bool bPsyRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
    'bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRdoq)',
    '|| bPsyRdoqTextualTrue;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    function_start = text.find('static bool parseBoolOrNumericDouble(const char* value, double falseValue, double& parsedValue)')
    if function_start == -1:
        failures.append((TARGET.as_posix(), 0, 'missing param bool-or-numeric-double guardrail: function definition'))
        return failures

    next_function = text.find('static bool parseMaskingStrengthTriples', function_start)
    function_text = text[function_start:next_function if next_function != -1 else None]
    if 'parsedValue = x265_atof(value, bLocalError);\n    return !bLocalError;' in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden param bool-or-numeric-double regression: return !bLocalError;'))
    if 'parsedValue = x265_atof(value, bLocalError);' in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden param bool-or-numeric-double regression: helper must not write parsedValue before double parse succeeds'))
    if 'bLocalError = false;\n    double doubleValue = x265_atof(value, bLocalError);' not in function_text:
        failures.append((TARGET.as_posix(), 0, 'forbidden param bool-or-numeric-double regression: helper must reset bLocalError before double parse'))
    if 'bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRd);' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden param bool-or-numeric-double regression: missing psy-rd true-text rejection'))
    if 'bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRdoq);' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden param bool-or-numeric-double regression: missing psy-rdoq true-text rejection'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing param bool-or-numeric-double guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check param bool-or-numeric-double helper safety guardrails')
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

    print('Param bool-or-numeric-double safety validated')


if __name__ == '__main__':
    main()
