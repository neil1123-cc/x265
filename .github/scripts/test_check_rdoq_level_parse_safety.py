#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_rdoq_level_parse_safety.py')


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
    'static bool parseBoolOrNumericInt(const char* value, int falseValue, int& parsedValue)',
    'int boolValue = x265_atobool(value, bLocalError);',
    'int intValue = parseOptionIntValue(value, bLocalError);',
    'parsedValue = intValue;',
    'bool bRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
    'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
    '       || bRdoqTextualTrue',
    '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
    'bool bRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));',
    'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
    '       || bRdoqTextualTrue',
    '       || p->rdoqLevel < 0 || p->rdoqLevel > 2;',
    'CHECK(param->rdoqLevel < 0 || param->rdoqLevel > 2,',
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
                    'parsedValue = intValue;',
                    'parsedValue = x265_atoi(value, bLocalError);',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden rdoq parse regression: helper must not write parsedValue before numeric parse succeeds')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)',
                    'bError |= some_other_check(value, p->rdoqLevel)',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing rdoq parse guardrail: both rdoq-level call sites')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '       || bRdoqTextualTrue\n',
                    '',
                    2,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden rdoq parse regression: missing textual true rejection')

    print('RDOQ level parse safety tests passed')


if __name__ == '__main__':
    main()
