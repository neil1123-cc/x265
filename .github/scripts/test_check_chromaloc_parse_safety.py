#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_chromaloc_parse_safety.py')


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
                    'OPT("chromaloc")',
                    '{',
                    '    bool bChromaSampleLocTypeError = false;',
                    '    int chromaSampleLocType = parseOptionIntValue(value, bChromaSampleLocTypeError);',
                    '    bError |= bChromaSampleLocTypeError;',
                    '    if (!bChromaSampleLocTypeError)',
                    '    {',
                    '        p->vui.bEnableChromaLocInfoPresentFlag = 1;',
                    '        p->vui.chromaSampleLocTypeTopField = chromaSampleLocType;',
                    '        p->vui.chromaSampleLocTypeBottomField = chromaSampleLocType;',
                    '    }',
                    '}',
                    'OPT("display-window")',
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
                    'OPT("chromaloc")',
                    '{',
                    '    int chromaSampleLocType = parseOptionIntValue(value, bChromaSampleLocTypeError);',
                    '    bError |= bChromaSampleLocTypeError;',
                    '    if (!bChromaSampleLocTypeError)',
                    '    {',
                    '        p->vui.bEnableChromaLocInfoPresentFlag = 1;',
                    '        p->vui.chromaSampleLocTypeTopField = chromaSampleLocType;',
                    '        p->vui.chromaSampleLocTypeBottomField = chromaSampleLocType;',
                    '    }',
                    '}',
                    'OPT("display-window")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing chromaloc guardrail: bool bChromaSampleLocTypeError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("chromaloc")',
                    '{',
                    '    p->vui.bEnableChromaLocInfoPresentFlag = 1;',
                    '    p->vui.chromaSampleLocTypeTopField = x265_atoi(value, bError);',
                    '    p->vui.chromaSampleLocTypeBottomField = p->vui.chromaSampleLocTypeTopField;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden chromaloc regression: invalid values must not update VUI chroma location state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("chromaloc")',
                    '{',
                    '    bool bChromaSampleLocTypeError = false;',
                    '    int chromaSampleLocType = parseOptionIntValue(value, bChromaSampleLocTypeError);',
                    '    bError |= bChromaSampleLocTypeError;',
                    '    if (!bChromaSampleLocTypeError)',
                    '    {',
                    '        p->vui.chromaSampleLocTypeBottomField = chromaSampleLocType;',
                    '        p->vui.bEnableChromaLocInfoPresentFlag = 1;',
                    '        p->vui.chromaSampleLocTypeTopField = chromaSampleLocType;',
                    '    }',
                    '}',
                    'OPT("display-window")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'chromaloc parsing must keep the parse gate ahead of VUI chroma-location state publication')

    print('Chromaloc parse safety tests passed')


if __name__ == '__main__':
    main()
