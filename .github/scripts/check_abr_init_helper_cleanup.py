#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'auto rollbackInputHelper = [&]()',
    'if (m_reader)',
    'delete m_reader;',
    'm_reader = nullptr;',
    'else if (m_scaler)',
    'm_scaler->destroy();',
    'delete m_scaler;',
    'm_scaler = nullptr;',
    'if (!m_cliopt.parseZoneFile())',
    'rollbackInputHelper();',
    'if (i->isFail())',
    'if (m_cliopt.output->isFail())',
    'if (!m_encoder)',
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
            failures.append((TARGET.as_posix(), 0, f'missing abr init helper cleanup guardrail: {snippet}'))

    for anchor in ('if (!m_cliopt.parseZoneFile())', 'if (i->isFail())', 'if (m_cliopt.output->isFail())', 'if (!m_encoder)'):
        anchor_pos = text.find(anchor)
        cleanup_pos = text.find('rollbackInputHelper();', anchor_pos)
        if anchor_pos == -1 or cleanup_pos == -1 or cleanup_pos < anchor_pos:
            failures.append((TARGET.as_posix(), 0, f'PassEncoder::init must call rollbackInputHelper() before returning from {anchor}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::init helper cleanup on late failure paths')
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

    print('Abr init helper cleanup validated')


if __name__ == '__main__':
    main()
