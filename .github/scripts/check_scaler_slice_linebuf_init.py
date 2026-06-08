#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/scaler.cpp')
ANCHOR = 'int ScalerSlice::create(int lumLines, int crLines, int h_sub_sample, int v_sub_sample, int ring)'
END = 'int ScalerSlice::createLines(int size, int width)'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    start = text.find(ANCHOR)
    end = text.find(END, start if start != -1 else 0)
    if start == -1 or end == -1:
        return [(TARGET.as_posix(), 0, 'unable to locate ScalerSlice::create')]

    body = text[start:end]
    failures = []

    required = (
        'm_plane[i].lineBuf = X265_MALLOC(uint8_t*, n);',
        'if (!m_plane[i].lineBuf)',
        'return -1;',
        'std::fill_n(m_plane[i].lineBuf, n, nullptr);',
    )
    for snippet in required:
        if snippet not in body:
            failures.append((TARGET.as_posix(), 0, f'missing scaler slice lineBuf init guardrail: {snippet}'))

    alloc_pos = body.find('m_plane[i].lineBuf = X265_MALLOC(uint8_t*, n);')
    check_pos = body.find('if (!m_plane[i].lineBuf)', alloc_pos if alloc_pos != -1 else 0)
    return_pos = body.find('return -1;', check_pos if check_pos != -1 else 0)
    fill_pos = body.find('std::fill_n(m_plane[i].lineBuf, n, nullptr);', return_pos if return_pos != -1 else 0)
    if -1 in (alloc_pos, check_pos, return_pos, fill_pos) or not (alloc_pos < check_pos < return_pos < fill_pos):
        failures.append((TARGET.as_posix(), 0, 'ScalerSlice::create must clear lineBuf pointer slots after allocation so partial createLines() failures can destroy safely'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ScalerSlice lineBuf initialization guard')
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

    print('ScalerSlice lineBuf init guard validated')


if __name__ == '__main__':
    main()
