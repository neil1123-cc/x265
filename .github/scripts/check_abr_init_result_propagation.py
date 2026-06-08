#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
ANCHORS = (
    ('if (!m_cliopt.parseZoneFile())', 'm_ret = 1;'),
    ('if (i->isFail())', 'm_ret = 4;'),
    ('if (m_cliopt.output->isFail())', 'm_ret = 3;'),
    ('if (!m_encoder)', 'm_ret = 2;'),
)
REQUIRED_SNIPPETS = (
    'if (!result)',
    'result = m_ret;',
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
            failures.append((TARGET.as_posix(), 0, f'missing abr init result propagation guardrail: {snippet}'))

    for anchor, ret_assign in ANCHORS:
        anchor_pos = text.find(anchor)
        ret_pos = text.find(ret_assign, anchor_pos)
        result_guard_pos = text.find('if (!result)', ret_pos)
        result_assign_pos = text.find('result = m_ret;', result_guard_pos)
        return_pos = text.find('return -1;', result_assign_pos)
        if -1 in (anchor_pos, ret_pos, result_guard_pos, result_assign_pos, return_pos) or not (anchor_pos < ret_pos < result_guard_pos < result_assign_pos < return_pos):
            failures.append((TARGET.as_posix(), 0, f'PassEncoder::init must propagate result on late failure path {anchor}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::init late failure result propagation')
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

    print('Abr init result propagation validated')


if __name__ == '__main__':
    main()
