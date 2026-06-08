#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/abrEncApp.cpp'),
    Path('source/common/common.cpp'),
    Path('source/common/common.h'),
    Path('source/common/cpu.cpp'),
    Path('source/common/threading.h'),
    Path('source/common/threadpool.cpp'),
    Path('source/encoder/encoder.cpp'),
    Path('source/x265.cpp'),
    Path('source/x265.h'),
    Path('source/x265cli.cpp'),
    Path('source/x265cli.h'),
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

LEGACY_TOKENS = ('NULL', 'throw()', 'volatile', 'register', 'auto_ptr')


def scan_tokens(text):
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

        matched = False
        for token in ('NULL', 'volatile', 'register', 'auto_ptr'):
            if text.startswith(token, index):
                before = text[index - 1] if index > 0 else ''
                after = text[index + len(token)] if index + len(token) < length else ''
                if (not before or not (before.isalnum() or before == '_')) and (not after or not (after.isalnum() or after == '_')):
                    yield line, token
                index += len(token)
                matched = True
                break
        if matched:
            continue

        if text.startswith('throw()', index):
            yield line, 'throw()'
            index += len('throw()')
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
        lines = text.splitlines()
        allowed_snippets = ALLOWED_LINE_SNIPPETS.get(relative_posix, ())
        for line_number, token in scan_tokens(text):
            line_text = lines[line_number - 1].strip()
            if any(snippet in line_text for snippet in allowed_snippets):
                continue
            failures.append((relative_posix, line_number, f'avoid legacy GNU++20-sensitive token in core C/C++ sources: {token}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check core C/C++ sources for legacy GNU++20-sensitive pattern regressions')
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

    print('Core source legacy patterns validated')


if __name__ == '__main__':
    main()
