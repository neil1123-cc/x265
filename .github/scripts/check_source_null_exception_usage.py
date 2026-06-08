#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/common/threadpool.cpp'),
)

ALLOWED_LINE_SNIPPETS = {
    'source/common/threadpool.cpp': (
        'std::strcmp(p->numaPools, "NULL") == 0',
        '!strcasecmp(nodeStr, "NULL")',
    ),
}


def find_null_tokens(text):
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

        if text.startswith('NULL', index):
            before = text[index - 1] if index > 0 else ''
            after = text[index + 4] if index + 4 < length else ''
            if (not before or not (before.isalnum() or before == '_')) and (not after or not (after.isalnum() or after == '_')):
                yield line
            index += 4
            continue

        index += 1


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    common_header = repo_root / 'source/common/common.h'
    if not common_header.is_file():
        failures.append(('source/common/common.h', 0, 'missing file'))
    else:
        common_text = common_header.read_text(encoding='utf-8', errors='ignore')
        for token in ('#ifndef NULL', '#define NULL 0'):
            if token in common_text:
                failures.append(('source/common/common.h', 0, f'remove legacy internal NULL macro from common header: {token}'))

    for relative_path in TARGETS:
        path = repo_root / relative_path
        relative_posix = relative_path.as_posix()
        if not path.is_file():
            failures.append((relative_posix, 0, 'missing file'))
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        allowed_snippets = ALLOWED_LINE_SNIPPETS[relative_posix]
        lines = text.splitlines()
        for line_number in find_null_tokens(text):
            line_text = lines[line_number - 1].strip()
            if not any(snippet in line_text for snippet in allowed_snippets):
                failures.append(
                    (
                        relative_posix,
                        line_number,
                        'limit remaining NULL usage to reviewed compatibility macro and string-token exception sites',
                    )
                )
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check remaining reviewed NULL exception sites')
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

    print('Source NULL exception guard validated')


if __name__ == '__main__':
    main()
