#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/gop.cpp')
REQUIRED_SNIPPETS = (
    'bool closeFailed = std::ferror(data_file) != 0;',
    'if (std::fclose(data_file))',
    'bool closeFailed = std::ferror(gop_file) != 0;',
    'if (std::fclose(gop_file))',
    'b_fail = true;',
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
            failures.append((TARGET.as_posix(), 0, f'missing GOP cleanup close guardrail: {snippet}'))

    if 'std::ferror(data_file) || std::fclose(data_file)' in text or 'std::ferror(gop_file) || std::fclose(gop_file)' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden GOP cleanup short-circuit close regression'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check GOP cleanup close state')
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

    print('GOP cleanup close guard validated')


if __name__ == '__main__':
    main()
