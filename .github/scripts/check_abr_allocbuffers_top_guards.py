#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'm_inputPicBuffer = X265_MALLOC(x265_picture**, m_numEncodes);',
    'if (!m_inputPicBuffer)',
    'm_analysisBuffer = X265_MALLOC(x265_analysis_data*, m_numEncodes);',
    'if (!m_analysisBuffer)',
    'm_picIdxReadCnt = X265_MALLOC(ThreadSafeInteger*, m_numEncodes);',
    'if (!m_picIdxReadCnt)',
    'm_analysisWrite = X265_MALLOC(ThreadSafeInteger*, m_numEncodes);',
    'if (!m_analysisWrite)',
    'm_analysisRead = X265_MALLOC(ThreadSafeInteger*, m_numEncodes);',
    'if (!m_analysisRead)',
    'm_readFlag = X265_MALLOC(int*, m_numEncodes);',
    'if (!m_readFlag)',
    'goto fail;',
    'X265_FREE(m_readFlag);',
    'X265_FREE(m_analysisRead);',
    'X265_FREE(m_analysisWrite);',
    'X265_FREE(m_picIdxReadCnt);',
    'X265_FREE(m_analysisBuffer);',
    'X265_FREE(m_inputPicBuffer);',
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
            failures.append((TARGET.as_posix(), 0, f'missing abr allocBuffers top guardrail: {snippet}'))

    alloc_pos = text.find('m_inputPicBuffer = X265_MALLOC(x265_picture**, m_numEncodes);')
    check_pos = text.find('if (!m_inputPicBuffer)', alloc_pos)
    fail_pos = text.find('fail:')
    cleanup_pos = text.find('X265_FREE(m_inputPicBuffer);', fail_pos)
    if -1 not in (alloc_pos, check_pos, fail_pos, cleanup_pos) and not (alloc_pos < check_pos < fail_pos < cleanup_pos):
        failures.append((TARGET.as_posix(), 0, 'AbrEncoder::allocBuffers must guard top-level allocations before later buffer setup and clean them in fail:'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check AbrEncoder allocBuffers top-level allocation guards')
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

    print('AbrEncoder allocBuffers top-level guards validated')


if __name__ == '__main__':
    main()
