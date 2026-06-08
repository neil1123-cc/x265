#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ssim_rd_parse_safety.py')


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
                    'OPT("ssim-rd")',
                    '{',
                    '    bool bSsimRdError = false;',
                    '    int bSsimRd = x265_atobool(value, bSsimRdError);',
                    '    bError |= bSsimRdError;',
                    '    if (!bSsimRdError)',
                    '    {',
                    '        p->bSsimRd = bSsimRd;',
                    '        if (bSsimRd)',
                    '            p->psyRd = 0.0;',
                    '    }',
                    '}',
                    'OPT("hdr")',
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
                    'OPT("ssim-rd")',
                    '{',
                    '    int bSsimRd = x265_atobool(value, bSsimRdError);',
                    '    bError |= bSsimRdError;',
                    '    if (!bSsimRdError)',
                    '    {',
                    '        p->bSsimRd = bSsimRd;',
                    '        if (bSsimRd)',
                    '            p->psyRd = 0.0;',
                    '    }',
                    '}',
                    'OPT("hdr")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing ssim-rd guardrail: bool bSsimRdError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("ssim-rd")',
                    '{',
                    '    int bval = atobool(value);',
                    '    if (bError || bval)',
                    '    {',
                    '        bError = false;',
                    '        p->psyRd = 0.0;',
                    '        p->bSsimRd = atobool(value);',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ssim-rd regression: invalid values must not clear parse errors or mutate psyRd')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("ssim-rd")',
                    '{',
                    '    bool bSsimRdError = false;',
                    '    int bSsimRd = x265_atobool(value, bSsimRdError);',
                    '    bError |= bSsimRdError;',
                    '    if (!bSsimRdError)',
                    '    {',
                    '        if (bSsimRd)',
                    '            p->psyRd = 0.0;',
                    '        p->bSsimRd = bSsimRd;',
                    '    }',
                    '}',
                    'OPT("hdr")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'ssim-rd parsing must keep the bool parse gate ahead of bSsimRd publication and psyRd zeroing')

    print('Ssim-rd parse safety tests passed')

if __name__ == '__main__':
    main()
