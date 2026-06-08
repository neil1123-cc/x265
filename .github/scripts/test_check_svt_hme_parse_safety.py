#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_hme_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing SVT HME guardrail: ',
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


PASS_SOURCE = '\n'.join((
    'OPT("svt-hme")',
    '{',
    '    int bEnableHme = x265_atobool(value, bError);',
    '    if (!bError)',
    '    {',
    '        svtHevcParam->enableHmeFlag = (uint8_t)bEnableHme;',
    '        if (svtHevcParam->enableHmeFlag)',
    '            svtHevcParam->useDefaultMeHme = 1;',
    '    }',
    '}',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("svt-hme")',
                    '{',
                    '    svtHevcParam->enableHmeFlag = (uint8_t)x265_atobool(value, bError);',
                    '    if (svtHevcParam->enableHmeFlag) svtHevcParam->useDefaultMeHme = 1;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT HME regression: parse result must be separated from state updates')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '        if (svtHevcParam->enableHmeFlag)\n'
                    '            svtHevcParam->useDefaultMeHme = 1;',
                    '        if (svtHevcParam->enableHmeFlag) svtHevcParam->useDefaultMeHme = 1;',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT HME regression: default HME settings must not change on parse failure')

    print('SVT HME parse safety tests passed')


if __name__ == '__main__':
    main()
