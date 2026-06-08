#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_load_staging_cleanup.py')

# Coverage probes used by the scan for analysis-load staging cleanup guardrails.
NORMALIZED_PROBES = (
    'analysis-load seek failures must clean staging buffers, free analysis state, and abort before any frame-record reads continue',
    'analysis-load invalid inter depth run must roll back staged motion buffers',
    'scaled inter-intra mode staging buffer failures must roll back all staged analysis-load buffers',
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
        'void Encoder::readAnalysisFile(x265_analysis_data* analysis, int curPoc, const x265_picture* picIn, int paramBytes)',
        '{',
        '    auto cleanupAnalysisLoadStaging = [&]()',
        '    {',
        '        X265_FREE(mvpIdx[i]);',
        '        X265_FREE(refIdx[i]);',
        '        X265_FREE(mv[i]);',
        '        X265_FREE(cuQPBuf);',
        '        X265_FREE(stagedTempLumaBuf);',
        '        X265_FREE(tempBuf);',
        '    };',
        '    auto seekAnalysisRecord = [&](uint64_t seekOffset)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to seek analysis record\\n");',
        '        cleanupAnalysisLoadStaging();',
        '        x265_free_analysis_data(m_param, analysis);',
        '        m_aborted = true;',
        '        return false;',
        '    };',
        '#define X265_FREAD(val, size, readSize, fileOffset, src) \\',
        '    if (fread(val, size, readSize, fileOffset) != readSize) \\',
        '    { \\',
        '        cleanupAnalysisLoadStaging(); \\',
        '        x265_free_analysis_data(m_param, analysis); \\',
        '        return; \\',
        '    }',
        '    if (m_param->bUseAnalysisFile && !seekAnalysisRecord(totalConsumedBytes + paramBytes))',
        '        return;',
        '    while (poc != curPoc && !feof(m_analysisFileIn))',
        '    {',
        '        if (!seekAnalysisRecord(currentOffset + paramBytes))',
        '            return;',
        '        X265_FREAD(&frameRecordSize, sizeof(uint32_t), 1, m_analysisFileIn, &(picData->frameRecordSize));',
        '    }',
        '    if (!validateAnalysisDepthRun(analysis->numPartitions, depthBuf[d], (uint32_t)count, interMaxDepthEntries, bytes))',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Invalid inter depth run\\n");',
        '        cleanupAnalysisLoadStaging();',
        '    }',
        '    tempLumaBuf = X265_MALLOC(uint8_t, numCUsLoad * scaledNumPartition);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Unable to allocate scaled inter-intra mode staging buffer\\n");',
        '    stagedTempLumaBuf = tempLumaBuf;',
        '    cleanupAnalysisLoadStaging();',
        '    stagedTempLumaBuf = nullptr;',
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
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('X265_FREE(stagedTempLumaBuf);', '', 1)})
        expect_fail(run_checker(root), 'missing analysis-load staging cleanup guardrail: X265_FREE(stagedTempLumaBuf);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('        cleanupAnalysisLoadStaging(); \\', '', 1)})
        expect_fail(run_checker(root), 'analysis-load read failures must clean local staging buffers before freeing analysis state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace('if (!seekAnalysisRecord(currentOffset + paramBytes))', 'if (true)', 1)})
        expect_fail(run_checker(root), 'missing analysis-load staging cleanup guardrail: if (!seekAnalysisRecord(currentOffset + paramBytes))')

    print('Analysis-load staging cleanup guard tests passed')


if __name__ == '__main__':
    main()
