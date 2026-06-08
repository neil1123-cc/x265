#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'this->output = OutputFile::open(outputfn, info[0]);',
    'if (!this->output || this->output->isFail())',
    'if (this->output)',
    'this->output->release();',
    'this->output = nullptr;',
    'return true;',
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI output open cleanup guardrail: {snippet}'))

    fail_pos = text.find('if (!this->output || this->output->isFail())')
    branch_pos = text.find('if (this->output)', fail_pos)
    release_pos = text.find('this->output->release();', branch_pos)
    null_pos = text.find('this->output = nullptr;', release_pos)
    return_pos = text.find('return true;', null_pos)
    if -1 in (fail_pos, branch_pos, release_pos, null_pos, return_pos) or not (fail_pos < branch_pos < release_pos < null_pos < return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI output open failure must null-guard, then release and null output before returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI output open failure cleanup')
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

    print('CLI output open cleanup validated')


if __name__ == '__main__':
    main()
