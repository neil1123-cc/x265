#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'bool closeFailed = ferror(csvfp) != 0;',
    'if (fclose(csvfp))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log((x265_param*)param, X265_LOG_ERROR, "Unable to finalize existing CSV log file <%s> for append\\n", param->csvfn);',
    'return nullptr;',
    'csvfp = x265_fopen(param->csvfn, "ab");',
    'if (csvfp && ferror(csvfp))',
    'return csvfp;',
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
            failures.append((TARGET.as_posix(), 0, f'missing CSV log reopen guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CSV log reopen state')
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

    print('CSV log reopen guard validated')


if __name__ == '__main__':
    main()
