#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cutree_sharedmem_name_guard.py')


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


def valid_files():
    return {
        'source/common/ringmem.cpp': '\n'.join((
            'bool formatRingMemName(char *buffer, size_t capacity, const char *prefix, const char *name, const char *label)',
            '{',
            '    return true;',
            '}',
            'bool RingMem::init(int32_t itemSize, int32_t itemCnt, const char *name, bool protectRW)',
            '{',
            '    if (!formatRingMemName(nameBuf, sizeof(nameBuf), X265_SHARED_MEM_NAME, name, "shared memory object name"))',
            '        return false;',
            '    m_filepath = strdup(nameBuf);',
            '    if (!m_filepath)',
            '    {',
            '        if (newCreated)',
            '                    unlink(nameBuf);',
            '        return false;',
            '    }',
            '    if (!formatRingMemName(nameBuf, sizeof(nameBuf), X265_SEMAPHORE_RINGMEM_WRITER_NAME, name, "ringmem writer semaphore name"))',
            '        return false;',
            '    if (!formatRingMemName(nameBuf, sizeof(nameBuf), X265_SEMAPHORE_RINGMEM_READER_NAME, name, "ringmem reader semaphore name"))',
            '        return false;',
            '}',
            'void RingMem::release()',
            '{',
            '    if (m_filepath)',
            '    {',
            '        unlink(m_filepath);',
            '        std::free(m_filepath);',
            '    }',
            '}',
        )) + '\n',
        'source/common/threading.h': '\n'.join((
            'bool created = false;',
            'created = true;',
            'if (m_name)',
            '                ret = true;',
            'if (created)',
            '                    sem_unlink(name);',
            'if (m_name)',
            '                sem_unlink(m_name);',
        )) + '\n',
    }


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, valid_files())
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = valid_files()
        files['source/common/ringmem.cpp'] = files['source/common/ringmem.cpp'].replace(
            '    if (!formatRingMemName(nameBuf, sizeof(nameBuf), X265_SHARED_MEM_NAME, name, "shared memory object name"))\n'
            '        return false;\n',
            '    std::snprintf(nameBuf, sizeof(nameBuf) - 1, "%s%s", X265_SHARED_MEM_NAME, name);\n',
            1,
        )
        write_targets(root, files)
        expect_fail(run_checker(root), 'forbidden cutree shared-memory name regression: std::snprintf(nameBuf, sizeof(nameBuf) - 1, "%s%s", X265_SHARED_MEM_NAME, name);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        files = valid_files()
        files['source/common/threading.h'] = files['source/common/threading.h'].replace(
            'if (m_name)\n                sem_unlink(m_name);\n',
            'sem_unlink(m_name);\n            m_sem = nullptr;\n',
            1,
        )
        write_targets(root, files)
        expect_fail(run_checker(root), 'missing cutree shared-memory name guardrail: if (m_name)')

    print('Cutree shared-memory name guard tests passed')


if __name__ == '__main__':
    main()
