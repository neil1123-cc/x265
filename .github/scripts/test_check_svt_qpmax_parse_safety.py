#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_qpmax_parse_safety.py')


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
                    'OPT("qpmax")',
                    '{',
                    '    bool bQpMaxError = false;',
                    '    int qpMax = parseOptionIntValue(value, bQpMaxError);',
                    '    bError |= bQpMaxError;',
                    '    if (!bQpMaxError)',
                    '        p->rc.qpMax = qpMax;',
                    '}',
                    'OPT("qpmax")',
                    '{',
                    '    bool bMaxQpAllowedError = false;',
                    '    int maxQpAllowed = parseOptionIntValue(value, bMaxQpAllowedError);',
                    '    bError |= bMaxQpAllowedError;',
                    '    if (!bMaxQpAllowedError)',
                    '        svtHevcParam->maxQpAllowed = maxQpAllowed;',
                    '}',
                    'OPT("rc-lookahead")',
                    '{',
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
                'source/common/param.cpp': 'OPT("qpmax") svtHevcParam->maxQpAllowed = x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT qpmax regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("qpmax")',
                    '{',
                    '    bool bQpMaxError = false;',
                    '    int qpMax = parseOptionIntValue(value, bQpMaxError);',
                    '    bError |= bQpMaxError;',
                    '    if (!bQpMaxError)',
                    '        p->rc.qpMax = qpMax;',
                    '}',
                    'OPT("qpmax")',
                    '{',
                    '    svtHevcParam->maxQpAllowed = maxQpAllowed;',
                    '}',
                    'OPT("rc-lookahead")',
                    '{',
                    '    something_else();',
                    '}',
                    'OPT("qpmax")',
                    '{',
                    '    bool bMaxQpAllowedError = false;',
                    '    int maxQpAllowed = parseOptionIntValue(value, bMaxQpAllowedError);',
                    '    bError |= bMaxQpAllowedError;',
                    '    if (!bMaxQpAllowedError)',
                    '        svtHevcParam->maxQpAllowed = maxQpAllowed;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT qpmax parse block must gate assignment on parseOptionIntValue success')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    '    OPT("qpmax")',
                    '    {',
                    '        bool bMaxQpAllowedError = false;',
                    '        int maxQpAllowed = parseOptionIntValue(value, bMaxQpAllowedError);',
                    '        bError |= bMaxQpAllowedError;',
                    '        if (!bMaxQpAllowedError)',
                    '            svtHevcParam->maxQpAllowed = maxQpAllowed;',
                    '    }',
                    '}',
                    'int svt_param_parse(x265_param* param, const char* name, const char* value)',
                    '{',
                    '    OPT("qpmax")',
                    '    {',
                    '        int maxQpAllowed = parseOptionIntValue(value, bMaxQpAllowedError);',
                    '        bError |= bMaxQpAllowedError;',
                    '        if (!bMaxQpAllowedError)',
                    '            svtHevcParam->maxQpAllowed = maxQpAllowed;',
                    '    }',
                    '    return bError ? X265_PARAM_BAD_VALUE : 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing SVT qpmax guardrail in parse block: bool bMaxQpAllowedError = false;')

    print('SVT qpmax parse safety tests passed')


if __name__ == '__main__':
    main()
