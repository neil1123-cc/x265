#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_param_bool_numeric_int_safety.py')

# Normalized checker probes used by the coverage scan for bool-or-numeric-int guardrails.
NORMALIZED_PROBES = (
    'forbidden bool-or-numeric-int regression: unexpected true-value remap',
    'forbidden bool-or-numeric-int regression: helper must not write parsedValue before numeric parse succeeds',
    'missing bool-or-numeric-int guardrail: both rdoq call sites',
    'missing bool-or-numeric-int guardrail: ',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseBoolOrNumericInt(const char* value, int falseValue, int& parsedValue)',
                    'int boolValue = x265_atobool(value, bLocalError);',
                    'if (!bLocalError && !boolValue)',
                    'parsedValue = falseValue;',
                    'int intValue = parseOptionIntValue(value, bLocalError);',
                    'parsedValue = intValue;',
                    'return !bLocalError;',
                    'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
                    '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
                    'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
                    '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
                    'CHECK(param->rdoqLevel < 0 || param->rdoqLevel > 2,',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseBoolOrNumericInt(const char* value, int falseValue, int& parsedValue)',
                    'int boolValue = x265_atobool(value, bLocalError);',
                    'if (!bLocalError && boolValue)',
                    'parsedValue = 1;',
                    'parsedValue = x265_atoi(value, bLocalError);',
                    'return !bLocalError;',
                    'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
                    '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
                    'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
                    '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
                    'CHECK(param->rdoqLevel < 0 || param->rdoqLevel > 2,',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden bool-or-numeric-int regression')

    print('Bool-or-numeric-int helper safety tests passed')


if __name__ == '__main__':
    main()
