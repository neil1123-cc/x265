#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (m_cliopt.output)',
    'm_cliopt.output->closeFile(largest_pts, second_largest_pts);',
    'if (m_cliopt.output->isFail() && !m_ret)',
    'm_ret = 3;',
    'else if (!m_ret)',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread fail output guardrail: {snippet}'))

    pts_cleanup_pos = text.find('pts_queue = nullptr;')
    output_guard_pos = text.find('if (m_cliopt.output)', pts_cleanup_pos)
    close_pos = text.find('m_cliopt.output->closeFile(largest_pts, second_largest_pts);', output_guard_pos)
    fail_pos = text.find('if (m_cliopt.output->isFail() && !m_ret)', close_pos)
    else_pos = text.find('else if (!m_ret)', fail_pos)
    if -1 in (pts_cleanup_pos, output_guard_pos, close_pos, fail_pos, else_pos) or not (pts_cleanup_pos < output_guard_pos < close_pos < fail_pos < else_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain fail cleanup must guard output before closeFile/isFail'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::threadMain fail output guard')
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

    print('ABR thread fail output guard validated')


if __name__ == '__main__':
    main()
