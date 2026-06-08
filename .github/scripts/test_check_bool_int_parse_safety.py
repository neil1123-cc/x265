#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_bool_int_parse_safety.py')


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
    'static bool parseBoolOrIntValue(const char* value, int& parsedValue)',
    'int boolValue = x265_atobool(value, bLocalError);',
    'parsedValue = boolValue;',
    'int intValue = parseOptionIntValue(value, bLocalError);',
    'parsedValue = intValue;',
    'OPT("scenecut")',
    '{',
    '   bool bScenecutTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
    '   bError |= !parseBoolOrIntValue(value, p->scenecutThreshold)',
    '          || bScenecutTextualTrue',
    '          || p->scenecutThreshold < 0;',
    '}',
    'OPT("b-adapt")',
    '{',
    '    bool bBAdaptTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
    '    bError |= !parseBoolOrIntValue(value, p->bFrameAdaptive)',
    '           || bBAdaptTextualTrue',
    '           || p->bFrameAdaptive < 0 || p->bFrameAdaptive > 2;',
    '}',
    'CHECK(param->bFrameAdaptive < 0 || param->bFrameAdaptive > 2,',
    'CHECK(param->scenecutThreshold < 0,',
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
                    'static bool parseBoolOrIntValue(const char* value, int& parsedValue)\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing bool-or-int guardrail: function definition')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'parsedValue = boolValue;',
                    'parsedValue = x265_atobool(value, bLocalError);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden bool-or-int regression: helper must not write parsedValue before bool parse succeeds')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'parsedValue = intValue;',
                    'parsedValue = x265_atoi(value, bLocalError);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden bool-or-int regression: helper must not write parsedValue before numeric parse succeeds')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '          || bScenecutTextualTrue\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden bool-or-int regression: missing scenecut bool-true rejection')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '           || bBAdaptTextualTrue\n',
                    '',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden bool-or-int regression: missing b-adapt bool-true rejection')

    print('Bool-or-int parse safety tests passed')


if __name__ == '__main__':
    main()
