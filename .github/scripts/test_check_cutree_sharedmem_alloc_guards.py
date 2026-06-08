#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_cutree_sharedmem_alloc_guards.py')

# Coverage probes used by the scan for cutree shared-memory allocation guardrails.
NORMALIZED_PROBES = (
    'missing file',
    'missing ',
    'RingMem::init must guard write/read semaphore allocations before using them',
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


def valid_ratecontrol_text():
    return '\n'.join((
        '#include <new>',
        'bool RateControl::initCUTreeSharedMem()',
        '{',
        '    if (!m_cutreeShrMem) {',
        '        m_cutreeShrMem = new (std::nothrow) RingMem;',
        '        if (!m_cutreeShrMem)',
        '        {',
        '            return false;',
        '        }',
        '        if (!m_cutreeShrMem->init(itemSize, itemCnt, shrname))',
        '        {',
        '            delete m_cutreeShrMem;',
        '            m_cutreeShrMem = nullptr;',
        '            return false;',
        '        }',
        '    }',
        '    return true;',
        '}',
    )) + '\n'


def valid_ringmem_text():
    return '\n'.join((
        '#include <new>',
        'm_writeSem = new (std::nothrow) NamedSemaphore;',
        'if (!m_writeSem)',
        '{',
        '    release();',
        '    return false;',
        '}',
        'm_readSem = new (std::nothrow) NamedSemaphore;',
        'if (!m_readSem)',
        '{',
        '    release();',
        '    return false;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {
            'source/encoder/ratecontrol.cpp': valid_ratecontrol_text(),
            'source/common/ringmem.cpp': valid_ringmem_text(),
        })
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {
            'source/encoder/ratecontrol.cpp': valid_ratecontrol_text().replace('m_cutreeShrMem = new (std::nothrow) RingMem;', 'm_cutreeShrMem = new RingMem();', 1),
            'source/common/ringmem.cpp': valid_ringmem_text(),
        })
        expect_fail(run_checker(root), 'forbidden CUTree shared-memory allocation regression: m_cutreeShrMem = new RingMem();')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {
            'source/encoder/ratecontrol.cpp': valid_ratecontrol_text().replace('            delete m_cutreeShrMem;\n            m_cutreeShrMem = nullptr;\n', '', 1),
            'source/common/ringmem.cpp': valid_ringmem_text(),
        })
        expect_fail(run_checker(root), 'RateControl::initCUTreeSharedMem must clear a partially initialized RingMem after init failure')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {
            'source/encoder/ratecontrol.cpp': valid_ratecontrol_text(),
            'source/common/ringmem.cpp': valid_ringmem_text().replace('m_writeSem = new (std::nothrow) NamedSemaphore;', 'm_writeSem = new NamedSemaphore();', 1),
        })
        expect_fail(run_checker(root), 'forbidden RingMem semaphore allocation regression: m_writeSem = new NamedSemaphore();')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {
            'source/encoder/ratecontrol.cpp': valid_ratecontrol_text(),
            'source/common/ringmem.cpp': valid_ringmem_text().replace('m_readSem = new (std::nothrow) NamedSemaphore;', 'm_readSem = new NamedSemaphore();', 1),
        })
        expect_fail(run_checker(root), 'forbidden RingMem semaphore allocation regression: m_readSem = new NamedSemaphore();')

    print('CUTree shared-memory allocation guard tests passed')


if __name__ == '__main__':
    main()
