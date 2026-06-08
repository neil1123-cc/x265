#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_psy_scale_parse_safety.py')


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
                    'OPT("psy-bscale")',
                    '{',
                    '    bool bPsyScaleBError = false;',
                    '    int psyScaleB = parseOptionIntValue(value, bPsyScaleBError);',
                    '    bError |= bPsyScaleBError;',
                    '    if (!bPsyScaleBError)',
                    '        p->psyScaleB = psyScaleB;',
                    '}',
                    'OPT("psy-pscale")',
                    '{',
                    '    bool bPsyScalePError = false;',
                    '    int psyScaleP = parseOptionIntValue(value, bPsyScalePError);',
                    '    bError |= bPsyScalePError;',
                    '    if (!bPsyScalePError)',
                    '        p->psyScaleP = psyScaleP;',
                    '}',
                    'OPT("psy-iscale")',
                    '{',
                    '    bool bPsyScaleIError = false;',
                    '    int psyScaleI = parseOptionIntValue(value, bPsyScaleIError);',
                    '    bError |= bPsyScaleIError;',
                    '    if (!bPsyScaleIError)',
                    '        p->psyScaleI = psyScaleI;',
                    '}',
                    'OPT("rd-refine")',
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
                    'OPT("psy-bscale")',
                    '{',
                    '    int psyScaleB = parseOptionIntValue(value, bPsyScaleBError);',
                    '    bError |= bPsyScaleBError;',
                    '    if (!bPsyScaleBError)',
                    '        p->psyScaleB = psyScaleB;',
                    '}',
                    'OPT("psy-pscale")',
                    '{',
                    '    bool bPsyScalePError = false;',
                    '    int psyScaleP = parseOptionIntValue(value, bPsyScalePError);',
                    '    bError |= bPsyScalePError;',
                    '    if (!bPsyScalePError)',
                    '        p->psyScaleP = psyScaleP;',
                    '}',
                    'OPT("psy-iscale")',
                    '{',
                    '    bool bPsyScaleIError = false;',
                    '    int psyScaleI = parseOptionIntValue(value, bPsyScaleIError);',
                    '    bError |= bPsyScaleIError;',
                    '    if (!bPsyScaleIError)',
                    '        p->psyScaleI = psyScaleI;',
                    '}',
                    'OPT("rd-refine")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing psy-scale guardrail: bool bPsyScaleBError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("psy-bscale") p->psyScaleB = x265_atoi(value, bError);',
                    'OPT("psy-pscale") p->psyScaleP = x265_atoi(value, bError);',
                    'OPT("psy-iscale") p->psyScaleI = x265_atoi(value, bError);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden psy-scale regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("psy-bscale")',
                    '{',
                    '    bool bPsyScaleBError = false;',
                    '    int psyScaleB = parseOptionIntValue(value, bPsyScaleBError);',
                    '    bError |= bPsyScaleBError;',
                    '    if (!bPsyScaleBError)',
                    '        p->psyScaleB = psyScaleB;',
                    '}',
                    'OPT("psy-pscale")',
                    '{',
                    '    bool bPsyScalePError = false;',
                    '    int psyScaleP = parseOptionIntValue(value, bPsyScalePError);',
                    '    bError |= bPsyScalePError;',
                    '        p->psyScaleP = psyScaleP;',
                    '    if (!bPsyScalePError)',
                    '}',
                    'OPT("psy-iscale")',
                    '{',
                    '    bool bPsyScaleIError = false;',
                    '    int psyScaleI = parseOptionIntValue(value, bPsyScaleIError);',
                    '    bError |= bPsyScaleIError;',
                    '    if (!bPsyScaleIError)',
                    '        p->psyScaleI = psyScaleI;',
                    '}',
                    'OPT("rd-refine")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Psy-scale parsing must stage parsed integers and only publish them after the reviewed error gates succeed')

    print('Psy scale parse safety tests passed')

if __name__ == '__main__':
    main()
