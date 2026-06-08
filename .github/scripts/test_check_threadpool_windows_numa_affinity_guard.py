#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_threadpool_windows_numa_affinity_guard.py')

# Coverage probes used by the scan for Windows NUMA affinity guardrails.
NORMALIZED_PROBES = (
    'missing ThreadPool::allocThreadPools function',
    'missing ThreadPool::getCpuCount function',
    'ThreadPool::allocThreadPools must zero-initialize affinity masks and guard GetNumaNodeProcessorMaskEx before reading Mask',
    'ThreadPool::getCpuCount must guard NUMA affinity queries before reading Mask and fall back to GetSystemInfo when enumeration fails',
    'missing threadpool Windows NUMA affinity guardrail: ',
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


def valid_text():
    return '\n'.join((
        'ThreadPool* ThreadPool::allocThreadPools(x265_param* p, int& numPools, bool isThreadsReserved)',
        '{',
        '    for (int i = 0; i < numNumaNodes; i++)',
        '    {',
        '        GROUP_AFFINITY groupAffinity = {};',
        '        if (GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity))',
        '            cpusPerNode[i] = popCount(groupAffinity.Mask);',
        '        else',
        '            x265_log(p, X265_LOG_WARNING, "Failed to query NUMA node %d processor mask\\n", i);',
        '    }',
        '}',
        'int ThreadPool::getCpuCount()',
        '{',
        '    int cpus = 0;',
        '    for (int i = 0; i < numNumaNodes; i++)',
        '    {',
        '        GROUP_AFFINITY groupAffinity = {};',
        '        if (GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity))',
        '            cpus += popCount(groupAffinity.Mask);',
        '    }',
        '    if (cpus)',
        '        return cpus;',
        '    SYSTEM_INFO sysinfo;',
        '    GetSystemInfo(&sysinfo);',
        '    return sysinfo.dwNumberOfProcessors;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/threadpool.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/threadpool.cpp': valid_text().replace(
                    '        GROUP_AFFINITY groupAffinity = {};\n'
                    '        if (GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity))\n'
                    '            cpusPerNode[i] = popCount(groupAffinity.Mask);\n'
                    '        else\n'
                    '            x265_log(p, X265_LOG_WARNING, "Failed to query NUMA node %d processor mask\\n", i);\n',
                    '        PGROUP_AFFINITY groupAffinityPointer = new GROUP_AFFINITY;\n'
                    '        GetNumaNodeProcessorMaskEx((UCHAR)i, groupAffinityPointer);\n'
                    '        cpusPerNode[i] = popCount(groupAffinityPointer->Mask);\n',
                    1,
                ),
            },
        )
        expect_fail(
            run_checker(root),
            'forbidden threadpool Windows NUMA affinity regression: PGROUP_AFFINITY groupAffinityPointer = new GROUP_AFFINITY;',
        )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/threadpool.cpp': valid_text().replace(
                    '        GROUP_AFFINITY groupAffinity = {};\n'
                    '        if (GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity))\n'
                    '            cpus += popCount(groupAffinity.Mask);\n',
                    '        GROUP_AFFINITY groupAffinity;\n'
                    '        GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity);\n'
                    '        cpus += popCount(groupAffinity.Mask);\n',
                    1,
                ),
            },
        )
        expect_fail(
            run_checker(root),
            'forbidden threadpool Windows NUMA affinity regression: GROUP_AFFINITY groupAffinity;',
        )

    print('Threadpool Windows NUMA affinity guard tests passed')


if __name__ == '__main__':
    main()
