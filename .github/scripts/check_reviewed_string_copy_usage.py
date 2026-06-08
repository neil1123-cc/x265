#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/abrEncApp.cpp'),
    Path('source/common/common.h'),
    Path('source/encoder/encoder.cpp'),
    Path('source/encoder/slicetype.cpp'),
    Path('source/encoder/ratecontrol.cpp'),
    Path('source/input/avs.h'),
    Path('source/input/vpy.cpp'),
    Path('source/x265cli.cpp'),
    Path('source/common/param.cpp'),
    Path('source/encoder/level.cpp'),
)


def find_string_copy_tokens(text):
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

        if text.startswith('std::strcpy(', index):
            yield line, 'std::strcpy'
            index += 12
            continue

        if text.startswith('std::strcat(', index):
            yield line, 'std::strcat'
            index += 12
            continue

        if text.startswith('std::strncpy(', index):
            yield line, 'std::strncpy'
            index += 13
            continue

        if text.startswith('strcpy(', index):
            before = text[index - 1] if index > 0 else ''
            if not before or not (before.isalnum() or before == '_'):
                yield line, 'strcpy'
            index += 7
            continue

        if text.startswith('strcat(', index):
            before = text[index - 1] if index > 0 else ''
            if not before or not (before.isalnum() or before == '_'):
                yield line, 'strcat'
            index += 7
            continue

        if text.startswith('strncpy(', index):
            before = text[index - 1] if index > 0 else ''
            if not before or not (before.isalnum() or before == '_'):
                yield line, 'strncpy'
            index += 8
            continue

        index += 1


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    for relative_path in TARGETS:
        path = repo_root / relative_path
        if not path.is_file():
            failures.append((relative_path.as_posix(), 0, 'missing file'))
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        for line, token in find_string_copy_tokens(text):
            failures.append((relative_path.as_posix(), line, f'avoid reviewed legacy string copy helper {token} in this path'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed source paths for strcpy/strcat regressions')
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

    print('Reviewed string copy usage validated')


if __name__ == '__main__':
    main()
