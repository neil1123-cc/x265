#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/dynamicHDR10/JsonHelper.cpp'),
    Path('source/dynamicHDR10/JsonHelper.h'),
    Path('source/dynamicHDR10/metadataFromJson.cpp'),
    Path('source/dynamicHDR10/metadataFromJson.h'),
    Path('source/dynamicHDR10/SeiMetadataDictionary.cpp'),
    Path('source/dynamicHDR10/SeiMetadataDictionary.h'),
    Path('source/dynamicHDR10/BasicStructures.h'),
    Path('source/dynamicHDR10/api.cpp'),
    Path('source/dynamicHDR10/hdr10plus.h'),
    Path('source/dynamicHDR10/json11/json11.cpp'),
    Path('source/dynamicHDR10/json11/json11.h'),
)


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

        for token in ('NULL', 'volatile', 'register'):
            if text.startswith(token, index):
                before = text[index - 1] if index > 0 else ''
                after = text[index + len(token)] if index + len(token) < length else ''
                if (not before or not (before.isalnum() or before == '_')) and (not after or not (after.isalnum() or after == '_')):
                    yield line, token
                index += len(token)
                break
        else:
            if text.startswith('throw()', index):
                yield line, 'throw()'
                index += len('throw()')
                continue
            if text.startswith('auto_ptr', index):
                yield line, 'auto_ptr'
                index += len('auto_ptr')
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
        for line, token in scan_tokens(text):
            if relative_posix == 'source/dynamicHDR10/json11/json11.h' and token == 'NULL':
                continue
            failures.append((relative_posix, line, f'avoid GNU++20 legacy pattern in dynamicHDR10 sources: {token}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check dynamicHDR10 sources for GNU++20 legacy pattern regressions')
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

    print('dynamicHDR10 legacy patterns validated')


if __name__ == '__main__':
    main()
