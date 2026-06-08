#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'this->recon[i] = ReconFile::open(',
    'if (!this->recon[i] || this->recon[i]->isFail())',
    'if (this->recon[i])',
    'this->recon[i]->release();',
    'this->recon[i] = 0;',
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI recon open guardrail: {snippet}'))

    open_pos = text.find('this->recon[i] = ReconFile::open(')
    guard_pos = text.find('if (!this->recon[i] || this->recon[i]->isFail())', open_pos)
    if -1 in (open_pos, guard_pos) or guard_pos < open_pos:
        failures.append((TARGET.as_posix(), 0, 'Recon open result must be null-checked before isFail()'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI recon open null guard')
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

    print('CLI recon open guards validated')


if __name__ == '__main__':
    main()
