#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_pass_parse_safety.py')


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
                    'OPT("pass")',
                    '{',
                    '    bool bPassError = false;',
                    '    int parsedPass = parseOptionIntValue(value, bPassError);',
                    '    bError |= bPassError;',
                    '    if (!bPassError)',
                    '    {',
                    '        int pass = x265_clip3(0, 3, parsedPass);',
                    '        p->rc.bStatWrite = pass & 1;',
                    '        p->rc.bStatRead = pass & 2;',
                    '        p->rc.dataShareMode = X265_SHARE_MODE_FILE;',
                    '    }',
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
                    'OPT("pass")',
                    '{',
                    '    int parsedPass = parseOptionIntValue(value, bPassError);',
                    '    bError |= bPassError;',
                    '    if (!bPassError)',
                    '    {',
                    '        int pass = x265_clip3(0, 3, parsedPass);',
                    '        p->rc.bStatWrite = pass & 1;',
                    '        p->rc.bStatRead = pass & 2;',
                    '        p->rc.dataShareMode = X265_SHARE_MODE_FILE;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing pass guardrail: bool bPassError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("pass")',
                    '{',
                    '    int pass = x265_clip3(0, 3, x265_atoi(value, bError));',
                    '    p->rc.bStatWrite = pass & 1;',
                    '    p->rc.bStatRead = pass & 2;',
                    '    p->rc.dataShareMode = X265_SHARE_MODE_FILE;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden pass regression: invalid values must not overwrite multipass state')

    print('Pass parse safety tests passed')


if __name__ == '__main__':
    main()
