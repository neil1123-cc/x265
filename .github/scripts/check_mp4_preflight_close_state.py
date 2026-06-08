#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/mp4.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(fh) || std::fclose(fh)',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = std::ferror(fh) != 0;',
    'if (std::fclose(fh))',
    'closeFailed = true;',
    'if (closeFailed)',
    'MP4_LOG_ERROR("cannot finalize output file preflight `%s\'.\\n", fname);'.replace("\\'", "'"),
    'm_fail = true;',
    'return false;',
)
REGION_START = 'FILE* fh = x265_fopen(fname, "wb");'
REGION_END = 'm_root = lsmash_create_root();'


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find(REGION_START)
    region_end = text.find(REGION_END, region_start)
    if -1 not in (region_start, region_end):
        region_end += len(REGION_END)
        region = text[region_start:region_end]
    else:
        region = text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden MP4 preflight short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing MP4 preflight close-state guardrail: {snippet}'))

    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        close_failed_init = region.find('bool closeFailed = std::ferror(fh) != 0;')
        fclose_call = region.find('if (std::fclose(fh))', close_failed_init)
        close_failed_set = region.find('closeFailed = true;', fclose_call)
        close_failed_check = region.find('if (closeFailed)', close_failed_set)
        log_call = region.find('MP4_LOG_ERROR("cannot finalize output file preflight `%s\'.\\n", fname);'.replace("\\'", "'"), close_failed_check)
        fail_set = region.find('m_fail = true;', close_failed_check)
        fail_return = region.find('return false;', close_failed_check)
        root_create = region.find('m_root = lsmash_create_root();', fail_return)
        if -1 in (close_failed_init, fclose_call, close_failed_set, close_failed_check, log_call, fail_set, fail_return, root_create):
            failures.append((TARGET.as_posix(), 0, 'MP4 preflight must record fclose failure before reporting the preflight error and creating the root'))
        elif not (close_failed_init < fclose_call < close_failed_set < close_failed_check < log_call < fail_set < fail_return < root_create):
            failures.append((TARGET.as_posix(), 0, 'MP4 preflight must record fclose failure before reporting the preflight error and creating the root'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check MP4 preflight close state')
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

    print('MP4 preflight close-state guard validated')


if __name__ == '__main__':
    main()
