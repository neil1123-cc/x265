#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
BRANCH = 'if (!m_cliopt.output)'
REQUIRED_SNIPPETS = (
    BRANCH,
    'm_ret = 3;',
    'm_threadActive.store(false);',
    'm_parent->m_numActiveEncodes.decr();',
    'return;',
    'm_cliopt.output->setParam(m_param);',
    'if (m_cliopt.output->isFail())',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread output null guardrail: {snippet}'))

    fail_pos = text.rfind('if (m_cliopt.output->isFail())')
    set_param_pos = text.rfind('m_cliopt.output->setParam(m_param);', 0, fail_pos)
    branch_pos = text.rfind(BRANCH, 0, set_param_pos)
    ret_pos = text.find('m_ret = 3;', branch_pos)
    stop_pos = text.find('m_threadActive.store(false);', ret_pos)
    decr_pos = text.find('m_parent->m_numActiveEncodes.decr();', stop_pos)
    return_pos = text.find('return;', decr_pos)
    if -1 in (branch_pos, set_param_pos, ret_pos, stop_pos, decr_pos, return_pos, fail_pos) or not (branch_pos < ret_pos < stop_pos < decr_pos < return_pos < set_param_pos < fail_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain must guard null output before dereferencing it'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::threadMain output null guard')
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

    print('ABR thread output null guard validated')


if __name__ == '__main__':
    main()
