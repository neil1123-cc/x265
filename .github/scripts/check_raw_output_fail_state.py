#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/raw.cpp')
REQUIRED_SNIPPETS = (
    'if (b_fail || !ofs)',
    'if (!ofs)',
    'bool closeFailed = false;',
    'if (ofs == stdout)',
    'closeFailed = std::fflush(ofs) || std::ferror(ofs);',
    'closeFailed = std::ferror(ofs) != 0;',
    'if (std::fclose(ofs))',
    'closeFailed = true;',
    'if (closeFailed)',
    'ofs = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing RAW output fail-state guardrail: {snippet}'))

    if text.count('if (b_fail || !ofs)') < 2:
        failures.append((TARGET.as_posix(), 0, 'RAW output must reject header and frame writes after fail-state or missing file handle'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check RAW output fail state')
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

    print('RAW output fail-state guard validated')


if __name__ == '__main__':
    main()
