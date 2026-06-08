#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
BRANCH = 'if (!m_cliopt.api)'
REQUIRED_SNIPPETS = (
    BRANCH,
    'rollbackInputHelper();',
    'm_ret = 2;',
    'if (!result)',
    'result = m_ret;',
    'return -1;',
    'm_encoder = m_cliopt.api->encoder_open(m_param);',
    'm_cliopt.api->encoder_parameters(m_encoder, m_param);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR init api null guardrail: {snippet}'))

    branch_pos = text.find(BRANCH)
    rollback_pos = text.find('rollbackInputHelper();', branch_pos)
    ret_pos = text.find('m_ret = 2;', rollback_pos)
    result_pos = text.find('result = m_ret;', ret_pos)
    return_pos = text.find('return -1;', result_pos)
    open_pos = text.find('m_encoder = m_cliopt.api->encoder_open(m_param);', return_pos)
    params_pos = text.find('m_cliopt.api->encoder_parameters(m_encoder, m_param);', open_pos)
    if -1 in (branch_pos, rollback_pos, ret_pos, result_pos, return_pos, open_pos, params_pos) or not (branch_pos < rollback_pos < ret_pos < result_pos < return_pos < open_pos < params_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::init must guard null api before encoder_open/encoder_parameters'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::init api null guard')
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

    print('ABR init api null guard validated')


if __name__ == '__main__':
    main()
