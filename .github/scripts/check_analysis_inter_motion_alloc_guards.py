#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'uint8_t *interDir = nullptr, *chromaDir = nullptr, *mvpIdx[2] = { nullptr, nullptr };',
    'MV* mv[2] = { nullptr, nullptr };',
    'int8_t* refIdx[2] = { nullptr, nullptr };',
    'mvpIdx[i] = X265_MALLOC(uint8_t, depthBytes);',
    'refIdx[i] = X265_MALLOC(int8_t, depthBytes);',
    'mv[i] = X265_MALLOC(MV, depthBytes);',
    'if (!mvpIdx[i] || !refIdx[i] || !mv[i])',
    'for (uint32_t n = 0; n < numDir; n++)',
    'X265_FREE(mvpIdx[n]);',
    'X265_FREE(refIdx[n]);',
    'X265_FREE(mv[n]);',
    'x265_free_analysis_data(m_param, analysis);',
    'm_aborted = true;',
    'return;',
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
            failures.append((TARGET.as_posix(), 0, f'missing inter motion alloc guardrail: {snippet}'))

    alloc_pos = text.find('mvpIdx[i] = X265_MALLOC(uint8_t, depthBytes);')
    check_pos = text.find('if (!mvpIdx[i] || !refIdx[i] || !mv[i])', alloc_pos)
    read_pos = text.find('X265_FREAD(mvpIdx[i], sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->mvpIdx[i]);', alloc_pos)
    if -1 not in (alloc_pos, check_pos, read_pos) and not (alloc_pos < check_pos < read_pos):
        failures.append((TARGET.as_posix(), 0, 'inter motion staging buffers must be checked before reading motion analysis data'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check inter motion staging allocation guardrails')
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

    print('Inter motion staging allocation guards validated')


if __name__ == '__main__':
    main()
