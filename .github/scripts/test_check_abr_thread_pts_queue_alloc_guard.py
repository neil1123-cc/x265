#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_thread_pts_queue_alloc_guard.py')

# Coverage probes used by the scan for ABR PTS queue allocation guardrails.
NORMALIZED_PROBES = (
    'PassEncoder::threadMain must guard PTS queue allocation before use',
    'forbidden ABR thread PTS queue allocation pattern: ',
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
                    'std::priority_queue<int64_t>* pts_queue = nullptr;',
                    'pts_queue = m_cliopt.output->needPTS() ? new (std::nothrow) std::priority_queue<int64_t>() : nullptr;',
                    'if (m_cliopt.output->needPTS() && !pts_queue)',
                    '{',
                    '    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate PTS queue in %s\\n",',
                    '        m_cliopt.encName[0] ? m_cliopt.encName : "x265");',
                    '    m_ret = 4;',
                    '    goto fail;',
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
                'source/abrEncApp.cpp': 'pts_queue = m_cliopt.output->needPTS() ? new std::priority_queue<int64_t>() : nullptr;\n',
            },
        )
        expect_fail(run_checker(root), 'missing ABR thread PTS queue alloc guardrail: std::priority_queue<int64_t>* pts_queue = nullptr;')

    print('ABR thread PTS queue allocation guard tests passed')


if __name__ == '__main__':
    main()
