#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_scaled_analysis_load_alloc_guards.py')

# Coverage probes used by the scan for scaled analysis-load allocation guardrails.
NORMALIZED_PROBES = (
    'scaled analysis-load seek failures must free analysis state and abort before any frame-record reads continue',
    'scaled VBV staging buffers must be checked before reading lookahead VBV data',
    'scaled intra tempBuf must be checked before deriving depth/mode staging pointers',
    'scaled intra cuQPBuf must be checked before reading staged intra depth data',
    'scaled intra tempLumaBuf must be checked before reading scaled intra modes',
    'scaled inter tempBuf must be checked before deriving staged inter pointers',
    'scaled inter cuQPBuf must be checked before reading staged inter depth data',
    'scaled inter motion staging buffers must be checked before reading motion vectors',
    'scaled inter tempLumaBuf must be checked before reading intra-in-inter modes',
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


def valid_text():
    return '\n'.join((
        'void Encoder::readAnalysisFile(x265_analysis_data* analysis, int curPoc, const x265_picture* picIn, int paramBytes, cuLocation cuLoc)',
        '{',
        '    auto seekAnalysisRecord = [&](uint64_t seekOffset)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to seek analysis record\\n");',
        '        x265_free_analysis_data(m_param, analysis);',
        '        m_aborted = true;',
        '        return false;',
        '    };',
        '    if (m_param->bUseAnalysisFile && !seekAnalysisRecord(totalConsumedBytes + paramBytes))',
        '        return;',
        '    while (poc != curPoc && !feof(m_analysisFileIn))',
        '    {',
        '        if (!seekAnalysisRecord(currentOffset + paramBytes))',
        '            return;',
        '        X265_FREAD(&frameRecordSize, sizeof(uint32_t), 1, m_analysisFileIn, &(picData->frameRecordSize));',
        '    }',
        '    intraSatdForVbvBuf = X265_MALLOC(uint32_t, analysis->numCuInHeight);',
        '    if (!intraVbvCostBuf || !vbvCostBuf || !satdForVbvBuf || !intraSatdForVbvBuf)',
        '        x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to allocate scaled VBV staging buffers\\n");',
        '    X265_FREAD(intraVbvCostBuf, sizeof(uint32_t), analysis->numCUsInFrame, m_analysisFileIn, picData->lookahead.intraVbvCost);',
        '    tempBuf = X265_MALLOC(uint8_t, depthBytes * 3);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to allocate scaled intra reuse staging buffer\\n");',
        '    depthBuf = tempBuf;',
        '    cuQPBuf = X265_MALLOC(int8_t, depthBytes);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to allocate scaled intra cuTree QP staging buffer\\n");',
        '    X265_FREAD(depthBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn, intraPic->depth);',
        '    uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, analysis->numCUsInFrame * scaledNumPartition);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to allocate scaled intra mode staging buffer\\n");',
        '    X265_FREAD(tempLumaBuf, sizeof(uint8_t), analysis->numCUsInFrame * scaledNumPartition, m_analysisFileIn, intraPic->modes);',
        '    uint8_t *interDir = nullptr, *chromaDir = nullptr, *mvpIdx[2] = { nullptr, nullptr };',
        '    MV* mv[2] = { nullptr, nullptr };',
        '    int8_t* refIdx[2] = { nullptr, nullptr };',
        '    tempBuf = X265_MALLOC(uint8_t, depthBytes * numBuf);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to allocate scaled inter reuse staging buffer\\n");',
        '    depthBuf = tempBuf;',
        '    cuQPBuf = X265_MALLOC(int8_t, depthBytes);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to allocate scaled inter cuTree QP staging buffer\\n");',
        '    X265_FREAD(depthBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->depth);',
        '    mvpIdx[i] = X265_MALLOC(uint8_t, depthBytes);',
        '    refIdx[i] = X265_MALLOC(int8_t, depthBytes);',
        '    mv[i] = X265_MALLOC(MV, depthBytes);',
        '    if (!mvpIdx[i] || !refIdx[i] || !mv[i])',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to allocate scaled inter motion staging buffers\\n");',
        '        for (uint32_t n = 0; n < numDir; n++)',
        '        {',
        '            X265_FREE(mvpIdx[n]);',
        '            X265_FREE(refIdx[n]);',
        '            X265_FREE(mv[n]);',
        '        }',
        '    }',
        '    X265_FREAD(mvpIdx[i], sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->mvpIdx[i]);',
        '    uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, analysis->numCUsInFrame * scaledNumPartition);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to allocate scaled inter intra-mode staging buffer\\n");',
        '    X265_FREAD(tempLumaBuf, sizeof(uint8_t), analysis->numCUsInFrame * scaledNumPartition, m_analysisFileIn, intraPic->modes);',
        '}',
        '#undef X265_FREAD',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace(
            'if (!intraVbvCostBuf || !vbvCostBuf || !satdForVbvBuf || !intraSatdForVbvBuf)',
            'if (!intraVbvCostBuf)',
            1,
        )})
        expect_fail(run_checker(root), 'missing scaled analysis-load alloc guardrail: if (!intraVbvCostBuf || !vbvCostBuf || !satdForVbvBuf || !intraSatdForVbvBuf)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace(
            'if (!mvpIdx[i] || !refIdx[i] || !mv[i])',
            'if (!mvpIdx[i])',
            1,
        )})
        expect_fail(run_checker(root), 'missing scaled analysis-load alloc guardrail: if (!mvpIdx[i] || !refIdx[i] || !mv[i])')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace(
            'if (m_param->bUseAnalysisFile && !seekAnalysisRecord(totalConsumedBytes + paramBytes))',
            'if (m_param->bUseAnalysisFile)',
            1,
        )})
        expect_fail(run_checker(root), 'missing scaled analysis-load alloc guardrail: if (m_param->bUseAnalysisFile && !seekAnalysisRecord(totalConsumedBytes + paramBytes))')

    print('Scaled analysis-load allocation guard tests passed')


if __name__ == '__main__':
    main()
