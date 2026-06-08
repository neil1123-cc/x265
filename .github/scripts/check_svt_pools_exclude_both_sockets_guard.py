#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'else if (!strcmp(temp2, "-"))',
    'x265_log(param, X265_LOG_ERROR, "Shouldn\'t exclude both sockets for pools option %s \\n", pools);',
    'bError = true;',
)
FORBIDDEN_SNIPPET = 'else if (!strcmp(temp2, "-")) x265_log(param, X265_LOG_ERROR, "Shouldn\'t exclude both sockets for pools option %s \\n", pools);'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if FORBIDDEN_SNIPPET in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden SVT pools exclude-both-sockets regression: invalid pools input must surface a parse error'))
        return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing SVT pools exclude-both-sockets guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT pools exclude-both-sockets guardrail')
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

    print('SVT pools exclude-both-sockets guard validated')


if __name__ == '__main__':
    main()
