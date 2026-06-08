#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_misc_control_parse_safety.py')


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
                    'OPT("ctu-info")',
                    '{',
                    '    bool bCTUInfoError = false;',
                    '    int ctuInfo = parseOptionIntValue(value, bCTUInfoError);',
                    '    bError |= bCTUInfoError;',
                    '    if (!bCTUInfoError)',
                    '        p->bCTUInfo = ctuInfo;',
                    '}',
                    'OPT("force-flush")',
                    '{',
                    '    bool bForceFlushError = false;',
                    '    int forceFlush = parseOptionIntValue(value, bForceFlushError);',
                    '    bError |= bForceFlushError;',
                    '    if (!bForceFlushError)',
                    '        p->forceFlush = forceFlush;',
                    '}',
                    'OPT("splitrd-skip")',
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
                    'OPT("ctu-info")',
                    '{',
                    '    bool bCTUInfoError = false;',
                    '    int ctuInfo = parseOptionIntValue(value, bCTUInfoError);',
                    '    bError |= bCTUInfoError;',
                    '    if (!bCTUInfoError)',
                    '        p->bCTUInfo = ctuInfo;',
                    '}',
                    'OPT("force-flush")',
                    '{',
                    '    int forceFlush = parseOptionIntValue(value, bForceFlushError);',
                    '    bError |= bForceFlushError;',
                    '    if (!bForceFlushError)',
                    '        p->forceFlush = forceFlush;',
                    '}',
                    'OPT("splitrd-skip")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing misc-control guardrail: bool bForceFlushError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("ctu-info") p->bCTUInfo = x265_atoi(value, bError);',
                    'OPT("force-flush")p->forceFlush = x265_atoi(value, bError);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden misc-control regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("ctu-info")',
                    '{',
                    '    bool bCTUInfoError = false;',
                    '    int ctuInfo = parseOptionIntValue(value, bCTUInfoError);',
                    '    bError |= bCTUInfoError;',
                    '    if (!bCTUInfoError)',
                    '        p->bCTUInfo = ctuInfo;',
                    '}',
                    'OPT("force-flush")',
                    '{',
                    '    bool bForceFlushError = false;',
                    '    int forceFlush = parseOptionIntValue(value, bForceFlushError);',
                    '    bError |= bForceFlushError;',
                    '        p->forceFlush = forceFlush;',
                    '    if (!bForceFlushError)',
                    '}',
                    'OPT("splitrd-skip")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Misc control parsing must stage parsed integers and only publish them after the reviewed error gates succeed')

    print('Misc control parse safety tests passed')

if __name__ == '__main__':
    main()
