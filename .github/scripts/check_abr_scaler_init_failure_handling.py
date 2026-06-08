#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'if (!src || !dst)',
    'delete src;',
    'delete dst;',
    'x265_log(m_param, X265_LOG_ERROR, "\\n MALLOC failure in Scaler");',
    'result = 4;',
    'm_ret = 4;',
    'return -1;',
    'm_scaler = new (std::nothrow) Scaler(0, 1, m_id, src, dst, this);',
    'if (!m_scaler)',
    'else if (!m_scaler->m_initOk)',
    'm_scaler->destroy();',
    'delete m_scaler;',
    'm_scaler = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ABR scaler init failure guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR scaler init failure handling guardrails')
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

    print('ABR scaler init failure handling validated')


if __name__ == '__main__':
    main()
