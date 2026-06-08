#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_init_output_null_guard.py')

# Coverage probe used by the scan for the reviewed ABR init output guard.
NORMALIZED_PROBES = (
    'PassEncoder::init must guard null output before using m_cliopt.output',
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
                'source/abrEncApp.cpp': '\n'.join((
                    'if (!m_cliopt.output)',
                    '{',
                    '    rollbackInputHelper();',
                    '    m_ret = 3;',
                    '    if (!result)',
                    '        result = m_ret;',
                    '    return -1;',
                    '}',
                    'm_cliopt.output->setParam(m_param);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/abrEncApp.cpp': 'm_cliopt.output->setParam(m_param);\n'})
        expect_fail(run_checker(root), 'missing ABR init output null guardrail: if (!m_cliopt.output)')

    print('ABR init output null guard tests passed')


if __name__ == '__main__':
    main()
