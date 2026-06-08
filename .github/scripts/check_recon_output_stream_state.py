#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/output/y4m.cpp'),
    Path('source/output/yuv.cpp'),
)
REQUIRED_SNIPPETS = {
    'source/output/y4m.cpp': (
        'if (!buf || !ofs || failed)',
        'return false;',
        'return !failed;',
    ),
    'source/output/yuv.cpp': (
        'if (!buf || !ofs || failed)',
        'return false;',
        'return !failed;',
    ),
}


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    for target in TARGETS:
        path = repo_root / target
        if not path.is_file():
            failures.append((target.as_posix(), 0, 'missing file'))
            continue

        text = path.read_text(encoding='utf-8', errors='ignore')
        for snippet in REQUIRED_SNIPPETS[target.as_posix()]:
            if snippet not in text:
                failures.append((target.as_posix(), 0, f'missing recon output stream-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check recon output stream state')
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

    print('Recon output stream-state guard validated')


if __name__ == '__main__':
    main()
