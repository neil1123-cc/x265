#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/threadpool.cpp')


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    alloc_text = extract_braced_block(text, 'ThreadPool* ThreadPool::allocThreadPools(x265_param* p, int& numPools, bool isThreadsReserved)')
    cpu_text = extract_braced_block(text, 'int ThreadPool::getCpuCount()')
    failures = []

    if not alloc_text:
        failures.append((TARGET.as_posix(), 0, 'missing ThreadPool::allocThreadPools function'))
        return failures
    if not cpu_text:
        failures.append((TARGET.as_posix(), 0, 'missing ThreadPool::getCpuCount function'))
        return failures

    alloc_required = (
        'GROUP_AFFINITY groupAffinity = {};',
        'if (GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity))',
        'cpusPerNode[i] = popCount(groupAffinity.Mask);',
        'x265_log(p, X265_LOG_WARNING, "Failed to query NUMA node %d processor mask\\n", i);',
    )
    for snippet in alloc_required:
        if snippet not in alloc_text:
            failures.append((TARGET.as_posix(), 0, f'missing threadpool Windows NUMA affinity guardrail: {snippet}'))

    cpu_required = (
        'GROUP_AFFINITY groupAffinity = {};',
        'if (GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity))',
        'cpus += popCount(groupAffinity.Mask);',
        'if (cpus)',
        'SYSTEM_INFO sysinfo;',
        'GetSystemInfo(&sysinfo);',
    )
    for snippet in cpu_required:
        if snippet not in cpu_text:
            failures.append((TARGET.as_posix(), 0, f'missing threadpool Windows NUMA affinity guardrail: {snippet}'))

    alloc_forbidden = (
        'PGROUP_AFFINITY groupAffinityPointer = new GROUP_AFFINITY;',
        'GetNumaNodeProcessorMaskEx((UCHAR)i, groupAffinityPointer);',
        'cpusPerNode[i] = popCount(groupAffinityPointer->Mask);',
    )
    for snippet in alloc_forbidden:
        if snippet in alloc_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden threadpool Windows NUMA affinity regression: {snippet}'))

    cpu_forbidden = (
        'GROUP_AFFINITY groupAffinity;',
        'GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity);\n        cpus += popCount(groupAffinity.Mask);',
    )
    for snippet in cpu_forbidden:
        if snippet in cpu_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden threadpool Windows NUMA affinity regression: {snippet}'))

    alloc_group_pos = alloc_text.find('GROUP_AFFINITY groupAffinity = {};')
    alloc_call_pos = alloc_text.find('if (GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity))', alloc_group_pos if alloc_group_pos != -1 else 0)
    alloc_pop_pos = alloc_text.find('cpusPerNode[i] = popCount(groupAffinity.Mask);', alloc_call_pos if alloc_call_pos != -1 else 0)
    alloc_warn_pos = alloc_text.find('x265_log(p, X265_LOG_WARNING, "Failed to query NUMA node %d processor mask\\n", i);', alloc_pop_pos if alloc_pop_pos != -1 else 0)
    if -1 in (alloc_group_pos, alloc_call_pos, alloc_pop_pos, alloc_warn_pos) or not (
        alloc_group_pos < alloc_call_pos < alloc_pop_pos < alloc_warn_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'ThreadPool::allocThreadPools must zero-initialize affinity masks and guard GetNumaNodeProcessorMaskEx before reading Mask'))

    cpu_group_pos = cpu_text.find('GROUP_AFFINITY groupAffinity = {};')
    cpu_call_pos = cpu_text.find('if (GetNumaNodeProcessorMaskEx((UCHAR)i, &groupAffinity))', cpu_group_pos if cpu_group_pos != -1 else 0)
    cpu_pop_pos = cpu_text.find('cpus += popCount(groupAffinity.Mask);', cpu_call_pos if cpu_call_pos != -1 else 0)
    cpu_guard_pos = cpu_text.find('if (cpus)', cpu_pop_pos if cpu_pop_pos != -1 else 0)
    cpu_return_pos = cpu_text.find('return cpus;', cpu_guard_pos if cpu_guard_pos != -1 else 0)
    cpu_sysinfo_pos = cpu_text.find('SYSTEM_INFO sysinfo;', cpu_return_pos if cpu_return_pos != -1 else 0)
    if -1 in (cpu_group_pos, cpu_call_pos, cpu_pop_pos, cpu_guard_pos, cpu_return_pos, cpu_sysinfo_pos) or not (
        cpu_group_pos < cpu_call_pos < cpu_pop_pos < cpu_guard_pos < cpu_return_pos < cpu_sysinfo_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'ThreadPool::getCpuCount must guard NUMA affinity queries before reading Mask and fall back to GetSystemInfo when enumeration fails'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check threadpool Windows NUMA affinity guards')
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

    print('Threadpool Windows NUMA affinity guards validated')


if __name__ == '__main__':
    main()
