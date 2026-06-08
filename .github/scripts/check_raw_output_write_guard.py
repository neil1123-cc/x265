#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/raw.cpp')
REQUIRED_SNIPPETS = (
    'size_t written = std::fwrite((const void*)nal->payload, 1, nal->sizeBytes, ofs);',
    'if (written != nal->sizeBytes || std::ferror(ofs))',
    'b_fail = true;',
    'return -1;',
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
            failures.append((TARGET.as_posix(), 0, f'missing RAW output write guardrail: {snippet}'))

    write_count = text.count('size_t written = std::fwrite((const void*)nal->payload, 1, nal->sizeBytes, ofs);')
    guard_count = text.count('if (written != nal->sizeBytes || std::ferror(ofs))')
    if write_count < 2 or guard_count < 2:
        failures.append((TARGET.as_posix(), 0, 'RAW output must guard fwrite results in both header and frame writers'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check RAW output write guard')
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

    print('RAW output write guard validated')


if __name__ == '__main__':
    main()
