#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_threadedme_start_failure_guard.py')

# Coverage probes used by the scan for threadedME start-failure guardrails.
NORMALIZED_PROBES = (
    'Encoder::create must stop jobs and disable threadedME when its worker thread fails to start',
    'missing threadedME frameencoder guardrail: if (m_top->m_threadedME && m_param->bThreadedME && !slice->isIntra())',
    'missing file',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (!m_threadedME->start())',
                    '{',
                    '    m_threadedME->stopJobs();',
                    '    m_param->bThreadedME = 0;',
                    '    x265_log(m_param, X265_LOG_ERROR, "Failed to start threadedME thread pool, --threaded-me disabled");',
                    '}',
                )) + '\n',
                'source/encoder/frameencoder.cpp': '\n'.join((
                    'if (m_top->m_threadedME && m_param->bThreadedME && !slice->isIntra())',
                    '    enqueue();',
                    'if (m_top->m_threadedME && m_param->bThreadedME && slice->m_sliceType != I_SLICE)',
                    '    wait();',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': 'm_threadedME->start();\n',
                'source/encoder/frameencoder.cpp': 'if (m_top->m_threadedME && !slice->isIntra())\n    enqueue();\n',
            },
        )
        expect_fail(run_checker(root), 'missing threadedME start failure guardrail: if (!m_threadedME->start())')

    print('ThreadedME start failure guard tests passed')


if __name__ == '__main__':
    main()
