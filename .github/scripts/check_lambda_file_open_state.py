#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'FILE *lfn = x265_fopen(param->rc.lambdaFileName, "r");',
    'else if (ferror(lfn))',
    'bool closeFailed = ferror(lfn) != 0;',
    'if (fclose(lfn))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after open failure\\n");',
    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
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
            failures.append((TARGET.as_posix(), 0, f'missing lambda file open-state guardrail: {snippet}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check lambda file open state')
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

    print('Lambda file open-state guard validated')


if __name__ == '__main__':
    main()
