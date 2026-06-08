#!/usr/bin/env python3
import argparse
from pathlib import Path


RINGMEM_CPP = Path('source/common/ringmem.cpp')
THREADING_H = Path('source/common/threading.h')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    ringmem_path = repo_root / RINGMEM_CPP
    threading_path = repo_root / THREADING_H
    if not ringmem_path.is_file():
        return [(RINGMEM_CPP.as_posix(), 0, 'missing file')]
    if not threading_path.is_file():
        return [(THREADING_H.as_posix(), 0, 'missing file')]

    ringmem = ringmem_path.read_text(encoding='utf-8', errors='ignore')
    threading = threading_path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    ringmem_required = (
        'bool formatRingMemName(char *buffer, size_t capacity, const char *prefix, const char *name, const char *label)',
        'if (!formatRingMemName(nameBuf, sizeof(nameBuf), X265_SHARED_MEM_NAME, name, "shared memory object name"))',
        'm_filepath = strdup(nameBuf);',
        'if (!m_filepath)',
        'if (newCreated)\n                    unlink(nameBuf);',
        'if (!formatRingMemName(nameBuf, sizeof(nameBuf), X265_SEMAPHORE_RINGMEM_WRITER_NAME, name, "ringmem writer semaphore name"))',
        'if (!formatRingMemName(nameBuf, sizeof(nameBuf), X265_SEMAPHORE_RINGMEM_READER_NAME, name, "ringmem reader semaphore name"))',
        'if (m_filepath)',
        'unlink(m_filepath);',
    )
    for snippet in ringmem_required:
        if snippet not in ringmem:
            failures.append((RINGMEM_CPP.as_posix(), 0, f'missing cutree shared-memory name guardrail: {snippet}'))

    ringmem_forbidden = (
        'std::snprintf(nameBuf, sizeof(nameBuf) - 1, "%s%s", X265_SHARED_MEM_NAME, name);',
        'std::snprintf(nameBuf, sizeof(nameBuf) - 1, "%s%s", X265_SEMAPHORE_RINGMEM_WRITER_NAME, name);',
        'std::snprintf(nameBuf, sizeof(nameBuf) - 1, "%s%s", X265_SEMAPHORE_RINGMEM_READER_NAME, name);',
        'unlink(m_filepath);\n                std::free(m_filepath);',
    )
    for snippet in ringmem_forbidden:
        if snippet in ringmem:
            failures.append((RINGMEM_CPP.as_posix(), 0, f'forbidden cutree shared-memory name regression: {snippet}'))

    threading_required = (
        'bool created = false;',
        'created = true;',
        'if (m_name)\n                ret = true;',
        'if (created)\n                    sem_unlink(name);',
        'if (m_name)\n                sem_unlink(m_name);',
    )
    for snippet in threading_required:
        if snippet not in threading:
            failures.append((THREADING_H.as_posix(), 0, f'missing cutree shared-memory name guardrail: {snippet}'))

    threading_forbidden = (
        'm_name = strdup(name);\n            ret = true;',
        'm_name = strdup(name);\n                    ret = true;',
        '#else //__APPLE__\n            sem_close(m_sem);\n            sem_unlink(m_name);\n            m_sem = nullptr;',
    )
    for snippet in threading_forbidden:
        if snippet in threading:
            failures.append((THREADING_H.as_posix(), 0, f'forbidden cutree shared-memory name regression: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check cutree shared-memory name guards')
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

    print('Cutree shared-memory name guards validated')


if __name__ == '__main__':
    main()
