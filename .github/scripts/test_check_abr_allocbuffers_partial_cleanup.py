#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_abr_allocbuffers_partial_cleanup.py')


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
                'source/abrEncApp.cpp': '\n'.join((
                    'm_inputPicBuffer = nullptr;',
                    'm_analysisBuffer = nullptr;',
                    'm_picWriteCnt = nullptr;',
                    'm_picReadCnt = nullptr;',
                    'm_analysisWriteCnt = nullptr;',
                    'm_analysisReadCnt = nullptr;',
                    'std::fill_n(m_inputPicBuffer, inputPicBufferCount, nullptr);',
                    'std::fill_n(m_analysisBuffer, m_numEncodes, nullptr);',
                    'std::fill_n(m_picIdxReadCnt, m_numEncodes, nullptr);',
                    'std::fill_n(m_analysisWrite, m_numEncodes, nullptr);',
                    'std::fill_n(m_analysisRead, m_numEncodes, nullptr);',
                    'std::fill_n(m_readFlag, m_numEncodes, nullptr);',
                    'for (uint8_t pass = 0; pass < queueOwnerCount; pass++)',
                    '{',
                    '    if (m_inputPicBuffer && m_inputPicBuffer[pass])',
                    '    {',
                    '        if (m_inputPicBuffer[pass][index])',
                    '        {',
                    '            X265_FREE(m_inputPicBuffer[pass][index]->planes[0]);',
                    '            x265_picture_free(m_inputPicBuffer[pass][index]);',
                    '        }',
                    '    }',
                    '    X265_FREE(m_analysisBuffer ? m_analysisBuffer[pass] : nullptr);',
                    '    X265_FREE(m_readFlag ? m_readFlag[pass] : nullptr);',
                    '}',
                    'delete[] m_analysisReadCnt;',
                    'delete[] m_analysisWriteCnt;',
                    'delete[] m_picReadCnt;',
                    'delete[] m_picWriteCnt;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/abrEncApp.cpp': '\n'.join((
                    'm_inputPicBuffer = nullptr;',
                    'm_analysisBuffer = nullptr;',
                    'for (uint8_t pass = 0; pass < queueOwnerCount; pass++)',
                    '{',
                    '    X265_FREE(m_inputPicBuffer[pass]);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing abr allocBuffers partial cleanup guardrail: std::fill_n(m_inputPicBuffer, inputPicBufferCount, nullptr);')

    print('AbrEncoder allocBuffers partial cleanup tests passed')


if __name__ == '__main__':
    main()
