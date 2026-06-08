#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/input/lavf.cpp')
REQUIRED_SNIPPETS = (
    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
    'if (!newFrameBuffer)',
    'X265_FREE(frame_buffer);',
    'frame_buffer = newFrameBuffer;',
    'frame_size = requiredFrameSize;',
)
FORBIDDEN_SNIPPETS = (
    'X265_FREE(frame_buffer);\n        frame_buffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
    'frame_size = 0;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    block_start = text.find('if (requiredFrameSize > frame_size || frame_buffer == nullptr)')
    block_end = text.find('pic.framesize = frame_size;', block_start)
    block_text = text[block_start:block_end if block_end != -1 else None]
    forbidden_text = block_text if block_start != -1 else text
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in forbidden_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden LAVF buffer replace regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in block_text:
            failures.append((TARGET.as_posix(), 0, f'missing LAVF buffer replace guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check LAVF input buffer replace safety guardrails')
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

    print('LAVF buffer replace safety validated')


if __name__ == '__main__':
    main()
