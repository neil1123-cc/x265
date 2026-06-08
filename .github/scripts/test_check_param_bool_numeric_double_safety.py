#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_param_bool_numeric_double_safety.py')

# Normalized checker probes used by the coverage scan for bool-or-numeric-double guardrails.
NORMALIZED_PROBES = (
    'missing param bool-or-numeric-double guardrail: function definition',
    'forbidden param bool-or-numeric-double regression: return !bLocalError;',
    'forbidden param bool-or-numeric-double regression: helper must not write parsedValue before double parse succeeds',
    'forbidden param bool-or-numeric-double regression: helper must reset bLocalError before double parse',
    'forbidden param bool-or-numeric-double regression: missing psy-rd true-text rejection',
    'forbidden param bool-or-numeric-double regression: missing psy-rdoq true-text rejection',
    'missing param bool-or-numeric-double guardrail: ',
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
                    'static bool parseBoolOrNumericDouble(const char* value, double falseValue, double& parsedValue)',
                    '{',
                    '    bool bLocalError = false;',
                    '    int boolValue = x265_atobool(value, bLocalError);',
                    '    if (!bLocalError && !boolValue)',
                    '    {',
                    '        parsedValue = falseValue;',
                    '        return true;',
                    '    }',
                    '',
                    '    bLocalError = false;',
                    '    double doubleValue = x265_atof(value, bLocalError);',
                    '    if (!bLocalError && std::isfinite(doubleValue))',
                    '    {',
                    '        parsedValue = doubleValue;',
                    '        return true;',
                    '    }',
                    '',
                    '    return false;',
                    '}',
                    'OPT("psy-rd")',
                    '{',
                    '    bool bPsyRdTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
                    '    bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRd)',
                    '           || bPsyRdTextualTrue;',
                    '}',
                    'OPT("psy-rdoq")',
                    '{',
                    '    bool bPsyRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
                    '    bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRdoq)',
                    '           || bPsyRdoqTextualTrue;',
                    '}',
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
                    'static bool parseBoolOrNumericDouble(const char* value, double falseValue, double& parsedValue)',
                    '{',
                    '    parsedValue = x265_atof(value, bLocalError);',
                    '    return !bLocalError;',
                    '}',
                    'OPT("psy-rd")',
                    '{',
                    '    bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRd);',
                    '}',
                    'static bool parseMaskingStrengthTriples(const char* value, int expectedTriples, int window[], double refQpDelta[], double nonRefQpDelta[])',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden param bool-or-numeric-double regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static bool parseBoolOrNumericDouble(const char* value, double falseValue, double& parsedValue)',
                    '{',
                    '    bool bLocalError = false;',
                    '    int boolValue = x265_atobool(value, bLocalError);',
                    '    if (!bLocalError && !boolValue)',
                    '    {',
                    '        parsedValue = falseValue;',
                    '        return true;',
                    '    }',
                    '    double doubleValue = x265_atof(value, bLocalError);',
                    '    if (!bLocalError && std::isfinite(doubleValue))',
                    '    {',
                    '        parsedValue = doubleValue;',
                    '        return true;',
                    '    }',
                    '    return false;',
                    '}',
                    'OPT("psy-rd")',
                    '{',
                    '    bool bPsyRdTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
                    '    bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRd)',
                    '           || bPsyRdTextualTrue;',
                    '}',
                    'OPT("psy-rdoq")',
                    '{',
                    '    bool bPsyRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
                    '    bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRdoq)',
                    '           || bPsyRdoqTextualTrue;',
                    '}',
                    'static bool parseMaskingStrengthTriples(const char* value, int expectedTriples, int window[], double refQpDelta[], double nonRefQpDelta[])',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'helper must reset bLocalError before double parse')

    print('Param bool-or-numeric-double safety tests passed')


if __name__ == '__main__':
    main()
