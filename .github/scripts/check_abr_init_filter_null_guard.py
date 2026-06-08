#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
ANCHOR = 'for (auto &&i : m_cliopt.filters)'
BRANCH = 'if (!i)'
REQUIRED_SNIPPETS = (
    ANCHOR,
    BRANCH,
    'rollbackInputHelper();',
    'm_ret = 4;',
    'if (!result)',
    'result = m_ret;',
    'return -1;',
    'i->setParam(m_param);',
    'if (i->isFail())',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR init filter null guardrail: {snippet}'))

    loop_pos = text.find(ANCHOR)
    branch_pos = text.find(BRANCH, loop_pos)
    rollback_pos = text.find('rollbackInputHelper();', branch_pos)
    ret_pos = text.find('m_ret = 4;', rollback_pos)
    result_pos = text.find('result = m_ret;', ret_pos)
    return_pos = text.find('return -1;', result_pos)
    set_param_pos = text.find('i->setParam(m_param);', return_pos)
    fail_pos = text.find('if (i->isFail())', set_param_pos)
    if -1 in (loop_pos, branch_pos, rollback_pos, ret_pos, result_pos, return_pos, set_param_pos, fail_pos) or not (loop_pos < branch_pos < rollback_pos < ret_pos < result_pos < return_pos < set_param_pos < fail_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::init must guard null filters before dereferencing them'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::init filter null guard')
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

    print('ABR init filter null guard validated')


if __name__ == '__main__':
    main()
