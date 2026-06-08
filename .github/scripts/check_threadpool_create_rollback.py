#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/threadpool.cpp')
REQUIRED_SNIPPETS = (
    'ThreadPool *pools = new (std::nothrow) ThreadPool[numPools];',
    'char *nodesstr = new (std::nothrow) char[64 * std::strlen(",63") + 1];',
    'if (!nodesstr)',
    'x265_log(p, X265_LOG_ERROR, "Unable to allocate thread pool NUMA log buffer\\n");',
    'delete[] pools;',
    'numPools = 0;',
    'return nullptr;',
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
)
FORBIDDEN_SNIPPETS = (
    'ThreadPool *pools = new ThreadPool[numPools];',
    'char *nodesstr = new char[64 * std::strlen(",63") + 1];',
    'm_workers = X265_MALLOC(WorkerThread, numThreads);',
    'm_jpTable = X265_MALLOC(JobProvider*, maxProviders);',
    'return m_workers && m_jpTable;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden threadpool create rollback regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing threadpool create rollback guardrail: {snippet}'))

    pools_alloc_pos = text.find('ThreadPool *pools = new (std::nothrow) ThreadPool[numPools];')
    pools_guard_return_pos = text.find('return nullptr;', pools_alloc_pos if pools_alloc_pos != -1 else 0)
    nodes_alloc_pos = text.find('char *nodesstr = new (std::nothrow) char[64 * std::strlen(",63") + 1];', pools_alloc_pos if pools_alloc_pos != -1 else 0)
    nodes_guard_pos = text.find('if (!nodesstr)', nodes_alloc_pos if nodes_alloc_pos != -1 else 0)
    nodes_delete_pools_pos = text.find('delete[] pools;', nodes_guard_pos if nodes_guard_pos != -1 else 0)
    if -1 in (pools_alloc_pos, pools_guard_return_pos, nodes_alloc_pos, nodes_guard_pos, nodes_delete_pools_pos) or not (
        pools_alloc_pos < nodes_alloc_pos < nodes_guard_pos < nodes_delete_pools_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'ThreadPool::allocThreadPools must use nothrow allocations and roll back pool state before returning nullptr'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check threadpool create rollback guardrails')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('Threadpool create rollback validated')


if __name__ == '__main__':
    main()
