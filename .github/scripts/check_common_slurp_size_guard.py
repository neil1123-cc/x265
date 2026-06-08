#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/common.cpp')


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    func_text = extract_braced_block(text, 'char* x265_slurp_file(const char *filename)')
    if not func_text:
        return [(TARGET.as_posix(), 0, 'missing x265_slurp_file function')]

    failures = []
    snippets = (
        'size_t fSize = 0;',
        'long fileSize = 0;',
        'fileSize = std::ftell(fh);',
        'bError |= fileSize <= 0;',
        'bError |= (uint64_t)fileSize > (uint64_t)SIZE_MAX - 2;',
        'fSize = (size_t)fileSize;',
        'buf = X265_MALLOC(char, fSize + 2);',
        'size_t readBytes = std::fread(buf, 1, fSize, fh);',
        'bError |= readBytes != fSize;',
        "if (!bError && buf[fSize - 1] != '\\n')",
        'if (!bError)',
        'buf[fSize] = 0;',
    )
    for snippet in snippets:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing common slurp size guardrail: {snippet}'))

    forbidden = 'bError |= (fSize = std::ftell(fh)) <= 0;'
    if forbidden in func_text:
        failures.append((TARGET.as_posix(), 0, f'forbidden common slurp size regression: {forbidden}'))
    forbidden = 'bError |= std::fread(buf, 1, fSize, fh) != fSize;'
    if forbidden in func_text:
        failures.append((TARGET.as_posix(), 0, f'forbidden common slurp size regression: {forbidden}'))

    file_size_pos = func_text.find('fileSize = std::ftell(fh);')
    nonpositive_pos = func_text.find('bError |= fileSize <= 0;', file_size_pos if file_size_pos != -1 else 0)
    overflow_pos = func_text.find('bError |= (uint64_t)fileSize > (uint64_t)SIZE_MAX - 2;', nonpositive_pos if nonpositive_pos != -1 else 0)
    cast_pos = func_text.find('fSize = (size_t)fileSize;', overflow_pos if overflow_pos != -1 else 0)
    alloc_pos = func_text.find('buf = X265_MALLOC(char, fSize + 2);', cast_pos if cast_pos != -1 else 0)
    read_pos = func_text.find('size_t readBytes = std::fread(buf, 1, fSize, fh);', alloc_pos if alloc_pos != -1 else 0)
    short_read_pos = func_text.find('bError |= readBytes != fSize;', read_pos if read_pos != -1 else 0)
    newline_pos = func_text.find("if (!bError && buf[fSize - 1] != '\\n')", short_read_pos if short_read_pos != -1 else 0)
    terminator_guard_pos = func_text.find('if (!bError)', newline_pos if newline_pos != -1 else 0)
    terminator_pos = func_text.find('buf[fSize] = 0;', terminator_guard_pos if terminator_guard_pos != -1 else 0)
    if -1 in (
        file_size_pos,
        nonpositive_pos,
        overflow_pos,
        cast_pos,
        alloc_pos,
        read_pos,
        short_read_pos,
        newline_pos,
        terminator_guard_pos,
        terminator_pos,
    ) or not (
        file_size_pos < nonpositive_pos < overflow_pos < cast_pos < alloc_pos < read_pos <
        short_read_pos < newline_pos < terminator_guard_pos < terminator_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'x265_slurp_file must validate read length before inspecting or terminating the slurped buffer'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check common slurp size guard')
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

    print('Common slurp size guard validated')


if __name__ == '__main__':
    main()
