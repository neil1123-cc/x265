#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_qp_mode_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing SVT qp mode guardrail: ',
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
                    'OPT("qp")',
                    '{',
                    '    bool bQpValueError = false;',
                    '    int qp = parseOptionIntValue(value, bQpValueError);',
                    '    bError |= bQpValueError;',
                    '    if (!bQpValueError)',
                    '    {',
                    '        svtHevcParam->rateControlMode = 0;',
                    '        svtHevcParam->qp = qp;',
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
                    'OPT("qp")',
                    '{',
                    '    svtHevcParam->rateControlMode = 0;',
                    '    svtHevcParam->qp = x265_atoi(value, bError);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT qp mode regression: invalid qp must not switch SVT rate control mode')

    print('SVT qp mode parse safety tests passed')


if __name__ == '__main__':
    main()
