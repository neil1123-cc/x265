#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


FRAMEENCODER_TARGET = Path('source/encoder/frameencoder.cpp')
FRAMEFILTER_TARGET = Path('source/encoder/framefilter.cpp')
ENCODER_TARGET = Path('source/encoder/encoder.cpp')

FRAMEENCODER_SNIPPETS = (
    '#include <new>',
    'm_sliceBaseRow = nullptr;',
    'm_sliceMaxBlockRow = nullptr;',
    'm_retFrameBuffer = nullptr;',
    'if (m_tld)',
    'if (m_param && (m_param->bEmitHRDSEI || m_param->interlaceMode != 0))',
    'm_rows = new (std::nothrow) CTURow[m_numRows];',
    'if (!m_rows)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder row state\\n");',
    'm_bAllRowsStop = new (std::nothrow) std::atomic<bool>[m_param->maxSlices];',
    'm_vbvResetTriggerRow = new (std::nothrow) std::atomic<int>[m_param->maxSlices];',
    'if (!m_sliceBaseRow || !m_bAllRowsStop || !m_vbvResetTriggerRow)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder slice state\\n");',
    'if (!m_sliceMaxBlockRow)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder block-row state\\n");',
    'if (!WaveFront::init(m_numRows * 2))',
    'x265_log(m_param, X265_LOG_ERROR, "unable to initialize wavefront queue\\n");',
    'if (!m_frameFilter.init(top, this, numRows, numCols))',
    'm_rce.picTimingSEI = new (std::nothrow) SEIPictureTiming;',
    'm_rce.hrdTiming = new (std::nothrow) HRDTiming;',
    'if (!m_rce.picTimingSEI || !m_rce.hrdTiming)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder HRD timing state\\n");',
    'if (!m_retFrameBuffer)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder return buffer\\n");',
)

FRAMEFILTER_SNIPPETS = (
    '#include <new>',
    'bool FrameFilter::init(Encoder *top, FrameEncoder *frame, int numRows, uint32_t numCols)',
    'void* stagedSsimBuf = nullptr;',
    'ParallelFilter* stagedParallelFilter = nullptr;',
    'if (m_param->bEnableSsim)',
    'stagedSsimBuf = X265_MALLOC(int, 8 * (m_param->sourceWidth / 4 + 3));',
    'if (!stagedSsimBuf)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder SSIM state\\n");',
    'stagedParallelFilter = new (std::nothrow) ParallelFilter[numRows];',
    'if (!stagedParallelFilter)',
    'X265_FREE(stagedSsimBuf);',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate frame encoder parallel filter state\\n");',
    'm_ssimBuf = stagedSsimBuf;',
    'm_parallelFilter = stagedParallelFilter;',
    'return true;',
)

ENCODER_SNIPPETS = (
    'if (!m_frameEncoder[i]->init(this, numRows, numCols))',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to initialize frame encoder, aborting\\n");',
    'm_aborted = true;',
    'break;',
    'if (m_aborted)',
    'return;',
)

ENCODER_CREATE_SEQUENCE = re.compile(
    r'void\s+Encoder::create\(\)\s*\{'
    r'.*?int\s+numRows\s*=\s*\(m_param->sourceHeight\s*\+\s*m_param->maxCUSize\s*-\s*1\)\s*/\s*m_param->maxCUSize;'
    r'\s*int\s+numCols\s*=\s*\(m_param->sourceWidth\s*\+\s*m_param->maxCUSize\s*-\s*1\)\s*/\s*m_param->maxCUSize;'
    r'\s*for\s*\(\s*int\s+i\s*=\s*0;\s*i\s*<\s*m_param->frameNumThreads;\s*i\+\+\s*\)\s*\{'
    r'\s*if\s*\(\s*!m_frameEncoder\[i\]->init\(this,\s*numRows,\s*numCols\)\s*\)\s*\{'
    r'\s*x265_log\(m_param,\s*X265_LOG_ERROR,\s*"Unable to initialize frame encoder, aborting\\n"\s*\);'
    r'\s*m_aborted\s*=\s*true;'
    r'\s*break;'
    r'\s*\}'
    r'\s*\}'
    r'\s*if\s*\(\s*m_aborted\s*\)\s*'
    r'return;'
    r'\s*for\s*\(\s*int\s+i\s*=\s*0;\s*i\s*<\s*m_param->frameNumThreads;\s*i\+\+\s*\)\s*\{'
    r'\s*if\s*\(\s*!m_frameEncoder\[i\]->start\(\)\s*\)',
    re.S,
)


def load_text(repo_root, relative):
    path = repo_root / relative
    if not path.is_file():
        return None, [(relative.as_posix(), 0, 'missing file')]
    return path.read_text(encoding='utf-8', errors='ignore'), []


