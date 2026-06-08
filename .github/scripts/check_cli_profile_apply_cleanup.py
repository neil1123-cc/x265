#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
BRANCH = 'if (api->param_apply_profile(param, profile))'
LOOP = 'for (int releaseIdx = 0; releaseIdx < viewCount; releaseIdx++)'
REQUIRED_SNIPPETS = (
    BRANCH,
    LOOP,
    'if (this->input[releaseIdx])',
    'this->input[releaseIdx]->release();',
    'this->input[releaseIdx] = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI profile apply cleanup guardrail: {snippet}'))

    branch_pos = text.find(BRANCH)
    loop_pos = text.find(LOOP, branch_pos)
    release_pos = text.find('this->input[releaseIdx]->release();', loop_pos)
    return_pos = text.find('return true;', release_pos)
    if -1 in (branch_pos, loop_pos, release_pos, return_pos) or not (branch_pos < loop_pos < release_pos < return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI profile apply failure must release opened inputs before returning'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI profile apply cleanup')
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

    print('CLI profile apply cleanup validated')


if __name__ == '__main__':
    main()
