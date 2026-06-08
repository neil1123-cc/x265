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
        'int* scratch = nullptr;',
        'MotionEstimatorTLD* metld = nullptr;',
        'OrigPicBuffer* origPicBuf = nullptr;',
        'if (!scratch)',
        'goto fail;',
        'if (!metld)',
        'if (!origPicBuf)',
        'fail:',
        'delete origPicBuf;',
        'delete[] metld;',
        'X265_FREE(scratch);',
        'delete[] tld;',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing lookahead create rollback guardrail: {snippet}'))

    scratch_guard_pos = text.find('if (!scratch)')
    scratch_goto_pos = text.find('goto fail;', scratch_guard_pos if scratch_guard_pos != -1 else 0)
    metld_guard_pos = text.find('if (!metld)', scratch_goto_pos if scratch_goto_pos != -1 else 0)
    metld_goto_pos = text.find('goto fail;', metld_guard_pos if metld_guard_pos != -1 else 0)
    orig_guard_pos = text.find('if (!origPicBuf)', metld_goto_pos if metld_goto_pos != -1 else 0)
    orig_goto_pos = text.find('goto fail;', orig_guard_pos if orig_guard_pos != -1 else 0)
    fail_pos = text.find('fail:', orig_goto_pos if orig_goto_pos != -1 else 0)
    delete_orig_pos = text.find('delete origPicBuf;', fail_pos if fail_pos != -1 else 0)
    delete_metld_pos = text.find('delete[] metld;', delete_orig_pos if delete_orig_pos != -1 else 0)
    free_scratch_pos = text.find('X265_FREE(scratch);', delete_metld_pos if delete_metld_pos != -1 else 0)
    delete_tld_pos = text.find('delete[] tld;', free_scratch_pos if free_scratch_pos != -1 else 0)
    if -1 in (
        scratch_guard_pos, scratch_goto_pos, metld_guard_pos, metld_goto_pos,
        orig_guard_pos, orig_goto_pos, fail_pos, delete_orig_pos,
        delete_metld_pos, free_scratch_pos, delete_tld_pos,
    ) or not (
        scratch_guard_pos < scratch_goto_pos < metld_guard_pos < metld_goto_pos <
        orig_guard_pos < orig_goto_pos < fail_pos < delete_orig_pos <
        delete_metld_pos < free_scratch_pos < delete_tld_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'Lookahead::create must roll back scratch, motion-estimator, orig-pic, and TLD allocations before returning false'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Lookahead::create rollback')
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

    print('Lookahead create rollback validated')


if __name__ == '__main__':
    main()
