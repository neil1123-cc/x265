#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/raw.cpp')
REQUIRED_SNIPPETS = (
    'ofs = x265_fopen(fname, "wb");',
    'if (!ofs)',
    'b_fail = true;',
    'else if (std::ferror(ofs))',
    'bool closeFailed = std::ferror(ofs) != 0;',
    'if (std::fclose(ofs))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(nullptr, X265_LOG_WARNING, "raw: unable to close output file after open failure\\n");',
    'ofs = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing raw open cleanup-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check RAW open cleanup state')
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

    print('RAW open cleanup-state guard validated')


if __name__ == '__main__':
    main()
