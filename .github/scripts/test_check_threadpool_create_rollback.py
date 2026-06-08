#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_threadpool_create_rollback.py')

# Coverage probes used by the scan for threadpool create-rollback guardrails.
NORMALIZED_PROBES = (
    'ThreadPool::allocThreadPools must use nothrow allocations and roll back pool state before returning nullptr',
    'forbidden threadpool create rollback regression: ',
    'missing threadpool create rollback guardrail: ',
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
                    'ThreadPool *pools = new (std::nothrow) ThreadPool[numPools];',
                    'char *nodesstr = new (std::nothrow) char[64 * std::strlen(",63") + 1];',
                    'if (!nodesstr)',
                    '{',
                    '    x265_log(p, X265_LOG_ERROR, "Unable to allocate thread pool NUMA log buffer\\n");',
                    '    delete[] pools;',
                    '    numPools = 0;',
                    '    return nullptr;',
                    '}',
                    'WorkerThread* stagedWorkers = X265_MALLOC(WorkerThread, numThreads);',
                    'if (stagedWorkers)',
                    'new (stagedWorkers + i)WorkerThread(*this, i);',
                    'JobProvider** stagedJpTable = X265_MALLOC(JobProvider*, maxProviders);',
                    'if (!stagedWorkers || !stagedJpTable)',
                    'stagedWorkers[i].~WorkerThread();',
                    'X265_FREE(stagedWorkers);',
                    'X265_FREE(stagedJpTable);',
                    'm_numWorkers = 0;',
                    'm_workers = stagedWorkers;',
                    'm_jpTable = stagedJpTable;',
                    'return true;',
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
                    'ThreadPool *pools = new ThreadPool[numPools];',
                    'char *nodesstr = new char[64 * std::strlen(",63") + 1];',
                    'm_workers = X265_MALLOC(WorkerThread, numThreads);',
                    'm_jpTable = X265_MALLOC(JobProvider*, maxProviders);',
                    'return m_workers && m_jpTable;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden threadpool create rollback regression')

    print('Threadpool create rollback tests passed')


if __name__ == '__main__':
    main()
