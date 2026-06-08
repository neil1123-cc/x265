#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_negated_bool_alias_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing negated bool alias guardrail: ',
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


PASS_SOURCE = '\n'.join((
    'static const char* invertBooleanAliasValue(const char* value, bool& bError)',
    '{',
    '    if (!value)',
    '        return "false";',
    '    bool bLocalError = false;',
    '    int boolValue = x265_atobool(value, bLocalError);',
    '    if (bLocalError)',
    '    {',
    '        bError = true;',
    '        return value;',
    '    }',
    '    return boolValue ? "false" : "true";',
    '}',
    'value = invertBooleanAliasValue(value, bError);',
    'bValueWasNull = false;',
    'if (bError)',
    '        return X265_PARAM_BAD_VALUE;',
    'value = invertBooleanAliasValue(value, bError);',
    'bValueWasNull = false;',
    'if (bError)',
    '        return X265_PARAM_BAD_VALUE;',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'value = invertBooleanAliasValue(value, bError);',
                    'value = !value || x265_atobool(value, bError) ? "false" : "true";',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden negated bool alias regression: invalid alias values must not be inverted inline')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'value = invertBooleanAliasValue(value, bError);',
                    'value = some_other_alias(value, bError);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing negated bool alias guardrail in both param parsers')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'bValueWasNull = false;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing negated bool alias null-value reset guardrail in main param parser')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'if (bError)\n'
                    '        return X265_PARAM_BAD_VALUE;\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing negated bool alias early-return guardrail in both param parsers')

    print('Negated bool alias parse safety tests passed')


if __name__ == '__main__':
    main()
