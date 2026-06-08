#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')
REQUIRED_SNIPPETS = (
    'csvfp = x265_fopen(param->csvfn, "ab");',
    'if (csvfp && ferror(csvfp))',
    'bool closeFailed = ferror(csvfp) != 0;',
    'if (fclose(csvfp))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log((x265_param*)param, X265_LOG_WARNING, "Unable to close CSV log file <%s> after append reopen failure\\n", param->csvfn);',
    'csvfp = x265_fopen(param->csvfn, "wb");',
    'if (ferror(csvfp))',
    'x265_log((x265_param*)param, X265_LOG_WARNING, "Unable to close CSV log file <%s> after create failure\\n", param->csvfn);',
    'return nullptr;',
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
            failures.append((TARGET.as_posix(), 0, f'missing CSV log open-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CSV log open state')
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

    print('CSV log open-state guard validated')


if __name__ == '__main__':
    main()
