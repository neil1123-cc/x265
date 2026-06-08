#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_qpmin_parse_safety.py')


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
                    'OPT("qpmin")',
                    '{',
                    '    bool bMinQpAllowedError = false;',
                    '    int minQpAllowed = parseOptionIntValue(value, bMinQpAllowedError);',
                    '    bError |= bMinQpAllowedError;',
                    '    if (!bMinQpAllowedError)',
                    '        svtHevcParam->minQpAllowed = minQpAllowed;',
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
                'source/common/param.cpp': 'OPT("qpmin") svtHevcParam->minQpAllowed = x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT qpmin regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("qpmin")',
                    '{',
                    '    svtHevcParam->minQpAllowed = minQpAllowed;',
                    '}',
                    'OPT("qpmax")',
                    '{',
                    '    something_else();',
                    '}',
                    'OPT("qpmin")',
                    '{',
                    '    bool bMinQpAllowedError = false;',
                    '    int minQpAllowed = parseOptionIntValue(value, bMinQpAllowedError);',
                    '    bError |= bMinQpAllowedError;',
                    '    if (!bMinQpAllowedError)',
                    '        svtHevcParam->minQpAllowed = minQpAllowed;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT qpmin parse block must gate assignment on parseOptionIntValue success')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    '    OPT("qpmin")',
                    '    {',
                    '        bool bMinQpAllowedError = false;',
                    '        int minQpAllowed = parseOptionIntValue(value, bMinQpAllowedError);',
                    '        bError |= bMinQpAllowedError;',
                    '        if (!bMinQpAllowedError)',
                    '            svtHevcParam->minQpAllowed = minQpAllowed;',
                    '    }',
                    '}',
                    'int svt_param_parse(x265_param* param, const char* name, const char* value)',
                    '{',
                    '    OPT("qpmin")',
                    '    {',
                    '        int minQpAllowed = parseOptionIntValue(value, bMinQpAllowedError);',
                    '        bError |= bMinQpAllowedError;',
                    '        if (!bMinQpAllowedError)',
                    '            svtHevcParam->minQpAllowed = minQpAllowed;',
                    '    }',
                    '    return bError ? X265_PARAM_BAD_VALUE : 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing SVT qpmin guardrail in parse block: bool bMinQpAllowedError = false;')

    print('SVT qpmin parse safety tests passed')


if __name__ == '__main__':
    main()
