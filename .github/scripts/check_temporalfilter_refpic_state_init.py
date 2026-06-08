#!/usr/bin/env python3
import argparse
from pathlib import Path


FRAME_TARGET = Path('source/common/frame.cpp')
TEMPORALFILTER_TARGET = Path('source/common/temporalfilter.cpp')


def read_target(repo_root, target, failures):
    path = repo_root / target
    if not path.is_file():
        failures.append((target.as_posix(), 0, 'missing file'))
        return ''
    return path.read_text(encoding='utf-8', errors='ignore')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    frame_text = read_target(repo_root, FRAME_TARGET, failures)
    temporal_text = read_target(repo_root, TEMPORALFILTER_TARGET, failures)
    if failures:
        return failures

    frame_required = 'std::fill_n(m_mcstfRefList, MAX_MCSTF_TEMPORAL_WINDOW_LENGTH, TemporalFilterRefPicInfo());'
    if frame_required not in frame_text:
        failures.append((FRAME_TARGET.as_posix(), 0, f'missing temporalfilter refpic state-init guardrail: {frame_required}'))

    temporal_required = (
        'refFrame->picBuffer = nullptr;',
        'refFrame->picBufferSubSampled2 = nullptr;',
        'refFrame->picBufferSubSampled4 = nullptr;',
        'refFrame->poc = 0;',
        'refFrame->lowres = nullptr;',
        'refFrame->lowerRes = nullptr;',
        'refFrame->origOffset = 0;',
        'refFrame->isFilteredFrame = false;',
        'refFrame->isSubsampled = nullptr;',
        'refFrame->slicetype = X265_TYPE_AUTO;',
    )
    for snippet in temporal_required:
        if snippet not in temporal_text:
            failures.append((TEMPORALFILTER_TARGET.as_posix(), 0, f'missing temporalfilter refpic state-init guardrail: {snippet}'))

    frame_fill_pos = frame_text.find(frame_required)
    mcstf_pos = frame_text.find('// mcstf')
    if -1 in (mcstf_pos, frame_fill_pos) or not (mcstf_pos < frame_fill_pos):
        failures.append((FRAME_TARGET.as_posix(), 0, 'Frame::Frame must initialize the MCSTF refpic array before MCSTF teardown can observe partially created entries'))

    reset_pos = temporal_text.find('void resetRefPicInfoState(TemporalFilterRefPicInfo* refFrame)')
    pic_buffer_pos = temporal_text.find('refFrame->picBuffer = nullptr;', reset_pos if reset_pos != -1 else 0)
    lowres_pos = temporal_text.find('refFrame->lowres = nullptr;', pic_buffer_pos if pic_buffer_pos != -1 else 0)
    filtered_pos = temporal_text.find('refFrame->isFilteredFrame = false;', lowres_pos if lowres_pos != -1 else 0)
    subsampled_pos = temporal_text.find('refFrame->isSubsampled = nullptr;', filtered_pos if filtered_pos != -1 else 0)
    slicetype_pos = temporal_text.find('refFrame->slicetype = X265_TYPE_AUTO;', subsampled_pos if subsampled_pos != -1 else 0)
    if -1 in (reset_pos, pic_buffer_pos, lowres_pos, filtered_pos, subsampled_pos, slicetype_pos) or not (
        reset_pos < pic_buffer_pos < lowres_pos < filtered_pos < subsampled_pos < slicetype_pos
    ):
        failures.append((TEMPORALFILTER_TARGET.as_posix(), 0, 'resetRefPicInfoState() must restore all non-owned refpic state fields before rollback or destroy paths run'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check temporalfilter refpic state initialization')
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

    print('Temporalfilter refpic state initialization validated')


if __name__ == '__main__':
    main()
