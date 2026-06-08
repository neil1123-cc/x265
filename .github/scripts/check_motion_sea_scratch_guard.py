#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/motion.cpp')
ANCHOR = 'case X265_SEA:'
END = 'case X265_FULL_SEARCH:'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    start = text.find(ANCHOR)
    end = text.find(END, start if start != -1 else 0)
    if start == -1 or end == -1:
        return [(TARGET.as_posix(), 0, 'unable to locate SEA motion search case')]

    body = text[start:end]
    failures = []

    required = (
        'int16_t* meScratchBuffer = nullptr;',
        'if (scratchSize)',
        'meScratchBuffer = X265_MALLOC(int16_t, scratchSize);',
        'if (!meScratchBuffer)',
        'break;',
        'std::fill_n(meScratchBuffer, scratchSize, int16_t(0));',
    )
    for snippet in required:
        if snippet not in body:
            failures.append((TARGET.as_posix(), 0, f'missing SEA scratch guardrail: {snippet}'))

    alloc_pos = body.find('meScratchBuffer = X265_MALLOC(int16_t, scratchSize);')
    null_pos = body.find('if (!meScratchBuffer)', alloc_pos if alloc_pos != -1 else 0)
    break_pos = body.find('break;', null_pos if null_pos != -1 else 0)
    fill_pos = body.find('std::fill_n(meScratchBuffer, scratchSize, int16_t(0));', break_pos if break_pos != -1 else 0)
    if -1 in (alloc_pos, null_pos, break_pos, fill_pos) or not (alloc_pos < null_pos < break_pos < fill_pos):
        failures.append((TARGET.as_posix(), 0, 'SEA scratch buffer must be null-checked before zero-fill'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SEA motion scratch allocation guard')
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

    print('SEA motion scratch guard validated')


if __name__ == '__main__':
    main()
