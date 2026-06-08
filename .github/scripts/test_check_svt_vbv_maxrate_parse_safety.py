#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_vbv_maxrate_parse_safety.py')


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
                    'OPT("vbv-maxrate")',
                    '{',
                    '    bool bVbvMaxrateError = false;',
                    '    int vbvMaxrate = parseOptionIntValue(value, bVbvMaxrateError);',
                    '    bError |= bVbvMaxrateError;',
                    '    if (!bVbvMaxrateError)',
                    '        svtHevcParam->vbvMaxrate = (uint32_t)vbvMaxrate;',
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
                'source/common/param.cpp': 'svtHevcParam->vbvMaxrate = (uint32_t)x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT vbv-maxrate regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("vbv-maxrate")',
                    '{',
                    '    svtHevcParam->vbvMaxrate = (uint32_t)vbvMaxrate;',
                    '}',
                    'OPT("vbv-bufsize")',
                    '{',
                    '    something_else();',
                    '}',
                    'OPT("vbv-maxrate")',
                    '{',
                    '    bool bVbvMaxrateError = false;',
                    '    int vbvMaxrate = parseOptionIntValue(value, bVbvMaxrateError);',
                    '    bError |= bVbvMaxrateError;',
                    '    if (!bVbvMaxrateError)',
                    '        svtHevcParam->vbvMaxrate = (uint32_t)vbvMaxrate;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT vbv-maxrate parse block must gate assignment on parseOptionIntValue success')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    '    OPT("vbv-maxrate")',
                    '    {',
                    '        bool bVbvMaxrateError = false;',
                    '        int vbvMaxrate = parseOptionIntValue(value, bVbvMaxrateError);',
                    '        bError |= bVbvMaxrateError;',
                    '        if (!bVbvMaxrateError)',
                    '            svtHevcParam->vbvMaxrate = (uint32_t)vbvMaxrate;',
                    '    }',
                    '}',
                    'int svt_param_parse(x265_param* param, const char* name, const char* value)',
                    '{',
                    '    OPT("vbv-maxrate")',
                    '    {',
                    '        int vbvMaxrate = parseOptionIntValue(value, bVbvMaxrateError);',
                    '        bError |= bVbvMaxrateError;',
                    '        if (!bVbvMaxrateError)',
                    '            svtHevcParam->vbvMaxrate = (uint32_t)vbvMaxrate;',
                    '    }',
                    '    return bError ? X265_PARAM_BAD_VALUE : 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing SVT vbv-maxrate guardrail in parse block: bool bVbvMaxrateError = false;')

    print('SVT vbv-maxrate parse safety tests passed')


if __name__ == '__main__':
    main()
