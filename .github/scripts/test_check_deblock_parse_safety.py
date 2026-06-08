#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_deblock_parse_safety.py')


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
                    'OPT("deblock")',
                    '{',
                    '    const char* separator = std::strchr(value, \':\');',
                    '    if (!separator)',
                    '        separator = std::strchr(value, \',\');',
                    '    if (separator)',
                    '    {',
                    '        int tcOffset = 0;',
                    '        int betaOffset = 0;',
                    '        bool bLocalError = !parseOptionIntPair(value, *separator, tcOffset, betaOffset);',
                    '        if (!bLocalError)',
                    '        {',
                    '            p->deblockingFilterTCOffset = tcOffset;',
                    '            p->deblockingFilterBetaOffset = betaOffset;',
                    '        }',
                    '        if (bLocalError)',
                    '            bError = true;',
                    '        else',
                    '            p->bEnableLoopFilter = true;',
                    '    }',
                    '    else',
                    '    {',
                    '        bool bLocalError = false;',
                    '        int offset = parseOptionIntToken(value, std::strlen(value), bLocalError);',
                    '        if (!bLocalError)',
                    '        {',
                    '            p->bEnableLoopFilter = 1;',
                    '            p->deblockingFilterTCOffset = offset;',
                    '            p->deblockingFilterBetaOffset = offset;',
                    '        }',
                    '        else',
                    '            p->bEnableLoopFilter = atobool(value);',
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
                    'OPT("deblock")',
                    '{',
                    '    const char* separator = std::strchr(value, \':\');',
                    '    if (!separator)',
                    '        separator = std::strchr(value, \',\');',
                    '    if (separator)',
                    '    {',
                    '        int betaOffset = 0;',
                    '        bool bLocalError = !parseOptionIntPair(value, *separator, tcOffset, betaOffset);',
                    '        if (!bLocalError)',
                    '        {',
                    '            p->deblockingFilterTCOffset = tcOffset;',
                    '            p->deblockingFilterBetaOffset = betaOffset;',
                    '        }',
                    '    }',
                    '    else',
                    '    {',
                    '        bool bLocalError = false;',
                    '        int offset = parseOptionIntToken(value, std::strlen(value), bLocalError);',
                    '        p->bEnableLoopFilter = atobool(value);',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing deblock guardrail: int tcOffset = 0;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("deblock")',
                    '{',
                    '    p->deblockingFilterTCOffset = parseOptionIntToken(value, leftLength, bLocalError);',
                    '    p->deblockingFilterBetaOffset = parseOptionIntToken(separator + 1, rightLength, bLocalError);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden deblock regression: invalid values must not partially overwrite deblock state')

    print('Deblock parse safety tests passed')


if __name__ == '__main__':
    main()
