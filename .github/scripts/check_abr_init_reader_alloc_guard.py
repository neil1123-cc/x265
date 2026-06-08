#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (!(m_cliopt.enableScaler && m_id))',
    'm_reader = new (std::nothrow) Reader(m_id, this);',
    'if (!m_reader)',
    'x265_log(m_param, X265_LOG_ERROR, "\\n MALLOC failure in Reader");',
    'result = 4;',
    'm_ret = 4;',
    'return -1;',
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
            failures.append((TARGET.as_posix(), 0, f'missing abr init reader alloc guardrail: {snippet}'))

    alloc_pos = text.find('m_reader = new (std::nothrow) Reader(m_id, this);')
    guard_pos = text.find('if (!m_reader)', alloc_pos)
    if -1 not in (alloc_pos, guard_pos) and not (alloc_pos < guard_pos):
        failures.append((TARGET.as_posix(), 0, 'PassEncoder::init must guard Reader allocation immediately after construction'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check PassEncoder::init Reader allocation guards')
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

    print('Abr init reader allocation guards validated')


if __name__ == '__main__':
    main()
