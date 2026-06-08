#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_inter_temp_luma_alloc_guard.py')

# Coverage probe used by the scan for the reviewed inter tempLuma staging guard.
NORMALIZED_PROBES = (
    'inter tempLuma staging buffer must be checked before reading scaled intra modes',
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
                    'uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, numCUsLoad * scaledNumPartition);',
                    'if (!tempLumaBuf)',
                    '    x265_free_analysis_data(m_param, analysis);',
                    '    m_aborted = true;',
                    '    return;',
                    'X265_FREAD(tempLumaBuf, sizeof(uint8_t), numCUsLoad * scaledNumPartition, m_analysisFileIn, intraPic->modes);',
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
                    'uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, numCUsLoad * scaledNumPartition);',
                    'X265_FREAD(tempLumaBuf, sizeof(uint8_t), numCUsLoad * scaledNumPartition, m_analysisFileIn, intraPic->modes);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing inter tempLuma alloc guardrail: if (!tempLumaBuf)')

    print('Inter tempLuma allocation guard tests passed')


if __name__ == '__main__':
    main()
