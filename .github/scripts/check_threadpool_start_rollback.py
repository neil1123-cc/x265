#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/threadpool.cpp')
REQUIRED_SNIPPETS = (
    'bool ThreadPool::start()',
    'if (!m_workers[i].start())',
    'm_isActive.store(false);',
    'for (int j = 0; j < i; j++)',
    'while (!(SLEEPBITMAP_LOAD(&m_sleepBitmap) & ((sleepbitmap_t)1 << j)))',
    'GIVE_UP_TIME();',
    'm_workers[j].awaken();',
    'm_workers[j].stop();',
    'return false;',
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
            failures.append((TARGET.as_posix(), 0, f'missing threadpool start rollback guardrail: {snippet}'))

    fail_pos = text.find('if (!m_workers[i].start())')
    rollback_pos = text.find('for (int j = 0; j < i; j++)', fail_pos)
    stop_pos = text.find('m_workers[j].stop();', rollback_pos)
    if -1 not in (fail_pos, rollback_pos, stop_pos) and not (fail_pos < rollback_pos < stop_pos):
        failures.append((TARGET.as_posix(), 0, 'ThreadPool::start should stop already-started workers before returning false'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ThreadPool::start rollback of previously started workers')
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

    print('ThreadPool start rollback validated')


if __name__ == '__main__':
    main()
