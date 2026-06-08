#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/lowres.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    required = (
        'CHECKED_MALLOC_ZERO(picHistogram, uint32_t***, NUMBER_OF_SEGMENTS_IN_WIDTH);',
        'CHECKED_MALLOC_ZERO(picHistogram[0], uint32_t**, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
        'CHECKED_MALLOC_ZERO(picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex], uint32_t*, histogramPlanes);',
        'CHECKED_MALLOC_ZERO(picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex][0], uint32_t, histogramPlanes * HISTOGRAM_NUMBER_OF_BINS);',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing lowres histogram allocation guardrail: {snippet}'))

    forbidden = (
        'picHistogram = X265_MALLOC(uint32_t***, NUMBER_OF_SEGMENTS_IN_WIDTH);',
        'picHistogram[0] = X265_MALLOC(uint32_t**, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
        'picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex] = X265_MALLOC(uint32_t*, histogramPlanes);',
        'picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex][0] = X265_MALLOC(uint32_t, histogramPlanes * HISTOGRAM_NUMBER_OF_BINS);',
    )
    for snippet in forbidden:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden lowres histogram allocation regression: {snippet}'))

    top_alloc_pos = text.find('CHECKED_MALLOC_ZERO(picHistogram, uint32_t***, NUMBER_OF_SEGMENTS_IN_WIDTH);')
    slab_alloc_pos = text.find('CHECKED_MALLOC_ZERO(picHistogram[0], uint32_t**, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);', top_alloc_pos if top_alloc_pos != -1 else 0)
    plane_ptr_alloc_pos = text.find('CHECKED_MALLOC_ZERO(picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex], uint32_t*, histogramPlanes);', slab_alloc_pos if slab_alloc_pos != -1 else 0)
    plane_data_alloc_pos = text.find('CHECKED_MALLOC_ZERO(picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex][0], uint32_t, histogramPlanes * HISTOGRAM_NUMBER_OF_BINS);', plane_ptr_alloc_pos if plane_ptr_alloc_pos != -1 else 0)
    if -1 in (top_alloc_pos, slab_alloc_pos, plane_ptr_alloc_pos, plane_data_alloc_pos) or not (
        top_alloc_pos < slab_alloc_pos < plane_ptr_alloc_pos < plane_data_alloc_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Lowres histogram allocations must be zero-initialized and checked before nested histogram pointers are dereferenced'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Lowres histogram allocation guards')
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

    print('Lowres histogram allocation guards validated')


if __name__ == '__main__':
    main()
