#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/encoder.cpp')
REQUIRED_SNIPPETS = (
    'if (!copyDupPictureSideData(dest, src, m_param))',
    'return false;',
    'char* base = (char*)dest->planes[0];',
    'dest->pts = src->pts;',
)
FORBIDDEN_SNIPPETS = (
    'dest->format = 0;\n\n    if (!copyDupPictureSideData(dest, src, m_param))',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden copyPicture staging regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing copyPicture staging guardrail: {snippet}'))

    side_data_pos = text.find('if (!copyDupPictureSideData(dest, src, m_param))')
    pixel_copy_pos = text.find('char* base = (char*)dest->planes[0];')
    header_copy_pos = text.find('dest->pts = src->pts;')
    if -1 not in (side_data_pos, pixel_copy_pos, header_copy_pos) and not (side_data_pos < pixel_copy_pos < header_copy_pos):
        failures.append((TARGET.as_posix(), 0, 'copyPicture must copy side-data before mutating dest planes and headers'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check copyPicture staging guardrails')
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

    print('copyPicture staging validated')


if __name__ == '__main__':
    main()
