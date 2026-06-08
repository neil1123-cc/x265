#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'tempBuf = X265_MALLOC(uint8_t, depthBytes * numBuf);',
    'if (!tempBuf)',
    'cuQPBuf = X265_MALLOC(int8_t, depthBytes);',
    'if (!cuQPBuf)',
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
            failures.append((TARGET.as_posix(), 0, f'missing inter analysis alloc guardrail: {snippet}'))

    inter_branch_pos = text.find('tempBuf = X265_MALLOC(uint8_t, depthBytes * numBuf);')
    temp_alloc_pos = inter_branch_pos
    temp_check_pos = text.find('if (!tempBuf)', inter_branch_pos)
    depth_assign_pos = text.find('depthBuf = tempBuf;', inter_branch_pos)
    cuqp_alloc_pos = text.find('cuQPBuf = X265_MALLOC(int8_t, depthBytes);')
    cuqp_check_pos = text.find('if (!cuQPBuf)')
    inter_depth_read_pos = text.find('X265_FREAD(depthBuf, sizeof(uint8_t), depthBytes, m_analysisFileIn, interPic->depth);')

    if -1 not in (temp_alloc_pos, temp_check_pos, depth_assign_pos) and not (temp_alloc_pos < temp_check_pos < depth_assign_pos):
        failures.append((TARGET.as_posix(), 0, 'inter analysis tempBuf must be checked before deriving depth and mode buffers'))
    if -1 not in (cuqp_alloc_pos, cuqp_check_pos, inter_depth_read_pos) and not (cuqp_alloc_pos < cuqp_check_pos < inter_depth_read_pos):
        failures.append((TARGET.as_posix(), 0, 'inter analysis cuQPBuf must be checked before reading staged inter data'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check inter analysis allocation guardrails')
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

    print('Inter analysis allocation guards validated')


if __name__ == '__main__':
    main()
