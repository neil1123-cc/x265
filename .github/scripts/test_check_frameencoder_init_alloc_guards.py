#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_frameencoder_init_alloc_guards.py')

# Coverage probes used by the scan for FrameEncoder init allocation guardrails.
NORMALIZED_PROBES = (
    'FrameEncoder::init must guard row, slice, wavefront, filter, HRD, and return-buffer allocations before use',
    'FrameFilter::init must stage SSIM and parallel-filter allocations and roll back SSIM state if filter allocation fails',
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


def valid_frameencoder_text():
    return '\n'.join((
        '#include <new>',
        'FrameEncoder::FrameEncoder()',
        '{',
        '    m_sliceBaseRow = nullptr;',
        '    m_sliceMaxBlockRow = nullptr;',
        '    m_retFrameBuffer = nullptr;',
        '}',
        'void FrameEncoder::destroy()',
        '{',
        '    if (m_tld)',
        '    {',
        '    }',
        '    if (m_param && (m_param->bEmitHRDSEI || m_param->interlaceMode != 0))',
        '    {',
        '    }',
        '}',
        'bool FrameEncoder::init(Encoder *top, int numRows, int numCols)',
        '{',
        '    m_rows = new (std::nothrow) CTURow[m_numRows];',
        '    if (!m_rows)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder row state\\n");',
        '        return false;',
        '    }',
        '    m_sliceBaseRow = X265_MALLOC(uint32_t, m_param->maxSlices + 1);',
        '    m_bAllRowsStop = new (std::nothrow) std::atomic<bool>[m_param->maxSlices];',
        '    m_vbvResetTriggerRow = new (std::nothrow) std::atomic<int>[m_param->maxSlices];',
        '    if (!m_sliceBaseRow || !m_bAllRowsStop || !m_vbvResetTriggerRow)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder slice state\\n");',
        '        return false;',
        '    }',
        '    m_sliceMaxBlockRow = X265_MALLOC(uint32_t, m_param->maxSlices + 1);',
        '    if (!m_sliceMaxBlockRow)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder block-row state\\n");',
        '        return false;',
        '    }',
        '    if (!WaveFront::init(m_numRows * 2))',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "unable to initialize wavefront queue\\n");',
        '        return false;',
        '    }',
        '    if (!m_frameFilter.init(top, this, numRows, numCols))',
        '    {',
        '        return false;',
        '    }',
        '    m_rce.picTimingSEI = new (std::nothrow) SEIPictureTiming;',
        '    m_rce.hrdTiming = new (std::nothrow) HRDTiming;',
        '    if (!m_rce.picTimingSEI || !m_rce.hrdTiming)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder HRD timing state\\n");',
        '        return false;',
        '    }',
        '    m_retFrameBuffer = X265_MALLOC(Frame*, m_param->numLayers);',
        '    if (!m_retFrameBuffer)',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder return buffer\\n");',
        '        return false;',
        '    }',
        '}',
    )) + '\n'


def valid_framefilter_text():
    return '\n'.join((
        '#include <new>',
        'bool FrameFilter::init(Encoder *top, FrameEncoder *frame, int numRows, uint32_t numCols)',
        '{',
        '    void* stagedSsimBuf = nullptr;',
        '    ParallelFilter* stagedParallelFilter = nullptr;',
        '    if (m_param->bEnableSsim)',
        '    {',
        '        stagedSsimBuf = X265_MALLOC(int, 8 * (m_param->sourceWidth / 4 + 3));',
        '        if (!stagedSsimBuf)',
        '        {',
        '            x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder SSIM state\\n");',
        '            return false;',
        '        }',
        '    }',
        '    stagedParallelFilter = new (std::nothrow) ParallelFilter[numRows];',
        '    if (!stagedParallelFilter)',
        '    {',
        '        X265_FREE(stagedSsimBuf);',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder parallel filter state\\n");',
        '        return false;',
        '    }',
        '    m_ssimBuf = stagedSsimBuf;',
        '    m_parallelFilter = stagedParallelFilter;',
        '    return true;',
        '}',
    )) + '\n'


