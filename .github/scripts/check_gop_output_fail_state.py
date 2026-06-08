#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/gop.cpp')
REQUIRED_SNIPPETS = (
    'if (b_fail || !gop_file)',
    'if (std::fprintf(gop_file, "#headers %s.headers\\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))',
    'if (std::fprintf(gop_file, "%s\\n", data_filename.c_str()) < 0 || std::fflush(gop_file))',
    'else if (!data_file)',
    'data_file = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing GOP output fail-state guardrail: {snippet}'))

    if text.count('if (b_fail || !gop_file)') < 2:
        failures.append((TARGET.as_posix(), 0, 'GOP output must reject writes after fail-state in both header and frame writers'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check GOP output fail state')
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

    print('GOP output fail-state guard validated')


if __name__ == '__main__':
    main()
