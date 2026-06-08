#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/gop.cpp')
REQUIRED_SNIPPETS = (
    'if (b_fail || !gop_file)',
    'if (std::fprintf(gop_file, "#options %s.options\\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))',
    'bool closeFailed = std::ferror(opt_file) != 0;',
    'if (std::fclose(opt_file))',
    'closeFailed = true;',
    'if (closeFailed)',
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
            failures.append((TARGET.as_posix(), 0, f'missing GOP options fail-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check GOP options fail state')
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

    print('GOP options fail-state guard validated')


if __name__ == '__main__':
    main()
