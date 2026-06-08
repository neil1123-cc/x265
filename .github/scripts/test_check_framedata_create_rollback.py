#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_framedata_create_rollback.py')

# Coverage probes used by the scan for FrameData rollback guardrails.
NORMALIZED_PROBES = (
    'forbidden FrameData create rollback regression: ',
    'missing FrameData create rollback guardrail: ',
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
                'source/common/framedata.cpp': '\n'.join((
                    'bool FrameData::create(const x265_param& param, const SPS& sps, int csp)',
                    '{',
                    'm_slice  = new (std::nothrow) Slice;',
                    'if (!m_slice)',
                    '    return false;',
                    'if (!m_slice->m_ctuMV)',
                    '    goto fail;',
                    'm_picCTU = new (std::nothrow) CUData[sps.numCUsInFrame];',
                    'if (!m_picCTU)',
                    '    goto fail;',
                    'isallocated = m_cuMemPool.create(0, param.internalCsp, sps.numCUsInFrame, param);',
                    'CHECKED_MALLOC_ZERO(m_cuStat, RCStatCU, sps.numCUsInFrame + 1);',
                    'CHECKED_MALLOC(m_rowStat, RCStatRow, sps.numCuInHeight);',
                    'reinit(sps);',
                    'return true;',
                    'goto fail;',
                    'fail:',
                    'destroy();',
                    'return false;',
                    '}',
                    'void FrameData::reinit(const SPS& sps)',
                    '{',
                    '}',
                    'void FrameData::destroy()',
                    '{',
                    'delete [] m_picCTU;',
                    'm_picCTU = nullptr;',
                    'if (m_slice)',
                    '{',
                    '    X265_FREE(m_slice->m_ctuMV);',
                    '    delete m_slice;',
                    '    m_slice = nullptr;',
                    '}',
                    'delete m_saoParam;',
                    'm_slice = nullptr;',
                    'm_saoParam = nullptr;',
                    'if (m_param && m_param->bDynamicRefine)',
                    'X265_FREE(m_cuStat);',
                    'm_cuStat = nullptr;',
                    'X265_FREE(m_rowStat);',
                    'm_rowStat = nullptr;',
                    'destroySEAIntegralBuffers();',
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
                'source/common/framedata.cpp': '\n'.join((
                    'm_slice  = new Slice;',
                    'm_picCTU = new CUData[sps.numCUsInFrame];',
                    'else',
                    '        return false;',
                    'X265_FREE(m_slice->m_ctuMV);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden FrameData create rollback regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/framedata.cpp': '\n'.join((
                    'bool FrameData::create(const x265_param& param, const SPS& sps, int csp)',
                    '{',
                    'm_slice  = new (std::nothrow) Slice;',
                    'if (!m_slice)',
                    '    return false;',
                    'if (!m_slice->m_ctuMV)',
                    '    goto fail;',
                    'm_picCTU = new (std::nothrow) CUData[sps.numCUsInFrame];',
                    'if (!m_picCTU)',
                    '    goto fail;',
                    'isallocated = m_cuMemPool.create(0, param.internalCsp, sps.numCUsInFrame, param);',
                    'CHECKED_MALLOC_ZERO(m_cuStat, RCStatCU, sps.numCUsInFrame + 1);',
                    'CHECKED_MALLOC(m_rowStat, RCStatRow, sps.numCuInHeight);',
                    'reinit(sps);',
                    'fail:',
                    'destroy();',
                    'return false;',
                    'return true;',
                    '}',
                    'void FrameData::reinit(const SPS& sps)',
                    '{',
                    '}',
                    'void FrameData::destroy()',
                    '{',
                    'delete [] m_picCTU;',
                    'm_picCTU = nullptr;',
                    'if (m_slice)',
                    '{',
                    '    X265_FREE(m_slice->m_ctuMV);',
                    '    delete m_slice;',
                    '    m_slice = nullptr;',
                    '}',
                    'delete m_saoParam;',
                    'm_saoParam = nullptr;',
                    'if (m_param && m_param->bDynamicRefine)',
                    'X265_FREE(m_cuStat);',
                    'm_cuStat = nullptr;',
                    'X265_FREE(m_rowStat);',
                    'm_rowStat = nullptr;',
                    'destroySEAIntegralBuffers();',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'FrameData::create must stage allocations before the success return and funnel failures through destroy()')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/framedata.cpp': '\n'.join((
                    'bool FrameData::create(const x265_param& param, const SPS& sps, int csp)',
                    '{',
                    'm_slice  = new (std::nothrow) Slice;',
                    'if (!m_slice)',
                    '    return false;',
                    'if (!m_slice->m_ctuMV)',
                    '    goto fail;',
                    'm_picCTU = new (std::nothrow) CUData[sps.numCUsInFrame];',
                    'if (!m_picCTU)',
                    '    goto fail;',
                    'isallocated = m_cuMemPool.create(0, param.internalCsp, sps.numCUsInFrame, param);',
                    'CHECKED_MALLOC_ZERO(m_cuStat, RCStatCU, sps.numCUsInFrame + 1);',
                    'CHECKED_MALLOC(m_rowStat, RCStatRow, sps.numCuInHeight);',
                    'reinit(sps);',
                    'return true;',
                    'fail:',
                    'destroy();',
                    'return false;',
                    '}',
                    'void FrameData::reinit(const SPS& sps)',
                    '{',
                    '}',
                    'void FrameData::destroy()',
                    '{',
                    'X265_FREE(m_cuStat);',
                    'm_cuStat = nullptr;',
                    'delete [] m_picCTU;',
                    'm_picCTU = nullptr;',
                    'if (m_slice)',
                    '{',
                    '    X265_FREE(m_slice->m_ctuMV);',
                    '    delete m_slice;',
                    '    m_slice = nullptr;',
                    '}',
                    'delete m_saoParam;',
                    'm_saoParam = nullptr;',
                    'if (m_param && m_param->bDynamicRefine)',
                    'X265_FREE(m_rowStat);',
                    'm_rowStat = nullptr;',
                    'destroySEAIntegralBuffers();',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'FrameData::destroy must clear top-level frame state before releasing statistics and SEA integral buffers')

    print('FrameData create rollback tests passed')


if __name__ == '__main__':
    main()
