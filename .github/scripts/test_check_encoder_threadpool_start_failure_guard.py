#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_encoder_threadpool_start_failure_guard.py')

# Coverage probe used by the scan for the reviewed thread-pool startup failure guard.
NORMALIZED_PROBES = (
    'Encoder::create must abort and return before continuing initialization when a thread pool fails to start',
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
                    'for (int j = 0; j < m_numPools; j++)',
                    '{',
                    '    if (!m_threadPool[j].start())',
                    '    {',
                    '        x265_log(m_param, X265_LOG_ERROR, "Unable to start thread pool %d, aborting\\n", j);',
                    '        m_aborted = true;',
                    '        break;',
                    '    }',
                    '}',
                    'if (m_aborted)',
                    '    return;',
                    'if (!m_scalingList.init())',
                    '{',
                    '    m_aborted = true;',
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
                'source/encoder/encoder.cpp': '\n'.join((
                    'for (int j = 0; j < m_numPools; j++)',
                    '    m_threadPool[j].start();',
                    'if (!m_scalingList.init())',
                    '    m_aborted = true;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing encoder threadpool start failure guardrail: if (!m_threadPool[j].start())')

    print('Encoder threadpool start failure guard tests passed')


if __name__ == '__main__':
    main()
