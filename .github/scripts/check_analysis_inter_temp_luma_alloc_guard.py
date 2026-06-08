#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, numCUsLoad * scaledNumPartition);',
    'if (!tempLumaBuf)',
    'x265_free_analysis_data(m_param, analysis);',
    'm_aborted = true;',
    'return;',
    'X265_FREAD(tempLumaBuf, sizeof(uint8_t), numCUsLoad * scaledNumPartition, m_analysisFileIn, intraPic->modes);',
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
            failures.append((TARGET.as_posix(), 0, f'missing inter tempLuma alloc guardrail: {snippet}'))

    alloc_pos = text.find('uint8_t *tempLumaBuf = X265_MALLOC(uint8_t, numCUsLoad * scaledNumPartition);')
    check_pos = text.find('if (!tempLumaBuf)', alloc_pos)
    read_pos = text.find('X265_FREAD(tempLumaBuf, sizeof(uint8_t), numCUsLoad * scaledNumPartition, m_analysisFileIn, intraPic->modes);', alloc_pos)
    if -1 not in (alloc_pos, check_pos, read_pos) and not (alloc_pos < check_pos < read_pos):
        failures.append((TARGET.as_posix(), 0, 'inter tempLuma staging buffer must be checked before reading scaled intra modes'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check inter tempLuma allocation guardrail')
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

    print('Inter tempLuma allocation guard validated')


if __name__ == '__main__':
    main()
