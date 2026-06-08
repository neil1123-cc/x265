#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_inter_depth_run_guard.py')

# Coverage probes used by the scan for inter depth-run guardrails.
NORMALIZED_PROBES = (
    'inter depth-run validation must happen before inter depth/mode writes',
    'missing inter depth-run guardrail: ',
    'forbidden inter depth-run regression: ',
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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'size_t count = 0;',
                    'uint32_t interMaxDepthEntries = analysis->numCUsInFrame * analysis->numPartitions;',
                    'if (!validateAnalysisDepthRun(analysis->numPartitions, depthBuf[d], (uint32_t)count, interMaxDepthEntries, bytes))',
                    '{',
                    '    x265_log(nullptr, X265_LOG_ERROR, "Error reading analysis data. Invalid inter depth run\\n");',
                    '    x265_free_analysis_data(m_param, analysis);',
                    '    m_aborted = true;',
                    '    return;',
                    '}',
                    'std::fill_n(&(analysis->interData)->depth[count], bytes, depthBuf[d]);',
                    'std::fill_n(&(analysis->interData)->modes[count], bytes, modeBuf[d]);',
                    'count += bytes;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'size_t count = 0;',
                    'uint32_t interMaxDepthEntries = analysis->numCUsInFrame * analysis->numPartitions;',
                    'size_t bytes = analysis->numPartitions >> (depthBuf[d] * 2);',
                    'std::fill_n(&(analysis->interData)->depth[count], bytes, depthBuf[d]);',
                    'std::fill_n(&(analysis->interData)->modes[count], bytes, modeBuf[d]);',
                    'count += bytes;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden inter depth-run regression')

    print('Inter depth-run validation guard tests passed')


if __name__ == '__main__':
    main()