def require_snippets(text, relative, snippets):
    failures = []
    for snippet in snippets:
        if snippet not in text:
            failures.append((relative.as_posix(), 0, f'missing frame encoder init alloc guardrail: {snippet}'))
    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    frameencoder_text, errs = load_text(repo_root, FRAMEENCODER_TARGET)
    failures.extend(errs)
    framefilter_text, errs = load_text(repo_root, FRAMEFILTER_TARGET)
    failures.extend(errs)
    encoder_text, errs = load_text(repo_root, ENCODER_TARGET)
    failures.extend(errs)
    if failures:
        return failures

    failures.extend(require_snippets(frameencoder_text, FRAMEENCODER_TARGET, FRAMEENCODER_SNIPPETS))
    failures.extend(require_snippets(framefilter_text, FRAMEFILTER_TARGET, FRAMEFILTER_SNIPPETS))
    failures.extend(require_snippets(encoder_text, ENCODER_TARGET, ENCODER_SNIPPETS))

    init_pos = frameencoder_text.find('bool FrameEncoder::init(Encoder *top, int numRows, int numCols)')
    rows_alloc_pos = frameencoder_text.find('m_rows = new (std::nothrow) CTURow[m_numRows];', init_pos if init_pos != -1 else 0)
    rows_guard_pos = frameencoder_text.find('if (!m_rows)', rows_alloc_pos if rows_alloc_pos != -1 else 0)
    slice_alloc_pos = frameencoder_text.find('m_sliceBaseRow = X265_MALLOC(uint32_t, m_param->maxSlices + 1);', rows_guard_pos if rows_guard_pos != -1 else 0)
    slice_guard_pos = frameencoder_text.find('if (!m_sliceBaseRow || !m_bAllRowsStop || !m_vbvResetTriggerRow)', slice_alloc_pos if slice_alloc_pos != -1 else 0)
    block_alloc_pos = frameencoder_text.find('m_sliceMaxBlockRow = X265_MALLOC(uint32_t, m_param->maxSlices + 1);', slice_guard_pos if slice_guard_pos != -1 else 0)
    block_guard_pos = frameencoder_text.find('if (!m_sliceMaxBlockRow)', block_alloc_pos if block_alloc_pos != -1 else 0)
    wavefront_guard_pos = frameencoder_text.find('if (!WaveFront::init(m_numRows * 2))', block_guard_pos if block_guard_pos != -1 else 0)
    filter_guard_pos = frameencoder_text.find('if (!m_frameFilter.init(top, this, numRows, numCols))', wavefront_guard_pos if wavefront_guard_pos != -1 else 0)
    hrd_alloc_pos = frameencoder_text.find('m_rce.picTimingSEI = new (std::nothrow) SEIPictureTiming;', filter_guard_pos if filter_guard_pos != -1 else 0)
    hrd_guard_pos = frameencoder_text.find('if (!m_rce.picTimingSEI || !m_rce.hrdTiming)', hrd_alloc_pos if hrd_alloc_pos != -1 else 0)
    ret_alloc_pos = frameencoder_text.find('m_retFrameBuffer = X265_MALLOC(Frame*, m_param->numLayers);', hrd_guard_pos if hrd_guard_pos != -1 else 0)
    ret_guard_pos = frameencoder_text.find('if (!m_retFrameBuffer)', ret_alloc_pos if ret_alloc_pos != -1 else 0)
    if -1 in (init_pos, rows_alloc_pos, rows_guard_pos, slice_alloc_pos, slice_guard_pos, block_alloc_pos, block_guard_pos, wavefront_guard_pos, filter_guard_pos, hrd_alloc_pos, hrd_guard_pos, ret_alloc_pos, ret_guard_pos) or not (
        init_pos < rows_alloc_pos < rows_guard_pos < slice_alloc_pos < slice_guard_pos < block_alloc_pos < block_guard_pos < wavefront_guard_pos < filter_guard_pos < hrd_alloc_pos < hrd_guard_pos < ret_alloc_pos < ret_guard_pos
    ):
        failures.append((FRAMEENCODER_TARGET.as_posix(), 0, 'FrameEncoder::init must guard row, slice, wavefront, filter, HRD, and return-buffer allocations before use'))

    framefilter_init_pos = framefilter_text.find('bool FrameFilter::init(Encoder *top, FrameEncoder *frame, int numRows, uint32_t numCols)')
    ssim_alloc_pos = framefilter_text.find('stagedSsimBuf = X265_MALLOC(int, 8 * (m_param->sourceWidth / 4 + 3));', framefilter_init_pos if framefilter_init_pos != -1 else 0)
    ssim_guard_pos = framefilter_text.find('if (!stagedSsimBuf)', ssim_alloc_pos if ssim_alloc_pos != -1 else 0)
    parallel_alloc_pos = framefilter_text.find('stagedParallelFilter = new (std::nothrow) ParallelFilter[numRows];', ssim_guard_pos if ssim_guard_pos != -1 else 0)
    parallel_guard_pos = framefilter_text.find('if (!stagedParallelFilter)', parallel_alloc_pos if parallel_alloc_pos != -1 else 0)
    free_ssim_pos = framefilter_text.find('X265_FREE(stagedSsimBuf);', parallel_guard_pos if parallel_guard_pos != -1 else 0)
    assign_ssim_pos = framefilter_text.find('m_ssimBuf = stagedSsimBuf;', free_ssim_pos if free_ssim_pos != -1 else 0)
    assign_filter_pos = framefilter_text.find('m_parallelFilter = stagedParallelFilter;', assign_ssim_pos if assign_ssim_pos != -1 else 0)
    return_true_pos = framefilter_text.find('return true;', assign_filter_pos if assign_filter_pos != -1 else 0)
    if -1 in (framefilter_init_pos, ssim_alloc_pos, ssim_guard_pos, parallel_alloc_pos, parallel_guard_pos, free_ssim_pos, assign_ssim_pos, assign_filter_pos, return_true_pos) or not (
        framefilter_init_pos < ssim_alloc_pos < ssim_guard_pos < parallel_alloc_pos < parallel_guard_pos < free_ssim_pos < assign_ssim_pos < assign_filter_pos < return_true_pos
    ):
        failures.append((FRAMEFILTER_TARGET.as_posix(), 0, 'FrameFilter::init must stage SSIM and parallel-filter allocations and roll back SSIM state if filter allocation fails'))

    if not ENCODER_CREATE_SEQUENCE.search(encoder_text):
        failures.append((ENCODER_TARGET.as_posix(), 0, 'Encoder::create must stop launching frame encoder threads after FrameEncoder::init fails'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check frame encoder init allocation guardrails')
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

    print('Frame encoder init allocation guards validated')


if __name__ == '__main__':
    main()
