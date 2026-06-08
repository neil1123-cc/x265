#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'if (!fgets(line, sizeof(line), lfn))',
    'if (ferror(lfn))',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");',
    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
    'return true;',
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
            failures.append((TARGET.as_posix(), 0, f'missing lambda-file error-state guardrail: {snippet}'))

    fgets_pos = text.find('if (!fgets(line, sizeof(line), lfn))')
    ferror_pos = text.find('if (ferror(lfn))', fgets_pos)
    close_log_pos = text.find('x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");', ferror_pos)
    read_log_pos = text.find('x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);', close_log_pos if close_log_pos != -1 else 0)
    return_pos = text.find('return true;', read_log_pos)
    incomplete_pos = text.find('if (t < 2)', return_pos)
    if -1 in (fgets_pos, ferror_pos, close_log_pos, read_log_pos, return_pos, incomplete_pos) or not (
        fgets_pos < ferror_pos < close_log_pos < read_log_pos < return_pos < incomplete_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'lambda-file parsing must handle fgets() read errors before incomplete/truncated EOF handling'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check lambda-file read error handling')
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

    print('Lambda-file error-state guard validated')


if __name__ == '__main__':
    main()
