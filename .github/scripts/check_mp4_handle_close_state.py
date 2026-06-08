#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/mp4.cpp')
FORBIDDEN_SNIPPETS = (
    'lsmash_close_file(&m_fileParam);',
)
REQUIRED_SNIPPETS = (
    'if (lsmash_close_file(&m_fileParam) < 0)',
    'm_fail = true;',
    'm_fileOpen = false;',
)
REGION_START = 'void MP4Muxer::cleanupHandle()'
REGION_END = 'void MP4Muxer::cleanupOutputFile()'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find(REGION_START)
    region_end = text.find(REGION_END, region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden MP4 handle close-state regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing MP4 handle close-state guardrail: {snippet}'))

    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        close_call = region.find('if (lsmash_close_file(&m_fileParam) < 0)')
        fail_set = region.find('m_fail = true;', close_call)
        file_open_clear = region.find('m_fileOpen = false;', close_call)
        root_destroy = region.find('lsmash_destroy_root(m_root);', close_call)
        root_clear = region.find('m_root = nullptr;', root_destroy)
        if -1 in (close_call, fail_set, file_open_clear, root_destroy, root_clear):
            failures.append((TARGET.as_posix(), 0, 'MP4 handle cleanup must resolve close failure before clearing file-open state and destroying the root'))
        elif not (close_call < fail_set < file_open_clear < root_destroy < root_clear):
            failures.append((TARGET.as_posix(), 0, 'MP4 handle cleanup must resolve close failure before clearing file-open state and destroying the root'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MP4 handle close state')
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

    print('MP4 handle close-state guard validated')


if __name__ == '__main__':
    main()
