#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
BRANCH = 'if (!api)'
REQUIRED_SNIPPETS = (
    'const x265_api* api = m_cliopt.api;',
    BRANCH,
    'm_ret = 2;',
    'm_threadActive.store(false);',
    'm_parent->m_numActiveEncodes.decr();',
    'return;',
    'api->encoder_headers(m_encoder, &p_nal, &nal)',
    'api->picture_init(m_param, &picField1);',
    'api->encoder_encode(m_encoder, &p_nal, &nal, picInput, pic_recon);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread api null guardrail: {snippet}'))

    api_decl_pos = text.rfind('const x265_api* api = m_cliopt.api;')
    branch_pos = text.find(BRANCH, api_decl_pos)
    ret_pos = text.find('m_ret = 2;', branch_pos)
    stop_pos = text.find('m_threadActive.store(false);', ret_pos)
    decr_pos = text.find('m_parent->m_numActiveEncodes.decr();', stop_pos)
    return_pos = text.find('return;', decr_pos)
    headers_pos = text.find('api->encoder_headers(m_encoder, &p_nal, &nal)', return_pos)
    if -1 in (api_decl_pos, branch_pos, ret_pos, stop_pos, decr_pos, return_pos, headers_pos) or not (api_decl_pos < branch_pos < ret_pos < stop_pos < decr_pos < return_pos < headers_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain must guard null api before dereferencing it'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::threadMain api null guard')
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

    print('ABR thread api null guard validated')


if __name__ == '__main__':
    main()
