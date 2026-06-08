#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
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
    'if (m_inputPicBuffer && m_inputPicBuffer[pass])',
    'if (m_inputPicBuffer[pass][index])',
    'X265_FREE(m_inputPicBuffer[pass][index]->planes[0]);',
    'x265_picture_free(m_inputPicBuffer[pass][index]);',
    'X265_FREE(m_analysisBuffer ? m_analysisBuffer[pass] : nullptr);',
    'X265_FREE(m_readFlag ? m_readFlag[pass] : nullptr);',
    'delete[] m_analysisReadCnt;',
    'delete[] m_analysisWriteCnt;',
    'delete[] m_picReadCnt;',
    'delete[] m_picWriteCnt;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing abr allocBuffers partial cleanup guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check AbrEncoder allocBuffers partial cleanup rollback')
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

    print('AbrEncoder allocBuffers partial cleanup validated')


if __name__ == '__main__':
    main()