def valid_encoder_text():
    return '\n'.join((
        'void Encoder::create()',
        '{',
        'int numRows = (m_param->sourceHeight + m_param->maxCUSize - 1) / m_param->maxCUSize;',
        'int numCols = (m_param->sourceWidth  + m_param->maxCUSize - 1) / m_param->maxCUSize;',
        'for (int i = 0; i < m_param->frameNumThreads; i++)',
        '{',
        '    if (!m_frameEncoder[i]->init(this, numRows, numCols))',
        '    {',
        '        x265_log(m_param, X265_LOG_ERROR, "Unable to initialize frame encoder, aborting\\n");',
        '        m_aborted = true;',
        '        break;',
        '    }',
        '}',
        'if (m_aborted)',
        '    return;',
        'for (int i = 0; i < m_param->frameNumThreads; i++)',
        '{',
        '    if (!m_frameEncoder[i]->start())',
        '    {',
        '    }',
        '}',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_frameencoder_text(),
                'source/encoder/framefilter.cpp': valid_framefilter_text(),
                'source/encoder/encoder.cpp': valid_encoder_text(),
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_frameencoder_text().replace(
                    'm_rows = new (std::nothrow) CTURow[m_numRows];\n', 'm_rows = new CTURow[m_numRows];\n', 1
                ),
                'source/encoder/framefilter.cpp': valid_framefilter_text(),
                'source/encoder/encoder.cpp': valid_encoder_text(),
            },
        )
        expect_fail(run_checker(root), 'missing frame encoder init alloc guardrail: m_rows = new (std::nothrow) CTURow[m_numRows];')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_frameencoder_text().replace(
                    '    if (!WaveFront::init(m_numRows * 2))\n'
                    '    {\n'
                    '        x265_log(m_param, X265_LOG_ERROR, "unable to initialize wavefront queue\\n");\n'
                    '        return false;\n'
                    '    }\n',
                    '',
                    1,
                ),
                'source/encoder/framefilter.cpp': valid_framefilter_text().replace(
                    '        X265_FREE(stagedSsimBuf);\n', '', 1
                ),
                'source/encoder/encoder.cpp': valid_encoder_text().replace('if (m_aborted)\n    return;\n', '', 1),
            },
        )
        expect_fail(run_checker(root), 'missing frame encoder init alloc guardrail: if (!WaveFront::init(m_numRows * 2))')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_frameencoder_text(),
                'source/encoder/framefilter.cpp': valid_framefilter_text(),
                'source/encoder/encoder.cpp': '\n'.join((
                    'void Encoder::create()',
                    '{',
                    'if (m_aborted)',
                    '    return;',
                    valid_encoder_text().strip()[len('void Encoder::create()\n{\n'):],
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_frameencoder_text(),
                'source/encoder/framefilter.cpp': valid_framefilter_text(),
                'source/encoder/encoder.cpp': '\n'.join((
                    'void Encoder::create()',
                    '{',
                    'if (m_aborted)',
                    '    return;',
                    valid_encoder_text().strip()[len('void Encoder::create()\n{\n'):].replace('if (m_aborted)\n    return;\n', '', 1),
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Encoder::create must stop launching frame encoder threads after FrameEncoder::init fails')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/frameencoder.cpp': valid_frameencoder_text(),
                'source/encoder/framefilter.cpp': valid_framefilter_text().replace(
                    'bool FrameFilter::init(Encoder *top, FrameEncoder *frame, int numRows, uint32_t numCols)',
                    'void FrameFilter::init(Encoder *top, FrameEncoder *frame, int numRows, uint32_t numCols)',
                    1,
                ),
                'source/encoder/encoder.cpp': valid_encoder_text(),
            },
        )
        expect_fail(run_checker(root), 'missing frame encoder init alloc guardrail: bool FrameFilter::init(Encoder *top, FrameEncoder *frame, int numRows, uint32_t numCols)')

    print('Frame encoder init allocation guard tests passed')


if __name__ == '__main__':
    main()
