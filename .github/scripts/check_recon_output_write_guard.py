#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/output/yuv.cpp'),
    Path('source/output/y4m.cpp'),
)
REQUIRED_SNIPPET = 'return !failed;'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    for target in TARGETS:
        path = repo_root / target
        if not path.is_file():
            failures.append((target.as_posix(), 0, 'missing file'))
            continue

        text = path.read_text(encoding='utf-8', errors='ignore')
        if REQUIRED_SNIPPET not in text:
            failures.append((target.as_posix(), 0, f'missing recon output write guardrail: {REQUIRED_SNIPPET}'))
        write_pos = text.find('bool ')
        return_pos = text.find(REQUIRED_SNIPPET, write_pos)
        if write_pos == -1 or return_pos == -1:
            failures.append((target.as_posix(), 0, 'writePicture must return accumulated failure state instead of unconditional success'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check recon output write guard')
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

    print('Recon output write guard validated')


if __name__ == '__main__':
    main()
