#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
ANCHOR = 'void Encoder::readAnalysisFile(x265_analysis_data* analysis, int curPoc, const x265_picture* picIn, int paramBytes, cuLocation cuLoc)'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    func_pos = text.find(ANCHOR)
    end_pos = text.find('#undef X265_FREAD', func_pos if func_pos != -1 else 0)
    if func_pos == -1 or end_pos == -1:
        return [(TARGET.as_posix(), 0, 'unable to locate scaled analysis-load reader')]

    body = text[func_pos:end_pos]

    required = (
        'auto seekAnalysisRecord = [&](uint64_t seekOffset)',
        'Error reading analysis data. Unable to seek analysis record',
        'if (m_param->bUseAnalysisFile && !seekAnalysisRecord(totalConsumedBytes + paramBytes))',
        'if (!seekAnalysisRecord(currentOffset + paramBytes))',
        'if (!intraVbvCostBuf || !vbvCostBuf || !satdForVbvBuf || !intraSatdForVbvBuf)',
        'Unable to allocate scaled VBV staging buffers',
        'Unable to allocate scaled intra reuse staging buffer',
        'Unable to allocate scaled intra cuTree QP staging buffer',
        'Unable to allocate scaled intra mode staging buffer',
        'uint8_t *interDir = nullptr, *chromaDir = nullptr, *mvpIdx[2] = { nullptr, nullptr };',
        'MV* mv[2] = { nullptr, nullptr };',
        'int8_t* refIdx[2] = { nullptr, nullptr };',
        'Unable to allocate scaled inter reuse staging buffer',
        'Unable to allocate scaled inter cuTree QP staging buffer',
        'if (!mvpIdx[i] || !refIdx[i] || !mv[i])',
        'Unable to allocate scaled inter motion staging buffers',
        'for (uint32_t n = 0; n < numDir; n++)',
        'X265_FREE(mvpIdx[n]);',
        'X265_FREE(refIdx[n]);',
        'X265_FREE(mv[n]);',
        'Unable to allocate scaled inter intra-mode staging buffer',
    )
    for snippet in required:
        if snippet not in body:
            failures.append((TARGET.as_posix(), 0, f'missing scaled analysis-load alloc guardrail: {snippet}'))

    seek_lambda_pos = body.find('auto seekAnalysisRecord = [&](uint64_t seekOffset)')
    seek_log_pos = body.find('Error reading analysis data. Unable to seek analysis record', seek_lambda_pos if seek_lambda_pos != -1 else 0)
    seek_free_pos = body.find('x265_free_analysis_data(m_param, analysis);', seek_log_pos if seek_log_pos != -1 else 0)
    seek_abort_pos = body.find('m_aborted = true;', seek_free_pos if seek_free_pos != -1 else 0)
    initial_seek_pos = body.find('if (m_param->bUseAnalysisFile && !seekAnalysisRecord(totalConsumedBytes + paramBytes))', seek_abort_pos if seek_abort_pos != -1 else 0)
    loop_seek_pos = body.find('if (!seekAnalysisRecord(currentOffset + paramBytes))', initial_seek_pos if initial_seek_pos != -1 else 0)
    loop_seek_read_pos = body.find('X265_FREAD(&frameRecordSize, sizeof(uint32_t), 1, m_analysisFileIn, &(picData->frameRecordSize));', loop_seek_pos if loop_seek_pos != -1 else 0)
    if -1 in (
        seek_lambda_pos,
        seek_log_pos,
        seek_free_pos,
        seek_abort_pos,
        initial_seek_pos,
        loop_seek_pos,
        loop_seek_read_pos,
    ) or not (
        seek_lambda_pos < seek_log_pos < seek_free_pos < seek_abort_pos < initial_seek_pos < loop_seek_pos < loop_seek_read_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'scaled analysis-load seek failures must free analysis state and abort before any frame-record reads continue'))

    vbv_alloc_pos = body.find('intraSatdForVbvBuf = X265_MALLOC(uint32_t, analysis->numCuInHeight);')
    vbv_guard_pos = body.find('if (!intraVbvCostBuf || !vbvCostBuf || !satdForVbvBuf || !intraSatdForVbvBuf)', vbv_alloc_pos if vbv_alloc_pos != -1 else 0)
    vbv_read_pos = body.find('X265_FREAD(intraVbvCostBuf, sizeof(uint32_t), analysis->numCUsInFrame, m_analysisFileIn, picData->lookahead.intraVbvCost);', vbv_guard_pos if vbv_guard_pos != -1 else 0)
    if -1 in (vbv_alloc_pos, vbv_guard_pos, vbv_read_pos) or not (vbv_alloc_pos < vbv_guard_pos < vbv_read_pos):
        failures.append((TARGET.as_posix(), 0, 'scaled VBV staging buffers must be checked before reading lookahead VBV data'))

    intra_alloc_pos = body.find('tempBuf = X265_MALLOC(uint8_t, depthBytes * 3);')
    intra_guard_pos = body.find('Unable to allocate scaled intra reuse staging buffer', intra_alloc_pos if intra_alloc_pos != -1 else 0)
    intra_assign_pos = body.find('depthBuf = tempBuf;', intra_guard_pos if intra_guard_pos != -1 else 0)
    if -1 in (intra_alloc_pos, intra_guard_pos, intra_assign_pos) or not (intra_alloc_pos < intra_guard_pos < intra_assign_pos):
        failures.append((TARGET.as_posix(), 0, 'scaled intra tempBuf must be checked before deriving depth/mode staging pointers'))

    intra_cuqp_alloc_pos = body.find('cuQPBuf = X265_MALLOC(int8_t, depthBytes);', intra_assign_pos if intra_assign_pos != -1 else 0)
    intra_cuqp_guard_pos = body.find('Unable to allocate scaled intra cuTree QP staging buffer', intra_cuqp_alloc_pos if intra_cuqp_alloc_pos != -1 else 0)
    intra_read_pos = body.find('X265_FREAD(depthBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn, intraPic->depth);', intra_cuqp_guard_pos if intra_cuqp_guard_pos != -1 else 0)
    if -1 in (intra_cuqp_alloc_pos, intra_cuqp_guard_pos, intra_read_pos) or not (intra_cuqp_alloc_pos < intra_cuqp_guard_pos < intra_read_pos):
        failures.append((TARGET.as_posix(), 0, 'scaled intra cuQPBuf must be checked before reading staged intra depth data'))

    intra_luma_alloc_pos = body.find('uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, analysis->numCUsInFrame * scaledNumPartition);')
    intra_luma_guard_pos = body.find('Unable to allocate scaled intra mode staging buffer', intra_luma_alloc_pos if intra_luma_alloc_pos != -1 else 0)
    intra_luma_read_pos = body.find('X265_FREAD(tempLumaBuf, sizeof(uint8_t), analysis->numCUsInFrame * scaledNumPartition, m_analysisFileIn, intraPic->modes);', intra_luma_guard_pos if intra_luma_guard_pos != -1 else 0)
    if -1 in (intra_luma_alloc_pos, intra_luma_guard_pos, intra_luma_read_pos) or not (intra_luma_alloc_pos < intra_luma_guard_pos < intra_luma_read_pos):
        failures.append((TARGET.as_posix(), 0, 'scaled intra tempLumaBuf must be checked before reading scaled intra modes'))

    inter_section_pos = body.find('uint8_t *interDir = nullptr, *chromaDir = nullptr, *mvpIdx[2] = { nullptr, nullptr };')
    inter_alloc_pos = body.find('tempBuf = X265_MALLOC(uint8_t, depthBytes * numBuf);', inter_section_pos if inter_section_pos != -1 else 0)
    inter_guard_pos = body.find('Unable to allocate scaled inter reuse staging buffer', inter_alloc_pos if inter_alloc_pos != -1 else 0)
    inter_assign_pos = body.find('depthBuf = tempBuf;', inter_guard_pos if inter_guard_pos != -1 else 0)
    if -1 in (inter_alloc_pos, inter_guard_pos, inter_assign_pos) or not (inter_alloc_pos < inter_guard_pos < inter_assign_pos):
        failures.append((TARGET.as_posix(), 0, 'scaled inter tempBuf must be checked before deriving staged inter pointers'))

    inter_cuqp_alloc_pos = body.find('cuQPBuf = X265_MALLOC(int8_t, depthBytes);', inter_assign_pos if inter_assign_pos != -1 else 0)
    inter_cuqp_guard_pos = body.find('Unable to allocate scaled inter cuTree QP staging buffer', inter_cuqp_alloc_pos if inter_cuqp_alloc_pos != -1 else 0)
    inter_read_pos = body.find('X265_FREAD(depthBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->depth);', inter_cuqp_guard_pos if inter_cuqp_guard_pos != -1 else 0)
    if -1 in (inter_cuqp_alloc_pos, inter_cuqp_guard_pos, inter_read_pos) or not (inter_cuqp_alloc_pos < inter_cuqp_guard_pos < inter_read_pos):
        failures.append((TARGET.as_posix(), 0, 'scaled inter cuQPBuf must be checked before reading staged inter depth data'))

    motion_alloc_pos = body.find('mvpIdx[i] = X265_MALLOC(uint8_t, depthBytes);', inter_read_pos if inter_read_pos != -1 else 0)
    motion_guard_pos = body.find('if (!mvpIdx[i] || !refIdx[i] || !mv[i])', motion_alloc_pos if motion_alloc_pos != -1 else 0)
    motion_read_pos = body.find('X265_FREAD(mvpIdx[i], sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->mvpIdx[i]);', motion_guard_pos if motion_guard_pos != -1 else 0)
    if -1 in (motion_alloc_pos, motion_guard_pos, motion_read_pos) or not (motion_alloc_pos < motion_guard_pos < motion_read_pos):
        failures.append((TARGET.as_posix(), 0, 'scaled inter motion staging buffers must be checked before reading motion vectors'))

    inter_luma_alloc_pos = body.rfind('uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, analysis->numCUsInFrame * scaledNumPartition);')
    inter_luma_guard_pos = body.find('Unable to allocate scaled inter intra-mode staging buffer', inter_luma_alloc_pos if inter_luma_alloc_pos != -1 else 0)
    inter_luma_read_pos = body.find('X265_FREAD(tempLumaBuf, sizeof(uint8_t), analysis->numCUsInFrame * scaledNumPartition, m_analysisFileIn, intraPic->modes);', inter_luma_guard_pos if inter_luma_guard_pos != -1 else 0)
    if -1 in (inter_luma_alloc_pos, inter_luma_guard_pos, inter_luma_read_pos) or not (inter_luma_alloc_pos < inter_luma_guard_pos < inter_luma_read_pos):
        failures.append((TARGET.as_posix(), 0, 'scaled inter tempLumaBuf must be checked before reading intra-in-inter modes'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scaled analysis-load allocation guardrails')
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

    print('Scaled analysis-load allocation guards validated')


if __name__ == '__main__':
    main()
