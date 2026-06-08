#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/mkv.cpp')
REQUIRED_SNIPPETS = (
    'ret = mk_write_header(p_mkv->w, writingApp, "V_MPEGH/ISO/HEVC",',
    'if (ret < 0)',
    'if (mk_close(p_mkv->w, 0) < 0)',
    'ERR("Unable to clean up MKV writer after header failure\\n");',
    'p_mkv->w = nullptr;',
    'b_fail = true;',
    'return ret;',
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
            failures.append((TARGET.as_posix(), 0, f'missing MKV header cleanup-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MKV header cleanup state')
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

    print('MKV header cleanup-state guard validated')


if __name__ == '__main__':
    main()
