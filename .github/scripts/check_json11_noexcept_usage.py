#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/dynamicHDR10/json11/json11.h'),
    Path('source/dynamicHDR10/json11/json11.cpp'),
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []

    header = repo_root / TARGETS[0]
    source = repo_root / TARGETS[1]

    if not header.is_file():
        failures.append((TARGETS[0].as_posix(), 0, 'missing file'))
        return failures
    if not source.is_file():
        failures.append((TARGETS[1].as_posix(), 0, 'missing file'))
        return failures

    header_text = header.read_text(encoding='utf-8', errors='ignore')
    source_text = source.read_text(encoding='utf-8', errors='ignore')

    forbidden_header_tokens = (
        '#define noexcept throw()',
        '#ifndef noexcept',
        '#define JSON11_NOEXCEPT',
        '_MSC_VER <= 1800',
    )
    for token in forbidden_header_tokens:
        if token in header_text:
            failures.append((TARGETS[0].as_posix(), 0, f'avoid redefining noexcept directly in json11 compatibility layer: {token}'))

    required_header_tokens = (
        'Json() noexcept;',
        'Json(std::nullptr_t) noexcept;',
    )
    for token in required_header_tokens:
        if token not in header_text:
            failures.append((TARGETS[0].as_posix(), 0, f'missing json11 noexcept compatibility token: {token}'))

    if 'throw()' in header_text:
        failures.append((TARGETS[0].as_posix(), 0, 'avoid old-style throw() exception specifications in json11 header'))
    if 'throw()' in source_text:
        failures.append((TARGETS[1].as_posix(), 0, 'avoid old-style throw() exception specifications in json11 source'))

    required_source_tokens = (
        'Json::Json() noexcept',
        'Json::Json(std::nullptr_t) noexcept',
    )
    for token in required_source_tokens:
        if token not in source_text:
            failures.append((TARGETS[1].as_posix(), 0, f'missing json11 noexcept compatibility token: {token}'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check json11 noexcept compatibility usage')
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

    print('json11 noexcept guard validated')


if __name__ == '__main__':
    main()
