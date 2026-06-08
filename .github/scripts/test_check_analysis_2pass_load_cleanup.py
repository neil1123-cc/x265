#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_2pass_load_cleanup.py')

# Coverage probes used by the scan for 2-pass analysis-load cleanup guardrails.
NORMALIZED_PROBES = (
    '2-pass analysis read failures must clean up staged buffers before freeing analysis state',
    '2-pass depth staging buffer must be checked before reading depth runs',
    '2-pass inter reference staging buffer must be checked immediately after allocation',
    '2-pass inter motion staging buffers must be checked before reading motion payloads',
    '2-pass inter mode staging buffer must be checked before reading mode payloads',
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
        'void Encoder::readAnalysisFile(x265_analysis_data* analysis, int curPoc, int sliceType)',
        '{',
        '    auto cleanupAnalysis2PassStaging = [&]()',
        '    {',
        '    };',
        '#define X265_FREAD(val, size, readSize, fileOffset) \\',
        '    if (fread(val, size, readSize, fileOffset) != readSize) \\',
        '    { \\',
        '    cleanupAnalysis2PassStaging(); \\',
        '    x265_free_analysis_data(m_param, analysis); \\',
        '    return; \\',
        '}',
        '    tempBuf = X265_MALLOC(uint8_t, depthBytes);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis 2 pass data. Unable to allocate depth staging buffer\\n");',
        '    X265_FREAD(tempBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn);',
        '    tempRefBuf = X265_MALLOC(int32_t, numDir * depthBytes);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis 2 pass data. Unable to allocate inter reference staging buffer\\n");',
        '    tempMVBuf[i] = X265_MALLOC(MV, depthBytes);',
        '    tempMvpBuf[i] = X265_MALLOC(uint8_t, depthBytes);',
        '    if (!tempMVBuf[i] || !tempMvpBuf[i])',
        '        x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis 2 pass data. Unable to allocate inter motion staging buffers\\n");',
        '    X265_FREAD(tempMVBuf[i], sizeof(MV), depthBytes, m_analysisFileIn);',
        '    tempModeBuf = X265_MALLOC(uint8_t, depthBytes);',
        '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis 2 pass data. Unable to allocate inter mode staging buffer\\n");',
        '    X265_FREAD(tempModeBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn);',
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
            'x265_free_analysis_data(m_param, analysis);',
            'x265_alloc_analysis_data(m_param, analysis);',
            1,
        )})
        expect_fail(run_checker(root), 'forbidden 2-pass analysis cleanup regression: x265_alloc_analysis_data(m_param, analysis);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/encoder.cpp': valid_text().replace(
            'if (!tempMVBuf[i] || !tempMvpBuf[i])',
            'if (!tempMVBuf[i])',
            1,
        )})
        expect_fail(run_checker(root), 'missing 2-pass analysis cleanup guardrail: if (!tempMVBuf[i] || !tempMvpBuf[i])')

    print('2-pass analysis-load cleanup guard tests passed')


if __name__ == '__main__':
    main()
