#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/ratecontrol.cpp')
REQUIRED_SNIPPETS = (
    'm_cutreeStatFileIn = x265_fopen(tmpFile, "rb");',
    'else if (ferror(m_cutreeStatFileIn))',
    'bool closeFailed = ferror(m_cutreeStatFileIn) != 0;',
    'if (fclose(m_cutreeStatFileIn))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree input stats file \\"%s.cutree\\" after open failure\\n", fileName);',
    'm_cutreeStatFileIn = nullptr;',
    'm_statFileOut = x265_fopen(statFileTmpname, "wb");',
    'else if (ferror(m_statFileOut))',
    'bool closeFailed = ferror(m_statFileOut) != 0;',
    'if (fclose(m_statFileOut))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close output stats file \\"%s.temp\\" after open failure\\n", fileName);',
    'm_statFileOut = nullptr;',
    'm_cutreeStatFileOut = x265_fopen(statFileTmpname, "wb");',
    'else if (ferror(m_cutreeStatFileOut))',
    'bool closeFailed = ferror(m_cutreeStatFileOut) != 0;',
    'if (fclose(m_cutreeStatFileOut))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(m_param, X265_LOG_WARNING, "failed to close cutree output stats file \\"%s.cutree.temp\\" after open failure\\n", fileName);',
    'm_cutreeStatFileOut = nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol stats open-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ratecontrol stats open state')
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

    print('Ratecontrol stats open-state guard validated')


if __name__ == '__main__':
    main()
