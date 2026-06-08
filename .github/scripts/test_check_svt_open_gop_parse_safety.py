#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_open_gop_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing SVT open-gop guardrail: ',
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
    'OPT("open-gop")',
    '{',
    '    int bOpenGop = x265_atobool(value, bError);',
    '    if (!bError && bOpenGop)',
    '        svtHevcParam->intraRefreshType = 1;',
    '    else if (!bError)',
    '        svtHevcParam->intraRefreshType = 2;',
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
                    'OPT("open-gop")',
                    '{',
                    '    if (x265_atobool(value, bError))',
                    '        svtHevcParam->intraRefreshType = 1;',
                    '    else',
                    '        svtHevcParam->intraRefreshType = 2;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT open-gop regression: parse result must be separated from error handling')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE + '\n'.join((
                    'OPT("open-gop")',
                    '{',
                    '    int bOpenGop = x265_atobool(value, bError);',
                    '    if (!bError && bOpenGop)',
                    '        svtHevcParam->intraRefreshType = 1;',
                    '    else',
                    '            svtHevcParam->intraRefreshType = 2;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT open-gop regression: invalid values must not silently force closed GOP')

    print('SVT open-gop parse safety tests passed')


if __name__ == '__main__':
    main()
