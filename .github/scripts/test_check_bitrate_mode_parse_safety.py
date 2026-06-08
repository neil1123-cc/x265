#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_bitrate_mode_parse_safety.py')

# Normalized checker probe used by the coverage scan for function-labeled parse blocks.
NORMALIZED_PROBES = (
    'missing bitrate mode guardrail in  parse block: ',
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
                    'int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '    OPT("bitrate")',
                    '    {',
                    '        bool bBitrateValueError = false;',
                    '        int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '        bError |= bBitrateValueError;',
                    '        if (!bBitrateValueError)',
                    '        {',
                    '            p->rc.bitrate = bitrate;',
                    '            p->rc.rateControlMode = X265_RC_ABR;',
                    '        }',
                    '    }',
                    '}',
                    'int x265_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '    OPT("bitrate")',
                    '    {',
                    '        bool bBitrateValueError = false;',
                    '        int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '        bError |= bBitrateValueError;',
                    '        if (!bBitrateValueError)',
                    '        {',
                    '            p->rc.bitrate = bitrate;',
                    '            p->rc.rateControlMode = X265_RC_ABR;',
                    '        }',
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
                    '    p->rc.bitrate = x265_atoi(value, bError);',
                    '        p->rc.rateControlMode = X265_RC_ABR;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden bitrate mode regression: invalid bitrate must not switch rate control mode')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '    OPT("bitrate")',
                    '    {',
                    '        p->rc.rateControlMode = X265_RC_ABR;',
                    '    }',
                    '}',
                    'int x265_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '    OPT("bitrate")',
                    '    {',
                    '        bool bBitrateValueError = false;',
                    '        int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '        bError |= bBitrateValueError;',
                    '        if (!bBitrateValueError)',
                    '        {',
                    '            p->rc.bitrate = bitrate;',
                    '            p->rc.rateControlMode = X265_RC_ABR;',
                    '        }',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_scenecut_aware_qp_param_parse bitrate parse block must gate ABR mode switch on parseOptionIntValue success')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    '    bool bBitrateValueError = false;',
                    '    int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '    bError |= bBitrateValueError;',
                    '    if (!bBitrateValueError)',
                    '    {',
                    '        p->rc.bitrate = bitrate;',
                    '        p->rc.rateControlMode = X265_RC_ABR;',
                    '    }',
                    '}',
                    'int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '    OPT("bitrate")',
                    '    {',
                    '        int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '        bError |= bBitrateValueError;',
                    '        if (!bBitrateValueError)',
                    '        {',
                    '            p->rc.bitrate = bitrate;',
                    '            p->rc.rateControlMode = X265_RC_ABR;',
                    '        }',
                    '    }',
                    '}',
                    'int x265_param_parse(x265_param* p, const char* name, const char* value)',
                    '{',
                    '    OPT("bitrate")',
                    '    {',
                    '        bool bBitrateValueError = false;',
                    '        int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    '        bError |= bBitrateValueError;',
                    '        if (!bBitrateValueError)',
                    '        {',
                    '            p->rc.bitrate = bitrate;',
                    '            p->rc.rateControlMode = X265_RC_ABR;',
                    '        }',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing bitrate mode guardrail in x265_scenecut_aware_qp_param_parse parse block: bool bBitrateValueError = false;')

    print('Bitrate mode parse safety tests passed')


if __name__ == '__main__':
    main()
