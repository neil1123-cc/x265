#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'std::priority_queue<int64_t>* pts_queue = nullptr;',
    'pts_queue = m_cliopt.output->needPTS() ? new (std::nothrow) std::priority_queue<int64_t>() : nullptr;',
    'if (m_cliopt.output->needPTS() && !pts_queue)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate PTS queue in %s\\n",',
    'm_ret = 4;',
    'goto fail;',
)
FORBIDDEN_SNIPPETS = (
    'pts_queue = m_cliopt.output->needPTS() ? new std::priority_queue<int64_t>() : nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread PTS queue alloc guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ABR thread PTS queue allocation pattern: {snippet}'))

    declare_pos = text.find('std::priority_queue<int64_t>* pts_queue = nullptr;')
    alloc_pos = text.find('pts_queue = m_cliopt.output->needPTS() ? new (std::nothrow) std::priority_queue<int64_t>() : nullptr;', declare_pos)
    guard_pos = text.find('if (m_cliopt.output->needPTS() && !pts_queue)', alloc_pos)
    goto_pos = text.find('goto fail;', guard_pos)
    if -1 in (declare_pos, alloc_pos, guard_pos, goto_pos) or not (declare_pos < alloc_pos < guard_pos < goto_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain must guard PTS queue allocation before use'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::threadMain PTS queue allocation guard')
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

    print('ABR thread PTS queue allocation guard validated')


if __name__ == '__main__':
    main()
