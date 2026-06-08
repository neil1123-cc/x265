#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'm_naluFile = x265_fopen(m_param->naluFile, "r");',
    'else if (std::ferror(m_naluFile))',
    'bool closeFailed = std::ferror(m_naluFile) != 0;',
    'if (std::fclose(m_naluFile))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close user SEI file \\"%s\\" after open failure\\n", m_param->naluFile);',
    'm_naluFile = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing nalu file open-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check nalu file open state')
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

    print('Nalu file open-state guard validated')


if __name__ == '__main__':
    main()
