#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lookahead_alloc_guards.py')

# Coverage probes used by the scan for lookahead allocation guardrails.
NORMALIZED_PROBES = (
    'Lookahead constructor/create/destroy must guard histogram allocations, initialize histogram row pointers, and validate worker-buffer allocations before use and cleanup',
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


def valid_text(include_cb_row=True):
    cb_row_lines = (
        '            for (uint32_t w = 1; w < NUMBER_OF_SEGMENTS_IN_WIDTH; w++)',
        '                m_accHistDiffRunningAvgCb[w] = m_accHistDiffRunningAvgCb[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;',
    ) if include_cb_row else ()

    return '\n'.join((
        '#include <new>',
        'Lookahead::Lookahead(x265_param *param, ThreadPool* pool)',
        '{',
        '    m_metld = nullptr;',
        '    m_accHistDiffRunningAvgCb = nullptr;',
        '    m_accHistDiffRunningAvgCr = nullptr;',
        '    m_accHistDiffRunningAvg = nullptr;',
        '    m_accHistDiffRunningAvgCb = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);',
        '    if (m_accHistDiffRunningAvgCb)',
        '    {',
        '        m_accHistDiffRunningAvgCb[0] = X265_MALLOC(uint32_t, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
        '        if (m_accHistDiffRunningAvgCb[0])',
        '        {',
        '            std::fill_n(m_accHistDiffRunningAvgCb[0], NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT, uint32_t(0));',
        *cb_row_lines,
        '        }',
        '    }',
        '    m_accHistDiffRunningAvgCr = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);',
        '    if (m_accHistDiffRunningAvgCr)',
        '    {',
        '        m_accHistDiffRunningAvgCr[0] = X265_MALLOC(uint32_t, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
        '        if (m_accHistDiffRunningAvgCr[0])',
        '        {',
        '            std::fill_n(m_accHistDiffRunningAvgCr[0], NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT, uint32_t(0));',
        '            for (uint32_t w = 1; w < NUMBER_OF_SEGMENTS_IN_WIDTH; w++)',
        '                m_accHistDiffRunningAvgCr[w] = m_accHistDiffRunningAvgCr[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;',
        '        }',
        '    }',
        '    m_accHistDiffRunningAvg = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);',
        '    if (m_accHistDiffRunningAvg)',
        '    {',
        '        m_accHistDiffRunningAvg[0] = X265_MALLOC(uint32_t, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
        '        if (m_accHistDiffRunningAvg[0])',
        '        {',
        '            std::fill_n(m_accHistDiffRunningAvg[0], NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT, uint32_t(0));',
        '            for (uint32_t w = 1; w < NUMBER_OF_SEGMENTS_IN_WIDTH; w++)',
        '                m_accHistDiffRunningAvg[w] = m_accHistDiffRunningAvg[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;',
        '        }',
        '    }',
        '}',
        'bool Lookahead::create()',
        '{',
        '    if (!m_accHistDiffRunningAvgCb || !m_accHistDiffRunningAvgCb[0] ||',
        '        !m_accHistDiffRunningAvgCr || !m_accHistDiffRunningAvgCr[0] ||',
        '        !m_accHistDiffRunningAvg || !m_accHistDiffRunningAvg[0])',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead histogram buffers\\n");',
        '        return false;',
        '    }',
        '    int numTLD = 1;',
        '    LookaheadTLD* tld = new (std::nothrow) LookaheadTLD[numTLD];',
        '    int* scratch = nullptr;',
        '    MotionEstimatorTLD* metld = nullptr;',
        '    OrigPicBuffer* origPicBuf = nullptr;',
        '    if (!tld)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead thread-local data\\n");',
        '        return false;',
        '    }',
        '    scratch = X265_MALLOC(int, tld[0].widthInCU);',
        '    if (!scratch)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead scratch buffer\\n");',
        '        goto fail;',
        '    }',
        '    metld = new (std::nothrow) MotionEstimatorTLD[numTLD];',
        '    if (!metld)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead motion-estimator buffers\\n");',
        '        goto fail;',
        '    }',
        '    origPicBuf = new (std::nothrow) OrigPicBuffer();',
        '    if (!origPicBuf)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate lookahead original-picture buffer\\n");',
        '        goto fail;',
        '    }',
        '    m_tld = tld;',
        '    m_scratch = scratch;',
        '    m_metld = metld;',
        '    m_origPicBuf = origPicBuf;',
        '    return true;',
        'fail:',
        '    delete origPicBuf;',
        '    delete[] metld;',
        '    X265_FREE(scratch);',
        '    delete[] tld;',
        '    return false;',
        '}',
        'void Lookahead::destroy()',
        '{',
        '    if (m_accHistDiffRunningAvgCb)',
        '        X265_FREE(m_accHistDiffRunningAvgCb[0]);',
        '    if (m_accHistDiffRunningAvgCr)',
        '        X265_FREE(m_accHistDiffRunningAvgCr[0]);',
        '    if (m_accHistDiffRunningAvg)',
        '        X265_FREE(m_accHistDiffRunningAvg[0]);',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/slicetype.cpp': valid_text(),
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/slicetype.cpp': '\n'.join((
                    'Lookahead::Lookahead(x265_param *param, ThreadPool* pool)',
                    '{',
                    '    m_accHistDiffRunningAvgCb = X265_MALLOC(uint32_t*, NUMBER_OF_SEGMENTS_IN_WIDTH);',
                    '    m_accHistDiffRunningAvgCb[0] = X265_MALLOC(uint32_t, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
                    '}',
                    'bool Lookahead::create()',
                    '{',
                    '    return true;',
                    '}',
                    'void Lookahead::destroy()',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing lookahead allocation guardrail: if (!m_accHistDiffRunningAvgCb || !m_accHistDiffRunningAvgCb[0] ||')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/slicetype.cpp': valid_text(include_cb_row=False),
            },
        )
        expect_fail(run_checker(root), 'missing lookahead allocation guardrail: m_accHistDiffRunningAvgCb[w] = m_accHistDiffRunningAvgCb[0] + w * NUMBER_OF_SEGMENTS_IN_HEIGHT;')

    print('Lookahead allocation guard tests passed')


if __name__ == '__main__':
    main()
