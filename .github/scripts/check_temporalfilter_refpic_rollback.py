#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/temporalfilter.cpp')
REQUIRED_SNIPPETS = (
    'void resetRefPicInfoState(TemporalFilterRefPicInfo* refFrame)',
    'resetRefPicInfoState(refFrame);',
    'refFrame->compensatedPic = new (std::nothrow) PicYuv;',
    'if (!refFrame->compensatedPic || !refFrame->compensatedPic->create(param, true))',
    'goto fail;',
    'return 1;',
    'fail:',
    'destroyRefPicInfo(refFrame);',
    'return 0;',
    'curFrame->compensatedPic->destroy();',
    'delete curFrame->compensatedPic;',
    'curFrame->compensatedPic = nullptr;',
    'curFrame->mvs = nullptr;',
    'curFrame->mvs0 = nullptr;',
    'curFrame->mvs1 = nullptr;',
    'curFrame->mvs2 = nullptr;',
    'curFrame->noise = nullptr;',
    'curFrame->error = nullptr;',
    'curFrame->mvsStride = 0;',
    'curFrame->mvsStride0 = 0;',
    'curFrame->mvsStride1 = 0;',
    'curFrame->mvsStride2 = 0;',
)
FORBIDDEN_SNIPPETS = (
    'refFrame->compensatedPic = new PicYuv;',
    'refFrame->compensatedPic->create(param, true);\n\n    return 1;\nfail:\n    return 0;',
)
CREATE_REGION_START = 'int TemporalFilter::createRefPicInfo(TemporalFilterRefPicInfo* refFrame, x265_param* param)'
CREATE_REGION_END = 'int MotionEstimatorTLD::motionErrorLumaSAD'
DESTROY_REGION_START = 'void TemporalFilter::destroyRefPicInfo(TemporalFilterRefPicInfo* curFrame)'
DESTROY_REGION_END = 'curFrame->mvsStride2 = 0;'


def get_region(text, start_marker, end_marker, include_end=False):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    if include_end:
        end += len(end_marker)
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    create_region = get_region(text, CREATE_REGION_START, CREATE_REGION_END)
    destroy_region = get_region(text, DESTROY_REGION_START, DESTROY_REGION_END, include_end=True)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden temporalfilter refpic rollback regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing temporalfilter refpic rollback guardrail: {snippet}'))
    if all(snippet in text for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            create_region,
            (
                'resetRefPicInfoState(refFrame);',
                'refFrame->compensatedPic = new (std::nothrow) PicYuv;',
                'if (!refFrame->compensatedPic || !refFrame->compensatedPic->create(param, true))',
                'goto fail;',
                'return 1;',
                'fail:',
                'destroyRefPicInfo(refFrame);',
                'return 0;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'TemporalFilter::createRefPicInfo must route compensatedPic failures through destroyRefPicInfo before returning 0'))
        if not has_in_order(
            destroy_region,
            (
                'if (curFrame->compensatedPic)',
                'curFrame->compensatedPic->destroy();',
                'delete curFrame->compensatedPic;',
                'curFrame->compensatedPic = nullptr;',
                'curFrame->mvs = nullptr;',
                'curFrame->mvs0 = nullptr;',
                'curFrame->mvs1 = nullptr;',
                'curFrame->mvs2 = nullptr;',
                'curFrame->noise = nullptr;',
                'curFrame->error = nullptr;',
                'curFrame->mvsStride = 0;',
                'curFrame->mvsStride0 = 0;',
                'curFrame->mvsStride1 = 0;',
                'curFrame->mvsStride2 = 0;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'TemporalFilter::destroyRefPicInfo must clear compensatedPic ownership before resetting motion and noise state'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check temporalfilter refpic rollback guardrails')
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

    print('Temporalfilter refpic rollback validated')


if __name__ == '__main__':
    main()
