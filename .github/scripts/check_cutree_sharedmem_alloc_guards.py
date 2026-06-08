#!/usr/bin/env python3
import argparse
from pathlib import Path


RATECONTROL_TARGET = Path('source/encoder/ratecontrol.cpp')
RINGMEM_TARGET = Path('source/common/ringmem.cpp')


def require_snippets(text, target, snippets, label):
    failures = []
    for snippet in snippets:
        if snippet not in text:
            failures.append((target.as_posix(), 0, f'missing {label}: {snippet}'))
    return failures


def forbid_snippets(text, target, snippets, label):
    failures = []
    for snippet in snippets:
        if snippet in text:
            failures.append((target.as_posix(), 0, f'forbidden {label}: {snippet}'))
    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    ratecontrol_path = repo_root / RATECONTROL_TARGET
    if not ratecontrol_path.is_file():
        failures.append((RATECONTROL_TARGET.as_posix(), 0, 'missing file'))
    else:
        text = ratecontrol_path.read_text(encoding='utf-8', errors='ignore')
        failures.extend(require_snippets(
            text,
            RATECONTROL_TARGET,
            (
                '#include <new>',
                'm_cutreeShrMem = new (std::nothrow) RingMem;',
                'if (!m_cutreeShrMem)',
                'delete m_cutreeShrMem;',
                'm_cutreeShrMem = nullptr;',
            ),
            'CUTree shared-memory allocation guardrail',
        ))
        failures.extend(forbid_snippets(
            text,
            RATECONTROL_TARGET,
            ('m_cutreeShrMem = new RingMem();',),
            'CUTree shared-memory allocation regression',
        ))

        alloc_pos = text.find('m_cutreeShrMem = new (std::nothrow) RingMem;')
        guard_pos = text.find('if (!m_cutreeShrMem)', alloc_pos if alloc_pos != -1 else 0)
        init_pos = text.find('if (!m_cutreeShrMem->init(itemSize, itemCnt, shrname))', guard_pos if guard_pos != -1 else 0)
        delete_pos = text.find('delete m_cutreeShrMem;', init_pos if init_pos != -1 else 0)
        clear_pos = text.find('m_cutreeShrMem = nullptr;', delete_pos if delete_pos != -1 else 0)
        if -1 in (alloc_pos, guard_pos, init_pos, delete_pos, clear_pos) or not (alloc_pos < guard_pos < init_pos < delete_pos < clear_pos):
            failures.append((RATECONTROL_TARGET.as_posix(), 0, 'RateControl::initCUTreeSharedMem must clear a partially initialized RingMem after init failure'))

    ringmem_path = repo_root / RINGMEM_TARGET
    if not ringmem_path.is_file():
        failures.append((RINGMEM_TARGET.as_posix(), 0, 'missing file'))
    else:
        text = ringmem_path.read_text(encoding='utf-8', errors='ignore')
        failures.extend(require_snippets(
            text,
            RINGMEM_TARGET,
            (
                '#include <new>',
                'm_writeSem = new (std::nothrow) NamedSemaphore;',
                'if (!m_writeSem)',
                'm_readSem = new (std::nothrow) NamedSemaphore;',
                'if (!m_readSem)',
                'release();',
            ),
            'RingMem semaphore allocation guardrail',
        ))
        failures.extend(forbid_snippets(
            text,
            RINGMEM_TARGET,
            (
                'm_writeSem = new NamedSemaphore();',
                'm_readSem = new NamedSemaphore();',
            ),
            'RingMem semaphore allocation regression',
        ))

        write_alloc_pos = text.find('m_writeSem = new (std::nothrow) NamedSemaphore;')
        write_guard_pos = text.find('if (!m_writeSem)', write_alloc_pos if write_alloc_pos != -1 else 0)
        read_alloc_pos = text.find('m_readSem = new (std::nothrow) NamedSemaphore;', write_guard_pos if write_guard_pos != -1 else 0)
        read_guard_pos = text.find('if (!m_readSem)', read_alloc_pos if read_alloc_pos != -1 else 0)
        if -1 in (write_alloc_pos, write_guard_pos, read_alloc_pos, read_guard_pos) or not (
            write_alloc_pos < write_guard_pos < read_alloc_pos < read_guard_pos
        ):
            failures.append((RINGMEM_TARGET.as_posix(), 0, 'RingMem::init must guard write/read semaphore allocations before using them'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CUTree shared-memory allocation guards')
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

    print('CUTree shared-memory allocation guards validated')


if __name__ == '__main__':
    main()
