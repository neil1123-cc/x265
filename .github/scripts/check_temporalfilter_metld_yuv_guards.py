#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/temporalfilter.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    required = (
        'inline bool hasMotionEstimatorTLDBuffers(const MotionEstimatorTLD* metld)',
        'return metld && metld->me.fencPUYuv.m_buf[0] && metld->predPUYuv.m_buf[0];',
        'm_metld = new (std::nothrow) MotionEstimatorTLD;',
        'if (!hasMotionEstimatorTLDBuffers(m_metld))',
        'delete m_metld;',
        'm_metld = nullptr;',
        'return false;',
        'return true;',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing temporalfilter metld YUV guardrail: {snippet}'))

    forbidden = 'return m_metld != nullptr;'
    if forbidden in text:
        failures.append((TARGET.as_posix(), 0, f'forbidden temporalfilter metld YUV regression: {forbidden}'))

    init_pos = text.find('bool TemporalFilter::init(const x265_param* param)')
    alloc_pos = text.find('m_metld = new (std::nothrow) MotionEstimatorTLD;', init_pos if init_pos != -1 else 0)
    guard_pos = text.find('if (!hasMotionEstimatorTLDBuffers(m_metld))', alloc_pos if alloc_pos != -1 else 0)
    delete_pos = text.find('delete m_metld;', guard_pos if guard_pos != -1 else 0)
    null_pos = text.find('m_metld = nullptr;', delete_pos if delete_pos != -1 else 0)
    return_false_pos = text.find('return false;', null_pos if null_pos != -1 else 0)
    return_true_pos = text.find('return true;', return_false_pos if return_false_pos != -1 else 0)
    if -1 in (init_pos, alloc_pos, guard_pos, delete_pos, null_pos, return_false_pos, return_true_pos) or not (
        init_pos < alloc_pos < guard_pos < delete_pos < null_pos < return_false_pos < return_true_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'TemporalFilter::init must validate MotionEstimatorTLD YUV buffers before returning success and roll back m_metld on failure'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check TemporalFilter MotionEstimatorTLD YUV guards')
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

    print('TemporalFilter MotionEstimatorTLD YUV guards validated')


if __name__ == '__main__':
    main()
