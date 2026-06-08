#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    required = (
        'RPSListNode* newIdxNode = new (std::nothrow) RPSListNode();',
        'if (newIdxNode == nullptr)',
        'goto fail;',
        'delete freeIndex;',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing encoder RPS-list allocation guardrail: {snippet}'))

    forbidden = (
        'RPSListNode* newIdxNode = new RPSListNode();',
    )
    for snippet in forbidden:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden encoder RPS-list allocation regression: {snippet}'))

    alloc_pos = text.find('RPSListNode* newIdxNode = new (std::nothrow) RPSListNode();')
    guard_pos = text.find('if (newIdxNode == nullptr)', alloc_pos if alloc_pos != -1 else 0)
    goto_pos = text.find('goto fail;', guard_pos if guard_pos != -1 else 0)
    fail_pos = text.find('fail:', goto_pos if goto_pos != -1 else 0)
    delete_pos = text.find('delete freeIndex;', fail_pos if fail_pos != -1 else 0)
    if -1 in (alloc_pos, guard_pos, goto_pos, fail_pos, delete_pos) or not (alloc_pos < guard_pos < goto_pos < fail_pos < delete_pos):
        failures.append((TARGET.as_posix(), 0, 'Encoder::computeSPSRPSIndex must route RPSListNode allocation failures through fail cleanup'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check encoder RPS-list allocation guard')
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

    print('Encoder RPS-list allocation guard validated')


if __name__ == '__main__':
    main()
