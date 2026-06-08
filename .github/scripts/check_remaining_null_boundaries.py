#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGETS = (
    Path('source/x265.h'),
    Path('source/common/threadpool.cpp'),
    Path('source/compat/getopt/getopt.c'),
    Path('source/compat/getopt/getopt.h'),
)

COMPAT_GETOPT_ALLOWLIST = {
    'source/compat/getopt/getopt.c': {
        321, 395, 411, 417, 422, 433, 521, 543, 617, 635, 641, 664, 689, 737, 752,
        782, 802, 855, 874, 909, 918, 932, 933, 964,
    },
    'source/compat/getopt/getopt.h': set(),
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
    for relative_path in TARGETS:
        path = repo_root / relative_path
        relative_posix = relative_path.as_posix()
        if not path.is_file():
            failures.append((relative_posix, 0, 'missing file'))
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        null_lines = tuple(find_null_tokens(text))
        if relative_posix == 'source/x265.h' and null_lines:
            failures.append((relative_posix, null_lines[0], 'remove runtime NULL tokens from public header implementations'))
            continue
        if relative_posix == 'source/common/threadpool.cpp' and null_lines:
            failures.append((relative_posix, null_lines[0], 'threadpool NULL handling should stay string-only, not token-based'))
            continue
        if relative_posix in COMPAT_GETOPT_ALLOWLIST:
            allowed_lines = COMPAT_GETOPT_ALLOWLIST[relative_posix]
            for line in null_lines:
                if line not in allowed_lines:
                    failures.append((relative_posix, line, 'compat getopt NULL boundary changed; review C compatibility island explicitly'))
            missing = sorted(allowed_lines.difference(null_lines))
            for line in missing:
                failures.append((relative_posix, line, 'compat getopt NULL boundary drifted; update allowlist only after review'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed remaining NULL boundaries')
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

    print('Remaining NULL boundaries validated')


if __name__ == '__main__':
    main()
