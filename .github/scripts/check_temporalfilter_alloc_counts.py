#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/temporalfilter.cpp')
REQUIRED_SNIPPETS = (
    'CHECKED_MALLOC_ZERO(refFrame->mvs, MV, ((m_sourceWidth ) / 4) * ((m_sourceHeight ) / 4));',
    'CHECKED_MALLOC_ZERO(refFrame->mvs0, MV, ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
    'CHECKED_MALLOC_ZERO(refFrame->mvs1, MV, ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
    'CHECKED_MALLOC_ZERO(refFrame->mvs2, MV, ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
    'CHECKED_MALLOC_ZERO(refFrame->noise, int, ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
    'CHECKED_MALLOC_ZERO(refFrame->error, int, ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
)
FORBIDDEN_SNIPPETS = (
    'CHECKED_MALLOC_ZERO(refFrame->mvs, MV, sizeof(MV)* ((m_sourceWidth ) / 4) * ((m_sourceHeight ) / 4));',
    'CHECKED_MALLOC_ZERO(refFrame->mvs0, MV, sizeof(MV)* ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
    'CHECKED_MALLOC_ZERO(refFrame->mvs1, MV, sizeof(MV)* ((m_sourceWidth ) / 16) * ((m_sourceHeight ) / 16));',
    'CHECKED_MALLOC_ZERO(refFrame->mvs2, MV, sizeof(MV)* ((m_sourceWidth ) / 16)*((m_sourceHeight ) / 16));',
    'CHECKED_MALLOC_ZERO(refFrame->noise, int, sizeof(int) * ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
    'CHECKED_MALLOC_ZERO(refFrame->error, int, sizeof(int) * ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));',
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
            failures.append((TARGET.as_posix(), 0, f'missing temporalfilter allocation-count guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden temporalfilter allocation-count regression: {snippet}'))

    func_pos = text.find('int TemporalFilter::createRefPicInfo(TemporalFilterRefPicInfo* refFrame, x265_param* param)')
    mvs_pos = text.find('CHECKED_MALLOC_ZERO(refFrame->mvs, MV, ((m_sourceWidth ) / 4) * ((m_sourceHeight ) / 4));', func_pos if func_pos != -1 else 0)
    noise_pos = text.find('CHECKED_MALLOC_ZERO(refFrame->noise, int, ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));', mvs_pos if mvs_pos != -1 else 0)
    error_pos = text.find('CHECKED_MALLOC_ZERO(refFrame->error, int, ((m_sourceWidth) / 4) * ((m_sourceHeight) / 4));', noise_pos if noise_pos != -1 else 0)
    if -1 in (func_pos, mvs_pos, noise_pos, error_pos) or not (func_pos < mvs_pos < noise_pos < error_pos):
        failures.append((TARGET.as_posix(), 0, 'TemporalFilter::createRefPicInfo must allocate MV and error buffers using element counts, not byte counts'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check temporalfilter allocation-count guardrails')
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

    print('Temporalfilter allocation counts validated')


if __name__ == '__main__':
    main()
