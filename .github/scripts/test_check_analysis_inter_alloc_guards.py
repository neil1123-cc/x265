#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_inter_alloc_guards.py')

# Coverage probes used by the scan for inter-analysis allocation guards.
NORMALIZED_PROBES = (
    'inter analysis tempBuf must be checked before deriving depth and mode buffers',
    'inter analysis cuQPBuf must be checked before reading staged inter data',
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
                    'tempBuf = X265_MALLOC(uint8_t, depthBytes * numBuf);',
                    'if (!tempBuf)',
                    '    x265_free_analysis_data(m_param, analysis);',
                    '    m_aborted = true;',
                    '    return;',
                    'depthBuf = tempBuf;',
                    'cuQPBuf = X265_MALLOC(int8_t, depthBytes);',
                    'if (!cuQPBuf)',
                    '    x265_free_analysis_data(m_param, analysis);',
                    '    m_aborted = true;',
                    '    return;',
                    'X265_FREAD(depthBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->depth);',
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
                    'tempBuf = X265_MALLOC(uint8_t, depthBytes * numBuf);',
                    'depthBuf = tempBuf;',
                    'cuQPBuf = X265_MALLOC(int8_t, depthBytes);',
                    'if (!cuQPBuf)',
                    '    m_aborted = true;',
                    'X265_FREAD(depthBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->depth);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing inter analysis alloc guardrail: if (!tempBuf)')

    print('Inter analysis allocation guard tests passed')


if __name__ == '__main__':
    main()
