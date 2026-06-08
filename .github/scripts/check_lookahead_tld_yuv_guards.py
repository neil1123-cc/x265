#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/slicetype.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    required = (
        'inline bool hasLookaheadTLDYuvBuffers(LookaheadTLD* tld, int numTLD)',
        'if (!tld[i].me.fencPUYuv.m_buf[0])',
        'inline bool hasMotionEstimatorTLDYuvBuffers(MotionEstimatorTLD* metld, int numTLD)',
        'if (!metld[i].me.fencPUYuv.m_buf[0] || !metld[i].predPUYuv.m_buf[0])',
        'LookaheadTLD* tld = new (std::nothrow) LookaheadTLD[numTLD];',
        'int* scratch = nullptr;',
        'MotionEstimatorTLD* metld = nullptr;',
        'OrigPicBuffer* origPicBuf = nullptr;',
        'if (!hasLookaheadTLDYuvBuffers(tld, numTLD))',
        'if (!hasMotionEstimatorTLDYuvBuffers(metld, numTLD))',
        'm_tld = tld;',
        'm_scratch = scratch;',
        'm_metld = metld;',
        'm_origPicBuf = origPicBuf;',
        'delete[] metld;',
        'delete[] tld;',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing lookahead TLD YUV guardrail: {snippet}'))

    forbidden = (
        'm_tld = new (std::nothrow) LookaheadTLD[numTLD];',
        'm_metld = new (std::nothrow) MotionEstimatorTLD[numTLD];',
        'return m_tld && m_scratch;',
    )
    for snippet in forbidden:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden lookahead TLD YUV regression: {snippet}'))

    tld_alloc_pos = text.find('LookaheadTLD* tld = new (std::nothrow) LookaheadTLD[numTLD];')
    tld_guard_pos = text.find('if (!hasLookaheadTLDYuvBuffers(tld, numTLD))', tld_alloc_pos if tld_alloc_pos != -1 else 0)
    scratch_pos = text.find('scratch = X265_MALLOC(int, tld[0].widthInCU);', tld_guard_pos if tld_guard_pos != -1 else 0)
    metld_alloc_pos = text.find('metld = new (std::nothrow) MotionEstimatorTLD[numTLD];', scratch_pos if scratch_pos != -1 else 0)
    metld_guard_pos = text.find('if (!hasMotionEstimatorTLDYuvBuffers(metld, numTLD))', metld_alloc_pos if metld_alloc_pos != -1 else 0)
    publish_tld_pos = text.find('m_tld = tld;', metld_guard_pos if metld_guard_pos != -1 else 0)
    publish_orig_pos = text.find('m_origPicBuf = origPicBuf;', publish_tld_pos if publish_tld_pos != -1 else 0)
    fail_pos = text.find('fail:', publish_orig_pos if publish_orig_pos != -1 else 0)
    delete_orig_pos = text.find('delete origPicBuf;', fail_pos if fail_pos != -1 else 0)
    delete_metld_pos = text.find('delete[] metld;', delete_orig_pos if delete_orig_pos != -1 else 0)
    free_scratch_pos = text.find('X265_FREE(scratch);', delete_metld_pos if delete_metld_pos != -1 else 0)
    delete_tld_pos = text.find('delete[] tld;', free_scratch_pos if free_scratch_pos != -1 else 0)
    if -1 in (
        tld_alloc_pos, tld_guard_pos, scratch_pos, metld_alloc_pos,
        metld_guard_pos, publish_tld_pos, publish_orig_pos, fail_pos,
        delete_orig_pos, delete_metld_pos, free_scratch_pos, delete_tld_pos,
    ) or not (
        tld_alloc_pos < tld_guard_pos < scratch_pos < metld_alloc_pos <
        metld_guard_pos < publish_tld_pos < publish_orig_pos < fail_pos <
        delete_orig_pos < delete_metld_pos < free_scratch_pos < delete_tld_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Lookahead::create must validate TLD YUV buffers before publishing members and roll back staged allocations on failure'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Lookahead TLD YUV guards')
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

    print('Lookahead TLD YUV guards validated')


if __name__ == '__main__':
    main()
