#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vbv_bufsize_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing SVT vbv-bufsize guardrail: ',
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
                    'OPT("vbv-bufsize")',
                    '{',
                    '    bool bVbvBufferSizeError = false;',
                    '    int vbvBufferSize = parseOptionIntValue(value, bVbvBufferSizeError);',
                    '    bError |= bVbvBufferSizeError;',
                    '    if (!bVbvBufferSizeError)',
                    '        p->rc.vbvBufferSize = vbvBufferSize;',
                    '}',
                    'OPT("vbv-bufsize")',
                    '{',
                    '    bool bVbvBufsizeError = false;',
                    '    int vbvBufsize = parseOptionIntValue(value, bVbvBufsizeError);',
                    '    bError |= bVbvBufsizeError;',
                    '    if (!bVbvBufsizeError)',
                    '        svtHevcParam->vbvBufsize = (uint32_t)vbvBufsize;',
                    '}',
                    'OPT("vbv-init")',
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
                'source/common/param.cpp': 'OPT("vbv-bufsize") svtHevcParam->vbvBufsize = (uint32_t)x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT vbv-bufsize regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("vbv-bufsize")',
                    '{',
                    '    bool bVbvBufferSizeError = false;',
                    '    int vbvBufferSize = parseOptionIntValue(value, bVbvBufferSizeError);',
                    '    bError |= bVbvBufferSizeError;',
                    '    if (!bVbvBufferSizeError)',
                    '        p->rc.vbvBufferSize = vbvBufferSize;',
                    '}',
                    'OPT("vbv-bufsize")',
                    '{',
                    '    svtHevcParam->vbvBufsize = (uint32_t)vbvBufsize;',
                    '}',
                    'OPT("vbv-init")',
                    '{',
                    '    something_else();',
                    '}',
                    'OPT("vbv-bufsize")',
                    '{',
                    '    bool bVbvBufsizeError = false;',
                    '    int vbvBufsize = parseOptionIntValue(value, bVbvBufsizeError);',
                    '    bError |= bVbvBufsizeError;',
                    '    if (!bVbvBufsizeError)',
                    '        svtHevcParam->vbvBufsize = (uint32_t)vbvBufsize;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT vbv-bufsize parse block must gate assignment on parseOptionIntValue success')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    '    OPT("vbv-bufsize")',
                    '    {',
                    '        bool bVbvBufsizeError = false;',
                    '        int vbvBufsize = parseOptionIntValue(value, bVbvBufsizeError);',
                    '        bError |= bVbvBufsizeError;',
                    '        if (!bVbvBufsizeError)',
                    '            svtHevcParam->vbvBufsize = (uint32_t)vbvBufsize;',
                    '    }',
                    '}',
                    'int svt_param_parse(x265_param* param, const char* name, const char* value)',
                    '{',
                    '    OPT("vbv-bufsize")',
                    '    {',
                    '        something_else();',
                    '    }',
                    '    return bError ? X265_PARAM_BAD_VALUE : 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT vbv-bufsize parse block must gate assignment on parseOptionIntValue success')

    print('SVT vbv-bufsize parse safety tests passed')


if __name__ == '__main__':
    main()
