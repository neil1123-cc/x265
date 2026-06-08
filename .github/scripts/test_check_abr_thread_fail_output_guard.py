#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_fail_output_guard.py')

# Coverage probe used by the scan for the reviewed ABR output cleanup guard.
NORMALIZED_PROBES = (
    'PassEncoder::threadMain fail cleanup must guard output before closeFile/isFail',
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
                    'pts_queue = nullptr;',
                    'if (m_cliopt.output)',
                    '{',
                    '    m_cliopt.output->closeFile(largest_pts, second_largest_pts);',
                    '    if (m_cliopt.output->isFail() && !m_ret)',
                    '        m_ret = 3;',
                    '}',
                    'else if (!m_ret)',
                    '    m_ret = 3;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': 'm_cliopt.output->closeFile(largest_pts, second_largest_pts);\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR thread fail output guardrail: if (m_cliopt.output)')

    print('ABR thread fail output guard tests passed')


if __name__ == '__main__':
    main()
