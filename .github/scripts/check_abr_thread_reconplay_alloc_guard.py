#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'ReconPlay* reconPlay = nullptr;',
    'if (m_cliopt.reconPlayCmd)',
    'reconPlay = new (std::nothrow) ReconPlay(m_cliopt.reconPlayCmd, *m_param);',
    'if (!reconPlay)',
    'x265_log(m_param, X265_LOG_ERROR, "Unable to allocate recon playback helper in %s\\n",',
    'm_ret = 4;',
    'goto fail;',
)
FORBIDDEN_SNIPPETS = (
    'reconPlay = new ReconPlay(m_cliopt.reconPlayCmd, *m_param);',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR thread reconplay alloc guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ABR thread reconplay allocation pattern: {snippet}'))

    cmd_pos = text.find('if (m_cliopt.reconPlayCmd)')
    alloc_pos = text.find('reconPlay = new (std::nothrow) ReconPlay(m_cliopt.reconPlayCmd, *m_param);', cmd_pos)
    guard_pos = text.find('if (!reconPlay)', alloc_pos)
    goto_pos = text.find('goto fail;', guard_pos)
    if -1 in (cmd_pos, alloc_pos, guard_pos, goto_pos) or not (cmd_pos < alloc_pos < guard_pos < goto_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::threadMain must guard ReconPlay allocation before use'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::threadMain ReconPlay allocation guards')
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

    print('ABR thread ReconPlay allocation guards validated')


if __name__ == '__main__':
    main()
