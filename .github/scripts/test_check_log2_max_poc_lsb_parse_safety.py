#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_log2_max_poc_lsb_parse_safety.py')


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
                    'OPT("log2-max-poc-lsb")',
                    '{',
                    '    bool bLog2MaxPocLsbError = false;',
                    '    int log2MaxPocLsb = parseOptionIntValue(value, bLog2MaxPocLsbError);',
                    '    bError |= bLog2MaxPocLsbError;',
                    '    if (!bLog2MaxPocLsbError)',
                    '        p->log2MaxPocLsb = log2MaxPocLsb;',
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
                    'OPT("log2-max-poc-lsb")',
                    '{',
                    '    int log2MaxPocLsb = parseOptionIntValue(value, bLog2MaxPocLsbError);',
                    '    bError |= bLog2MaxPocLsbError;',
                    '    if (!bLog2MaxPocLsbError)',
                    '        p->log2MaxPocLsb = log2MaxPocLsb;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing log2-max-poc-lsb guardrail: bool bLog2MaxPocLsbError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'OPT("log2-max-poc-lsb") p->log2MaxPocLsb = x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden log2-max-poc-lsb regression: invalid values must not overwrite prior state')

    print('Log2-max-poc-lsb parse safety tests passed')


if __name__ == '__main__':
    main()
