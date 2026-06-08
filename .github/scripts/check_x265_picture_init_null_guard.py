#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
BRANCH = 'if (!param || !pic)'
REQUIRED_SNIPPETS = (
    'void x265_picture_init(x265_param *param, x265_picture *pic)',
    BRANCH,
    'x265_log(nullptr, X265_LOG_ERROR, "x265_picture_init requires non-null param and picture\\n");',
    'return;',
    'std::fill_n(reinterpret_cast<uint8_t*>(pic), sizeof(x265_picture), uint8_t(0));',
    'pic->bitDepth = param->internalBitDepth;',
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
            failures.append((TARGET.as_posix(), 0, f'missing x265_picture_init null guardrail: {snippet}'))

    branch_pos = text.find(BRANCH)
    log_pos = text.find('x265_log(nullptr, X265_LOG_ERROR, "x265_picture_init requires non-null param and picture\\n");', branch_pos if branch_pos != -1 else 0)
    return_pos = text.find('return;', log_pos if log_pos != -1 else 0)
    fill_pos = text.find('std::fill_n(reinterpret_cast<uint8_t*>(pic), sizeof(x265_picture), uint8_t(0));', return_pos if return_pos != -1 else 0)
    bitdepth_pos = text.find('pic->bitDepth = param->internalBitDepth;', fill_pos if fill_pos != -1 else 0)
    if -1 in (branch_pos, log_pos, return_pos, fill_pos, bitdepth_pos) or not (branch_pos < log_pos < return_pos < fill_pos < bitdepth_pos):
        failures.append((TARGET.as_posix(), 0, 'x265_picture_init must guard null param/pic before clearing or dereferencing picture state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_picture_init null guard')
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

    print('x265_picture_init null guard validated')


if __name__ == '__main__':
    main()
