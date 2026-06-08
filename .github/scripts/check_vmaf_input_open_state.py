#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'vmafData->reference_file = x265_fopen(inputfn[0], "rb");',
    'vmafData->distorted_file = x265_fopen(reconfn[0], "rb");',
    'if (!vmafData->reference_file || !vmafData->distorted_file ||',
    'ferror(vmafData->reference_file) || ferror(vmafData->distorted_file))',
    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after open failure");',
    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after open failure");',
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
            failures.append((TARGET.as_posix(), 0, f'missing VMAF input open-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF input open state')
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

    print('VMAF input open-state guard validated')


if __name__ == '__main__':
    main()
