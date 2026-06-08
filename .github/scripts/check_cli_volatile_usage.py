#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/abrEncApp.cpp'),
    Path('source/common/cpu.cpp'),
    Path('source/common/threading.h'),
)

ALLOWED_LINE_SNIPPETS = {
    'source/abrEncApp.cpp': (
        'static volatile sig_atomic_t b_ctrl_c',
    ),
    'source/common/cpu.cpp': (
        'static volatile sig_atomic_t canjump = 0;',
    ),
    'source/common/threading.h': (
        'InterlockedIncrement((volatile LONG*)ptr)',
        'InterlockedDecrement((volatile LONG*)ptr)',
        'InterlockedExchangeAdd64((volatile LONGLONG*)ptr, (LONGLONG)(val))',
        'InterlockedExchangeAdd((volatile LONG*)ptr, (LONG)(val))',
        '_InterlockedOr((volatile LONG*)ptr, (LONG)mask)',
        '_InterlockedAnd((volatile LONG*)ptr, (LONG)mask)',
    ),
}


def find_volatile_tokens(text):
    line = 1
    index = 0
    length = len(text)
    in_line_comment = False
    in_block_comment = False
    in_single_quote = False
    in_double_quote = False
    escaped = False

    while index < length:
        char = text[index]
        nxt = text[index + 1] if index + 1 < length else ''

        if char == '\n':
            line += 1
            in_line_comment = False
            escaped = False
            index += 1
            continue

        if in_line_comment:
            index += 1
            continue

        if in_block_comment:
            if char == '*' and nxt == '/':
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if in_single_quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == "'":
                in_single_quote = False
            index += 1
            continue

        if in_double_quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_double_quote = False
            index += 1
            continue

        if char == '/' and nxt == '/':
            in_line_comment = True
            index += 2
            continue

        if char == '/' and nxt == '*':
            in_block_comment = True
            index += 2
            continue

        if char == "'":
            in_single_quote = True
            index += 1
            continue

        if char == '"':
            in_double_quote = True
            index += 1
            continue

        if text.startswith('volatile', index):
            before = text[index - 1] if index > 0 else ''
            after = text[index + 8] if index + 8 < length else ''
            if (not before or not (before.isalnum() or before == '_')) and (not after or not (after.isalnum() or after == '_')):
                yield line
            index += 8
            continue

        index += 1


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    for relative_path in TARGETS:
        path = repo_root / relative_path
        relative_posix = relative_path.as_posix()
        if not path.is_file():
            failures.append((relative_posix, 0, 'missing file'))
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        allowed_snippets = ALLOWED_LINE_SNIPPETS[relative_posix]
        lines = text.splitlines()
        for line_number in find_volatile_tokens(text):
            line_text = lines[line_number - 1].strip()
            if not any(snippet in line_text for snippet in allowed_snippets):
                failures.append(
                    (
                        relative_posix,
                        line_number,
                        'limit volatile usage to reviewed GNU++20 signal-handler and Windows API boundary sites',
                    )
                )
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI entrypoint C++ sources for volatile regressions')
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

    print('CLI volatile guard validated')


if __name__ == '__main__':
    main()
