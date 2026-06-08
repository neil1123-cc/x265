#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/nal.cpp')
REQUIRED_SNIPPETS = (
    'void NALList::takeContents(NALList& other)',
    'const uint32_t otherAllocSize = other.m_allocSize;',
    'other.m_buffer = nullptr;',
    'other.m_allocSize = 0;',
    'uint8_t* newBuffer = X265_MALLOC(uint8_t, otherAllocSize);',
    'if (newBuffer)',
    'other.m_buffer = newBuffer;',
    'other.m_allocSize = otherAllocSize;',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to realloc access unit buffer\\n");',
)
FORBIDDEN_SNIPPETS = (
    'other.m_buffer = X265_MALLOC(uint8_t, m_allocSize);',
    'other.m_buffer = X265_MALLOC(uint8_t, otherAllocSize);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden NAL takeContents realloc regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing NAL takeContents realloc guardrail: {snippet}'))

    take_contents_pos = text.find('void NALList::takeContents(NALList& other)')
    reset_num_pos = text.find('other.m_numNal = 0;', take_contents_pos if take_contents_pos != -1 else 0)
    reset_occ_pos = text.find('other.m_occupancy = 0;', reset_num_pos if reset_num_pos != -1 else 0)
    clear_buffer_pos = text.find('other.m_buffer = nullptr;', reset_occ_pos if reset_occ_pos != -1 else 0)
    clear_alloc_pos = text.find('other.m_allocSize = 0;', clear_buffer_pos if clear_buffer_pos != -1 else 0)
    alloc_pos = text.find('uint8_t* newBuffer = X265_MALLOC(uint8_t, otherAllocSize);', clear_alloc_pos if clear_alloc_pos != -1 else 0)
    assign_buffer_pos = text.find('other.m_buffer = newBuffer;', alloc_pos if alloc_pos != -1 else 0)
    assign_alloc_pos = text.find('other.m_allocSize = otherAllocSize;', assign_buffer_pos if assign_buffer_pos != -1 else 0)
    if -1 in (take_contents_pos, reset_num_pos, reset_occ_pos, clear_buffer_pos, clear_alloc_pos, alloc_pos, assign_buffer_pos, assign_alloc_pos) or not (
        take_contents_pos < reset_num_pos < reset_occ_pos < clear_buffer_pos < clear_alloc_pos < alloc_pos < assign_buffer_pos < assign_alloc_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'NALList::takeContents must reset the source list to a zero-capacity safe state before rebuilding its buffer'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check NAL takeContents realloc safety guardrails')
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

    print('NAL takeContents realloc safety validated')


if __name__ == '__main__':
    main()
