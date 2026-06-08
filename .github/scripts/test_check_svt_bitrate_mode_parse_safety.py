#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_bitrate_mode_parse_safety.py')


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
                    'OPT("bitrate")',
                    '{',
                    '    bool bBitrateValueError = false;',
                    '    int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '    bError |= bBitrateValueError;',
                    '    if (!bBitrateValueError)',
                    '    {',
                    '        svtHevcParam->rateControlMode = 1;',
                    '        svtHevcParam->targetBitRate = bitrate;',
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
                    'OPT("bitrate")',
                    '{',
                    '    svtHevcParam->rateControlMode = 1;',
                    '    svtHevcParam->targetBitRate = x265_atoi(value, bError);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT bitrate mode regression: invalid bitrate must not switch SVT rate control mode')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("bitrate")',
                    '{',
                    '    svtHevcParam->targetBitRate = bitrate;',
                    '}',
                    'OPT("qp")',
                    '{',
                    '    something_else();',
                    '}',
                    'OPT("bitrate")',
                    '{',
                    '    bool bBitrateValueError = false;',
                    '    int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '    bError |= bBitrateValueError;',
                    '    if (!bBitrateValueError)',
                    '    {',
                    '        svtHevcParam->rateControlMode = 1;',
                    '        svtHevcParam->targetBitRate = bitrate;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT bitrate parse block must gate rate control mode switch on parseOptionIntValue success')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    '    OPT("bitrate")',
                    '    {',
                    '        bool bBitrateValueError = false;',
                    '        int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '        bError |= bBitrateValueError;',
                    '        if (!bBitrateValueError)',
                    '        {',
                    '            svtHevcParam->rateControlMode = 1;',
                    '            svtHevcParam->targetBitRate = bitrate;',
                    '        }',
                    '    }',
                    '}',
                    'int svt_param_parse(x265_param* param, const char* name, const char* value)',
                    '{',
                    '    OPT("bitrate")',
                    '    {',
                    '        int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '        bError |= bBitrateValueError;',
                    '        if (!bBitrateValueError)',
                    '        {',
                    '            svtHevcParam->rateControlMode = 1;',
                    '            svtHevcParam->targetBitRate = bitrate;',
                    '        }',
                    '    }',
                    '    return bError ? X265_PARAM_BAD_VALUE : 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing SVT bitrate mode guardrail in parse block: bool bBitrateValueError = false;')

    print('SVT bitrate mode parse safety tests passed')


if __name__ == '__main__':
    main()
