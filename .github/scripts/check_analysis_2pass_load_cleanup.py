#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
ANCHOR = 'void Encoder::readAnalysisFile(x265_analysis_data* analysis, int curPoc, int sliceType)'


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
        return [(TARGET.as_posix(), 0, 'unable to locate 2-pass analysis-load reader')]

    body = text[func_pos:end_pos]

    required = (
        'auto cleanupAnalysis2PassStaging = [&]()',
        'cleanupAnalysis2PassStaging();',
        'x265_free_analysis_data(m_param, analysis);',
        'tempBuf = X265_MALLOC(uint8_t, depthBytes);',
        'Unable to allocate depth staging buffer',
        'tempRefBuf = X265_MALLOC(int32_t, numDir * depthBytes);',
        'Unable to allocate inter reference staging buffer',
        'tempMVBuf[i] = X265_MALLOC(MV, depthBytes);',
        'tempMvpBuf[i] = X265_MALLOC(uint8_t, depthBytes);',
        'if (!tempMVBuf[i] || !tempMvpBuf[i])',
        'Unable to allocate inter motion staging buffers',
        'tempModeBuf = X265_MALLOC(uint8_t, depthBytes);',
        'Unable to allocate inter mode staging buffer',
    )
    for snippet in required:
        if snippet not in body:
            failures.append((TARGET.as_posix(), 0, f'missing 2-pass analysis cleanup guardrail: {snippet}'))

    forbidden = 'x265_alloc_analysis_data(m_param, analysis);'
    if forbidden in body:
        failures.append((TARGET.as_posix(), 0, f'forbidden 2-pass analysis cleanup regression: {forbidden}'))

    macro_pos = body.find('#define X265_FREAD')
    cleanup_pos = body.find('cleanupAnalysis2PassStaging();', macro_pos if macro_pos != -1 else 0)
    free_pos = body.find('x265_free_analysis_data(m_param, analysis);', cleanup_pos if cleanup_pos != -1 else 0)
    if -1 in (macro_pos, cleanup_pos, free_pos) or not (macro_pos < cleanup_pos < free_pos):
        failures.append((TARGET.as_posix(), 0, '2-pass analysis read failures must clean up staged buffers before freeing analysis state'))

    depth_alloc_pos = body.find('tempBuf = X265_MALLOC(uint8_t, depthBytes);')
    depth_guard_pos = body.find('Unable to allocate depth staging buffer', depth_alloc_pos if depth_alloc_pos != -1 else 0)
    depth_read_pos = body.find('X265_FREAD(tempBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn);', depth_guard_pos if depth_guard_pos != -1 else 0)
    if -1 in (depth_alloc_pos, depth_guard_pos, depth_read_pos) or not (depth_alloc_pos < depth_guard_pos < depth_read_pos):
        failures.append((TARGET.as_posix(), 0, '2-pass depth staging buffer must be checked before reading depth runs'))

    ref_alloc_pos = body.find('tempRefBuf = X265_MALLOC(int32_t, numDir * depthBytes);')
    ref_guard_pos = body.find('Unable to allocate inter reference staging buffer', ref_alloc_pos if ref_alloc_pos != -1 else 0)
    if -1 in (ref_alloc_pos, ref_guard_pos) or not (ref_alloc_pos < ref_guard_pos):
        failures.append((TARGET.as_posix(), 0, '2-pass inter reference staging buffer must be checked immediately after allocation'))

    motion_alloc_pos = body.find('tempMVBuf[i] = X265_MALLOC(MV, depthBytes);', ref_guard_pos if ref_guard_pos != -1 else 0)
    motion_guard_pos = body.find('if (!tempMVBuf[i] || !tempMvpBuf[i])', motion_alloc_pos if motion_alloc_pos != -1 else 0)
    motion_read_pos = body.find('X265_FREAD(tempMVBuf[i], sizeof(MV), depthBytes, m_analysisFileIn);', motion_guard_pos if motion_guard_pos != -1 else 0)
    if -1 in (motion_alloc_pos, motion_guard_pos, motion_read_pos) or not (motion_alloc_pos < motion_guard_pos < motion_read_pos):
        failures.append((TARGET.as_posix(), 0, '2-pass inter motion staging buffers must be checked before reading motion payloads'))

    mode_alloc_pos = body.find('tempModeBuf = X265_MALLOC(uint8_t, depthBytes);', motion_read_pos if motion_read_pos != -1 else 0)
    mode_guard_pos = body.find('Unable to allocate inter mode staging buffer', mode_alloc_pos if mode_alloc_pos != -1 else 0)
    mode_read_pos = body.find('X265_FREAD(tempModeBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn);', mode_guard_pos if mode_guard_pos != -1 else 0)
    if -1 in (mode_alloc_pos, mode_guard_pos, mode_read_pos) or not (mode_alloc_pos < mode_guard_pos < mode_read_pos):
        failures.append((TARGET.as_posix(), 0, '2-pass inter mode staging buffer must be checked before reading mode payloads'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check 2-pass analysis-load cleanup and allocation guards')
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

    print('2-pass analysis-load cleanup guards validated')


if __name__ == '__main__':
    main()
