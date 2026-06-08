#!/usr/bin/env python3
import argparse
from pathlib import Path


REFERENCE_TARGET = Path('source/encoder/reference.cpp')
FRAMEENCODER_TARGET = Path('source/encoder/frameencoder.cpp')
REFERENCE_ANCHOR = 'int MotionReference::init(PicYuv* recPic, WeightParam *wp, const x265_param& p)'
FRAMEENCODER_ANCHOR = 'for (int l = 0; l < numPredDir; l++)'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    reference_path = repo_root / REFERENCE_TARGET
    if not reference_path.is_file():
        return [(REFERENCE_TARGET.as_posix(), 0, 'missing file')]

    reference_text = reference_path.read_text(encoding='utf-8', errors='ignore')
    reference_start = reference_text.find(REFERENCE_ANCHOR)
    reference_end = reference_text.find('void MotionReference::applyWeight', reference_start if reference_start != -1 else 0)
    if reference_start == -1 or reference_end == -1:
        return [(REFERENCE_TARGET.as_posix(), 0, 'unable to locate MotionReference::init')]
    reference_body = reference_text[reference_start:reference_end]

    required_reference = (
        'bool allocWeightBuffer[3] = { false, false, false };',
        'if (!wp)',
        'return 0;',
        'numSliceWeightedRows = X265_MALLOC(uint32_t, p.maxSlices);',
        'if (!numSliceWeightedRows)',
        'goto fail;',
        'std::fill_n(numSliceWeightedRows, p.maxSlices, uint32_t(0));',
        'allocWeightBuffer[c] = true;',
        'fail:',
        'fpelPlane[0] = recPic->m_picOrg[0];',
        'fpelPlane[1] = recPic->m_picOrg[1];',
        'fpelPlane[2] = recPic->m_picOrg[2];',
        'if (allocWeightBuffer[c])',
        'X265_FREE(weightBuffer[c]);',
        'weightBuffer[c] = nullptr;',
        'X265_FREE(numSliceWeightedRows);',
        'numSliceWeightedRows = nullptr;',
        'return -1;',
    )
    for snippet in required_reference:
        if snippet not in reference_body:
            failures.append((REFERENCE_TARGET.as_posix(), 0, f'missing MotionReference init guardrail: {snippet}'))

    wp_pos = reference_body.find('if (!wp)')
    alloc_pos = reference_body.find('numSliceWeightedRows = X265_MALLOC(uint32_t, p.maxSlices);', wp_pos if wp_pos != -1 else 0)
    null_pos = reference_body.find('if (!numSliceWeightedRows)', alloc_pos if alloc_pos != -1 else 0)
    fill_pos = reference_body.find('std::fill_n(numSliceWeightedRows, p.maxSlices, uint32_t(0));', null_pos if null_pos != -1 else 0)
    fail_pos = reference_body.find('fail:')
    free_rows_pos = reference_body.find('X265_FREE(numSliceWeightedRows);', fail_pos if fail_pos != -1 else 0)
    return_fail_pos = reference_body.find('return -1;', free_rows_pos if free_rows_pos != -1 else 0)
    if -1 in (wp_pos, alloc_pos, null_pos, fill_pos, fail_pos, free_rows_pos, return_fail_pos) or not (
        wp_pos < alloc_pos < null_pos < fill_pos < fail_pos < free_rows_pos < return_fail_pos
    ):
        failures.append((REFERENCE_TARGET.as_posix(), 0, 'MotionReference::init must only allocate slice-weight rows for weighted references and must roll back weighted state on failure'))

    frameencoder_path = repo_root / FRAMEENCODER_TARGET
    if not frameencoder_path.is_file():
        failures.append((FRAMEENCODER_TARGET.as_posix(), 0, 'missing file'))
        return failures

    frameencoder_text = frameencoder_path.read_text(encoding='utf-8', errors='ignore')
    frameencoder_start = frameencoder_text.find(FRAMEENCODER_ANCHOR)
    frameencoder_end = frameencoder_text.find('int numTLD;', frameencoder_start if frameencoder_start != -1 else 0)
    if frameencoder_start == -1 or frameencoder_end == -1:
        failures.append((FRAMEENCODER_TARGET.as_posix(), 0, 'unable to locate motion reference initialization loop'))
        return failures

    frameencoder_body = frameencoder_text[frameencoder_start:frameencoder_end]
    required_frameencoder = (
        'if (m_mref[l][ref].init(slice->m_refReconPicList[l][ref], w, *m_param) < 0)',
        'x265_log(m_param, X265_LOG_ERROR, "Unable to initialize motion reference weights\\n");',
        'm_top->m_aborted = true;',
        'return;',
    )
    for snippet in required_frameencoder:
        if snippet not in frameencoder_body:
            failures.append((FRAMEENCODER_TARGET.as_posix(), 0, f'missing motion reference init failure handling: {snippet}'))

    init_call_pos = frameencoder_body.find('if (m_mref[l][ref].init(slice->m_refReconPicList[l][ref], w, *m_param) < 0)')
    log_pos = frameencoder_body.find('x265_log(m_param, X265_LOG_ERROR, "Unable to initialize motion reference weights\\n");', init_call_pos if init_call_pos != -1 else 0)
    abort_pos = frameencoder_body.find('m_top->m_aborted = true;', log_pos if log_pos != -1 else 0)
    return_pos = frameencoder_body.find('return;', abort_pos if abort_pos != -1 else 0)
    if -1 in (init_call_pos, log_pos, abort_pos, return_pos) or not (
        init_call_pos < log_pos < abort_pos < return_pos
    ):
        failures.append((FRAMEENCODER_TARGET.as_posix(), 0, 'Motion reference init failures must abort frame compression immediately'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MotionReference initialization guards')
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

    print('MotionReference init guards validated')


if __name__ == '__main__':
    main()
