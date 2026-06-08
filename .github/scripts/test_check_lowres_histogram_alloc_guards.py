#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lowres_histogram_alloc_guards.py')

# Coverage probes used by the scan for lowres histogram allocation guardrails.
NORMALIZED_PROBES = (
    'Lowres histogram allocations must be zero-initialized and checked before nested histogram pointers are dereferenced',
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


def valid_text():
    return '\n'.join((
        'CHECKED_MALLOC_ZERO(picHistogram, uint32_t***, NUMBER_OF_SEGMENTS_IN_WIDTH);',
        'CHECKED_MALLOC_ZERO(picHistogram[0], uint32_t**, NUMBER_OF_SEGMENTS_IN_WIDTH * NUMBER_OF_SEGMENTS_IN_HEIGHT);',
        'CHECKED_MALLOC_ZERO(picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex], uint32_t*, histogramPlanes);',
        'CHECKED_MALLOC_ZERO(picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex][0], uint32_t, histogramPlanes * HISTOGRAM_NUMBER_OF_BINS);',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/lowres.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/lowres.cpp': valid_text().replace('CHECKED_MALLOC_ZERO(picHistogram, uint32_t***, NUMBER_OF_SEGMENTS_IN_WIDTH);', 'picHistogram = X265_MALLOC(uint32_t***, NUMBER_OF_SEGMENTS_IN_WIDTH);', 1)})
        expect_fail(run_checker(root), 'missing lowres histogram allocation guardrail: CHECKED_MALLOC_ZERO(picHistogram, uint32_t***, NUMBER_OF_SEGMENTS_IN_WIDTH);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/lowres.cpp': valid_text().replace('CHECKED_MALLOC_ZERO(picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex][0], uint32_t, histogramPlanes * HISTOGRAM_NUMBER_OF_BINS);', 'picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex][0] = X265_MALLOC(uint32_t, histogramPlanes * HISTOGRAM_NUMBER_OF_BINS);', 1)})
        expect_fail(run_checker(root), 'forbidden lowres histogram allocation regression: picHistogram[regionInPictureWidthIndex][regionInPictureHeightIndex][0] = X265_MALLOC(uint32_t, histogramPlanes * HISTOGRAM_NUMBER_OF_BINS);')

    print('Lowres histogram allocation guard tests passed')


if __name__ == '__main__':
    main()
