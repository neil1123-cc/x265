#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/output/gop.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(hdr_file) || std::fclose(hdr_file)',
    'std::ferror(data_file) || std::fclose(data_file)',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = std::ferror(hdr_file) != 0;',
    'if (std::fclose(hdr_file))',
    'bool closeFailed = std::ferror(data_file) != 0;',
    'if (std::fclose(data_file))',
    'data_file = nullptr;',
    'b_fail = true;',
    'return -1;',
)
HDR_REGION_START = 'if (!smart_fwrite(p_nal[i].payload, p_nal[i].sizeBytes, hdr_file))'
HDR_REGION_END = 'return -1;'
DATA_REGION_START = 'if (is_keyframe) {'
DATA_REGION_END = 'std::stringstream ss;'


def get_region(text, start_marker, end_marker, include_end=False):
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if -1 in (start, end):
        return text
    if include_end:
        end += len(end_marker)
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    hdr_region = get_region(text, HDR_REGION_START, HDR_REGION_END, include_end=True)
    data_region = get_region(text, DATA_REGION_START, DATA_REGION_END, include_end=True)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden GOP intermediate close short-circuit regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing GOP intermediate close guardrail: {snippet}'))

    if not has_in_order(
        hdr_region,
        (
            'bool closeFailed = std::ferror(hdr_file) != 0;',
            'if (std::fclose(hdr_file))',
            'closeFailed = true;',
            'if (closeFailed)',
            'b_fail = true;',
            'return -1;',
        ),
    ):
        failures.append((TARGET.as_posix(), 0, 'GOP header write failure must finalize the header file before returning'))

    if not has_in_order(
        data_region,
        (
            'bool closeFailed = std::ferror(data_file) != 0;',
            'if (std::fclose(data_file))',
            'closeFailed = true;',
            'if (closeFailed)',
            'b_fail = true;',
            'data_file = nullptr;',
            'return -1;',
            'data_file = nullptr;',
            'std::stringstream ss;',
        ),
    ):
        failures.append((TARGET.as_posix(), 0, 'GOP keyframe rollover must clear the prior data file before reopening the next GOP payload'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check GOP intermediate close state')
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

    print('GOP intermediate close-state guard validated')


if __name__ == '__main__':
    main()
