#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_inter_motion_alloc_guards.py')

# Coverage probe used by the scan for the reviewed inter-motion staging guards.
NORMALIZED_PROBES = (
    'inter motion staging buffers must be checked before reading motion analysis data',
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
                    'uint8_t *interDir = nullptr, *chromaDir = nullptr, *mvpIdx[2] = { nullptr, nullptr };',
                    'MV* mv[2] = { nullptr, nullptr };',
                    'int8_t* refIdx[2] = { nullptr, nullptr };',
                    'mvpIdx[i] = X265_MALLOC(uint8_t, depthBytes);',
                    'refIdx[i] = X265_MALLOC(int8_t, depthBytes);',
                    'mv[i] = X265_MALLOC(MV, depthBytes);',
                    'if (!mvpIdx[i] || !refIdx[i] || !mv[i])',
                    '{',
                    '    for (uint32_t n = 0; n < numDir; n++)',
                    '    {',
                    '        X265_FREE(mvpIdx[n]);',
                    '        X265_FREE(refIdx[n]);',
                    '        X265_FREE(mv[n]);',
                    '    }',
                    '    x265_free_analysis_data(m_param, analysis);',
                    '    m_aborted = true;',
                    '    return;',
                    '}',
                    'X265_FREAD(mvpIdx[i], sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->mvpIdx[i]);',
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
                    'uint8_t *interDir = nullptr, *chromaDir = nullptr, *mvpIdx[2] = { nullptr, nullptr };',
                    'MV* mv[2] = { nullptr, nullptr };',
                    'int8_t* refIdx[2] = { nullptr, nullptr };',
                    'mvpIdx[i] = X265_MALLOC(uint8_t, depthBytes);',
                    'refIdx[i] = X265_MALLOC(int8_t, depthBytes);',
                    'mv[i] = X265_MALLOC(MV, depthBytes);',
                    'X265_FREAD(mvpIdx[i], sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->mvpIdx[i]);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing inter motion alloc guardrail: if (!mvpIdx[i] || !refIdx[i] || !mv[i])')

    print('Inter motion staging allocation guard tests passed')


if __name__ == '__main__':
    main()
