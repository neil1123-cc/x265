#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/abrEncApp.cpp')
REQUIRED_SNIPPETS = (
    'bool fieldBuffersCreated = false;',
    'if (!fieldBuffersCreated)',
    'fieldBuffersCreated = true;',
    'if (fieldBuffersCreated)',
    'X265_FREE(picField1.planes[0]);',
    'X265_FREE(picField2.planes[0]);',
)
FORBIDDEN_SNIPPETS = (
    'int static bCreated = 0;',
    'if (bCreated == 0)',
    'bCreated = 1;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ABR field-buffer state guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ABR field-buffer state regression: {snippet}'))

    field_decl_pos = text.find('bool fieldBuffersCreated = false;')
    create_guard_pos = text.find('if (!fieldBuffersCreated)', field_decl_pos)
    created_pos = text.find('fieldBuffersCreated = true;', create_guard_pos)
    cleanup_pos = text.find('if (fieldBuffersCreated)', created_pos)
    free_pos = text.find('X265_FREE(picField1.planes[0]);', cleanup_pos)
    if -1 in (field_decl_pos, create_guard_pos, created_pos, cleanup_pos, free_pos) or not (field_decl_pos < create_guard_pos < created_pos < cleanup_pos < free_pos):
        failures.append((TARGET.as_posix(), 0, 'threadMain must keep field-buffer state per invocation and clean it up on exit'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR thread field-buffer state guard')
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

    print('ABR field-buffer state guard validated')


if __name__ == '__main__':
    main()
