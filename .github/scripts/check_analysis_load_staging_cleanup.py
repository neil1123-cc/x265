#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
ANCHOR = 'void Encoder::readAnalysisFile(x265_analysis_data* analysis, int curPoc, const x265_picture* picIn, int paramBytes)'


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
        return [(TARGET.as_posix(), 0, 'unable to locate analysis-load reader')]

    body = text[func_pos:end_pos]

    required = (
        'auto cleanupAnalysisLoadStaging = [&]()',
        'auto seekAnalysisRecord = [&](uint64_t seekOffset)',
        'X265_FREE(mvpIdx[i]);',
        'X265_FREE(refIdx[i]);',
        'X265_FREE(mv[i]);',
        'X265_FREE(cuQPBuf);',
        'X265_FREE(stagedTempLumaBuf);',
        'X265_FREE(tempBuf);',
        'cleanupAnalysisLoadStaging();',
        'Error reading analysis data. Unable to seek analysis record',
        'if (m_param->bUseAnalysisFile && !seekAnalysisRecord(totalConsumedBytes + paramBytes))',
        'if (!seekAnalysisRecord(currentOffset + paramBytes))',
        'if (!validateAnalysisDepthRun(analysis->numPartitions, depthBuf[d], (uint32_t)count, interMaxDepthEntries, bytes))',
        'Error reading analysis data. Invalid inter depth run',
        'tempLumaBuf = X265_MALLOC(uint8_t, numCUsLoad * scaledNumPartition);',
        'stagedTempLumaBuf = tempLumaBuf;',
        'stagedTempLumaBuf = nullptr;',
    )
    for snippet in required:
        if snippet not in body:
            failures.append((TARGET.as_posix(), 0, f'missing analysis-load staging cleanup guardrail: {snippet}'))

    macro_pos = body.find('#define X265_FREAD')
    macro_cleanup_pos = body.find('cleanupAnalysisLoadStaging();', macro_pos if macro_pos != -1 else 0)
    macro_free_pos = body.find('x265_free_analysis_data(m_param, analysis);', macro_cleanup_pos if macro_cleanup_pos != -1 else 0)
    if -1 in (macro_pos, macro_cleanup_pos, macro_free_pos) or not (macro_pos < macro_cleanup_pos < macro_free_pos):
        failures.append((TARGET.as_posix(), 0, 'analysis-load read failures must clean local staging buffers before freeing analysis state'))

    seek_lambda_pos = body.find('auto seekAnalysisRecord = [&](uint64_t seekOffset)')
    seek_log_pos = body.find('Error reading analysis data. Unable to seek analysis record', seek_lambda_pos if seek_lambda_pos != -1 else 0)
    seek_cleanup_pos = body.find('cleanupAnalysisLoadStaging();', seek_log_pos if seek_log_pos != -1 else 0)
    seek_free_pos = body.find('x265_free_analysis_data(m_param, analysis);', seek_cleanup_pos if seek_cleanup_pos != -1 else 0)
    seek_abort_pos = body.find('m_aborted = true;', seek_free_pos if seek_free_pos != -1 else 0)
    initial_seek_pos = body.find('if (m_param->bUseAnalysisFile && !seekAnalysisRecord(totalConsumedBytes + paramBytes))', seek_abort_pos if seek_abort_pos != -1 else 0)
    loop_seek_pos = body.find('if (!seekAnalysisRecord(currentOffset + paramBytes))', initial_seek_pos if initial_seek_pos != -1 else 0)
    loop_seek_read_pos = body.find('X265_FREAD(&frameRecordSize, sizeof(uint32_t), 1, m_analysisFileIn, &(picData->frameRecordSize));', loop_seek_pos if loop_seek_pos != -1 else 0)
    if -1 in (
        seek_lambda_pos,
        seek_log_pos,
        seek_cleanup_pos,
        seek_free_pos,
        seek_abort_pos,
        initial_seek_pos,
        loop_seek_pos,
        loop_seek_read_pos,
    ) or not (
        seek_lambda_pos < seek_log_pos < seek_cleanup_pos < seek_free_pos < seek_abort_pos < initial_seek_pos < loop_seek_pos < loop_seek_read_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'analysis-load seek failures must clean staging buffers, free analysis state, and abort before any frame-record reads continue'))

    invalid_depth_pos = body.find('Error reading analysis data. Invalid inter depth run')
    invalid_cleanup_pos = body.rfind('cleanupAnalysisLoadStaging();', 0, invalid_depth_pos if invalid_depth_pos != -1 else 0)
    if -1 in (invalid_depth_pos, invalid_cleanup_pos):
        failures.append((TARGET.as_posix(), 0, 'analysis-load invalid inter depth run must roll back staged motion buffers'))

    luma_alloc_pos = body.find('tempLumaBuf = X265_MALLOC(uint8_t, numCUsLoad * scaledNumPartition);')
    luma_guard_pos = body.find('Error reading analysis data. Unable to allocate scaled inter-intra mode staging buffer', luma_alloc_pos if luma_alloc_pos != -1 else 0)
    luma_stage_pos = body.find('stagedTempLumaBuf = tempLumaBuf;', luma_guard_pos if luma_guard_pos != -1 else 0)
    luma_cleanup_pos = body.find('cleanupAnalysisLoadStaging();', luma_guard_pos if luma_guard_pos != -1 else 0)
    if -1 in (luma_alloc_pos, luma_guard_pos, luma_stage_pos, luma_cleanup_pos) or not (luma_alloc_pos < luma_guard_pos < luma_stage_pos):
        failures.append((TARGET.as_posix(), 0, 'scaled inter-intra mode staging buffer failures must roll back all staged analysis-load buffers'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check analysis-load staging cleanup guards')
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

    print('Analysis-load staging cleanup guards validated')


if __name__ == '__main__':
    main()
