#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/framedata.cpp')
REQUIRED_SNIPPETS = (
    'm_slice  = new (std::nothrow) Slice;',
    'if (!m_slice)',
    'if (!m_slice->m_ctuMV)',
    'm_picCTU = new (std::nothrow) CUData[sps.numCUsInFrame];',
    'if (!m_picCTU)',
    'isallocated = m_cuMemPool.create(0, param.internalCsp, sps.numCUsInFrame, param);',
    'CHECKED_MALLOC_ZERO(m_cuStat, RCStatCU, sps.numCUsInFrame + 1);',
    'CHECKED_MALLOC(m_rowStat, RCStatRow, sps.numCuInHeight);',
    'reinit(sps);',
    'return true;',
    'goto fail;',
    'fail:',
    'destroy();',
    'return false;',
    'delete [] m_picCTU;',
    'm_picCTU = nullptr;',
    'X265_FREE(m_slice->m_ctuMV);',
    'delete m_slice;',
    'if (m_slice)',
    'm_slice = nullptr;',
    'delete m_saoParam;',
    'm_saoParam = nullptr;',
    'if (m_param && m_param->bDynamicRefine)',
    'X265_FREE(m_cuStat);',
    'm_cuStat = nullptr;',
    'X265_FREE(m_rowStat);',
    'm_rowStat = nullptr;',
    'destroySEAIntegralBuffers();',
)
FORBIDDEN_SNIPPETS = (
    'm_slice  = new Slice;',
    'm_picCTU = new CUData[sps.numCUsInFrame];',
    'else\n        return false;',
)
CREATE_REGION_START = 'bool FrameData::create(const x265_param& param, const SPS& sps, int csp)'
CREATE_REGION_END = 'void FrameData::reinit(const SPS& sps)'
DESTROY_REGION_START = 'void FrameData::destroy()'
DESTROY_REGION_END = '}'


def get_region(text, start_marker, end_marker, include_end=False):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    if include_end:
        end += len(end_marker)
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    create_region = get_region(text, CREATE_REGION_START, CREATE_REGION_END)
    destroy_region = get_region(text, DESTROY_REGION_START, 'destroySEAIntegralBuffers();', include_end=True)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden FrameData create rollback regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing FrameData create rollback guardrail: {snippet}'))
    if all(snippet in text for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            create_region,
            (
                'm_slice  = new (std::nothrow) Slice;',
                'if (!m_slice)',
                'return false;',
                'if (!m_slice->m_ctuMV)',
                'goto fail;',
                'm_picCTU = new (std::nothrow) CUData[sps.numCUsInFrame];',
                'if (!m_picCTU)',
                'goto fail;',
                'isallocated = m_cuMemPool.create(0, param.internalCsp, sps.numCUsInFrame, param);',
                'CHECKED_MALLOC_ZERO(m_cuStat, RCStatCU, sps.numCUsInFrame + 1);',
                'CHECKED_MALLOC(m_rowStat, RCStatRow, sps.numCuInHeight);',
                'reinit(sps);',
                'return true;',
                'fail:',
                'destroy();',
                'return false;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'FrameData::create must stage allocations before the success return and funnel failures through destroy()'))
        if not has_in_order(
            destroy_region,
            (
                'delete [] m_picCTU;',
                'm_picCTU = nullptr;',
                'if (m_slice)',
                'X265_FREE(m_slice->m_ctuMV);',
                'delete m_slice;',
                'm_slice = nullptr;',
                'delete m_saoParam;',
                'm_saoParam = nullptr;',
                'if (m_param && m_param->bDynamicRefine)',
                'X265_FREE(m_cuStat);',
                'm_cuStat = nullptr;',
                'X265_FREE(m_rowStat);',
                'm_rowStat = nullptr;',
                'destroySEAIntegralBuffers();',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'FrameData::destroy must clear top-level frame state before releasing statistics and SEA integral buffers'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check FrameData create rollback guardrails')
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

    print('FrameData create rollback validated')


if __name__ == '__main__':
    main()
