#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_qp_mode_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing qp mode guardrail: ',
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
    'bool bQpValueError = false;',
    'int qp = parseOptionIntValue(value, bQpValueError);',
    'bError |= bQpValueError;',
    'if (!bQpValueError)',
    '{',
    '    p->rc.qp = qp;',
    '    p->rc.rateControlMode = X265_RC_CQP;',
    '}',
    'bool bQpValueError = false;',
    'int qp = parseOptionIntValue(value, bQpValueError);',
    'bError |= bQpValueError;',
    'if (!bQpValueError)',
    '{',
    '    p->rc.qp = qp;',
    '    p->rc.rateControlMode = X265_RC_CQP;',
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
                    '    p->rc.qp = x265_atoi(value, bError);',
                    '        p->rc.rateControlMode = X265_RC_CQP;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden qp mode regression: invalid qp must not switch rate control mode')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'if (!bQpValueError)',
                    'if (!bQpModeError)',
                ),
            },
        )
        expect_fail(run_checker(root), 'missing qp mode guardrail: if (!bQpValueError)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'bool bQpValueError = false;',
                    'bool bOtherError = false;',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing qp mode guardrail in both param parsers')

    print('QP mode parse safety tests passed')


if __name__ == '__main__':
    main()
