#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'm_filmGrainIn = x265_fopen(m_param->filmGrain, "rb");',
    'else if (std::ferror(m_filmGrainIn))',
    'bool closeFailed = std::ferror(m_filmGrainIn) != 0;',
    'if (std::fclose(m_filmGrainIn))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close film grain file \\"%s\\" after open failure\\n", m_param->filmGrain);',
    'm_filmGrainIn = nullptr;',
    'm_aomFilmGrainIn = x265_fopen(m_param->aomFilmGrain, "rb");',
    'else if (std::ferror(m_aomFilmGrainIn))',
    'bool closeFailed = std::ferror(m_aomFilmGrainIn) != 0;',
    'if (std::fclose(m_aomFilmGrainIn))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(nullptr, X265_LOG_WARNING, "failed to close AOM film grain file \\"%s\\" after open failure\\n", m_param->aomFilmGrain);',
    'm_aomFilmGrainIn = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing film grain open-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check film grain open state')
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

    print('Film grain open-state guard validated')


if __name__ == '__main__':
    main()
