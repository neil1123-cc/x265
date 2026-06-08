#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'tempBuf = X265_MALLOC(uint8_t, depthBytes * 3);',
    'if (!tempBuf)',
    'cuQPBuf = X265_MALLOC(int8_t, depthBytes);',
    'if (!cuQPBuf)',
    'uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, numCUsLoad * scaledNumPartition);',
    'if (!tempLumaBuf)',
    'x265_free_analysis_data(m_param, analysis);',
    'm_aborted = true;',
    'return;',
)
FORBIDDEN_SNIPPETS = ()


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden intra analysis alloc regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing intra analysis alloc guardrail: {snippet}'))

    temp_alloc_pos = text.find('tempBuf = X265_MALLOC(uint8_t, depthBytes * 3);')
    temp_check_pos = text.find('if (!tempBuf)')
    depth_assign_pos = text.find('depthBuf = tempBuf;')
    cuqp_alloc_pos = text.find('cuQPBuf = X265_MALLOC(int8_t, depthBytes);')
    cuqp_check_pos = text.find('if (!cuQPBuf)')
    depth_read_pos = text.find('X265_FREAD(depthBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn, intraPic->depth);')
    luma_alloc_pos = text.find('uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, numCUsLoad * scaledNumPartition);')
    luma_check_pos = text.find('if (!tempLumaBuf)')
    luma_read_pos = text.find('X265_FREAD(tempLumaBuf, sizeof(uint8_t), numCUsLoad * scaledNumPartition, m_analysisFileIn, intraPic->modes);')

    if -1 not in (temp_alloc_pos, temp_check_pos, depth_assign_pos) and not (temp_alloc_pos < temp_check_pos < depth_assign_pos):
        failures.append((TARGET.as_posix(), 0, 'intra analysis tempBuf must be checked before deriving depth/mode/part buffers'))
    if -1 not in (cuqp_alloc_pos, cuqp_check_pos, depth_read_pos) and not (cuqp_alloc_pos < cuqp_check_pos < depth_read_pos):
        failures.append((TARGET.as_posix(), 0, 'intra analysis cuQPBuf must be checked before reading staged depth/mode data'))
    if -1 not in (luma_alloc_pos, luma_check_pos, luma_read_pos) and not (luma_alloc_pos < luma_check_pos < luma_read_pos):
        failures.append((TARGET.as_posix(), 0, 'intra analysis tempLumaBuf must be checked before reading scaled modes'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check intra analysis allocation guardrails')
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

    print('Intra analysis allocation guards validated')


if __name__ == '__main__':
    main()
