#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/gop.cpp')
REQUIRED_SNIPPETS = (
    'b_fail = true;',
    'data_file = nullptr;',
    'gop_file = nullptr;',
)
DATA_CLOSE_GUARD_SNIPPETS = (
    'if (data_file && std::fclose(data_file))',
    'bool closeFailed = std::ferror(data_file) != 0;',
)
GOP_CLOSE_GUARD_SNIPPETS = (
    'if (gop_file && std::fclose(gop_file))',
    'bool closeFailed = std::ferror(gop_file) != 0;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if not any(snippet in text for snippet in DATA_CLOSE_GUARD_SNIPPETS):
        failures.append((TARGET.as_posix(), 0, f'missing GOP close fail-state guardrail: one of {DATA_CLOSE_GUARD_SNIPPETS!r}'))
    if not any(snippet in text for snippet in GOP_CLOSE_GUARD_SNIPPETS):
        failures.append((TARGET.as_posix(), 0, f'missing GOP close fail-state guardrail: one of {GOP_CLOSE_GUARD_SNIPPETS!r}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing GOP close fail-state guardrail: {snippet}'))
    if 'std::ferror(data_file) || std::fclose(data_file)' in text or 'std::ferror(gop_file) || std::fclose(gop_file)' in text:
        failures.append((TARGET.as_posix(), 0, 'forbidden GOP close short-circuit regression'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check GOP close fail state')
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

    print('GOP close fail-state guard validated')


if __name__ == '__main__':
    main()
