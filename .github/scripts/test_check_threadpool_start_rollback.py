#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_threadpool_start_rollback.py')

# Coverage probes used by the scan for threadpool start rollback guardrails.
NORMALIZED_PROBES = (
    'ThreadPool::start should stop already-started workers before returning false',
    'missing threadpool start rollback guardrail: ',
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
                'source/common/threadpool.cpp': '\n'.join((
                    'bool ThreadPool::start()',
                    '{',
                    '    m_isActive.store(true);',
                    '    for (int i = 0; i < m_numWorkers; i++)',
                    '    {',
                    '        if (!m_workers[i].start())',
                    '        {',
                    '            m_isActive.store(false);',
                    '            for (int j = 0; j < i; j++)',
                    '            {',
                    '                while (!(SLEEPBITMAP_LOAD(&m_sleepBitmap) & ((sleepbitmap_t)1 << j)))',
                    '                    GIVE_UP_TIME();',
                    '                m_workers[j].awaken();',
                    '                m_workers[j].stop();',
                    '            }',
                    '            return false;',
                    '        }',
                    '    }',
                    '    return true;',
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
                'source/common/threadpool.cpp': '\n'.join((
                    'bool ThreadPool::start()',
                    '{',
                    '    if (!m_workers[i].start())',
                    '        return false;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing threadpool start rollback guardrail')

    print('ThreadPool start rollback tests passed')


if __name__ == '__main__':
    main()
