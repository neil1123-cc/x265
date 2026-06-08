#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/scalinglist.cpp')
REQUIRED_SNIPPETS = (
    'FILE *fp = x265_fopen(filename, "r");',
    'else if (std::ferror(fp))',
    'bool closeFailed = std::ferror(fp) != 0;',
    'if (std::fclose(fp))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);',
    'x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
)
FORBIDDEN_SNIPPETS = (
    'std::fseek(fp, 0, 0);',
)
REGION_START = 'FILE *fp = x265_fopen(filename, "r");'
REGION_END = 'bool closeFailed = false;'


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
            failures.append((TARGET.as_posix(), 0, f'forbidden scaling list open-state regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing scaling list open-state guardrail: {snippet}'))

    if not has_in_order(
        region,
        (
            'FILE *fp = x265_fopen(filename, "r");',
            'if (!fp)',
            'x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
            'return true;',
            'else if (std::ferror(fp))',
            'bool closeFailed = std::ferror(fp) != 0;',
            'if (std::fclose(fp))',
            'closeFailed = true;',
            'if (closeFailed)',
            'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);',
            'x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
            'return true;',
            'bool closeFailed = false;',
        ),
    ):
        failures.append((TARGET.as_posix(), 0, 'scaling list open failure handling must finalize the preflight handle before reporting the open error and entering parse state'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scaling list open state')
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

    print('Scaling list open-state guard validated')


if __name__ == '__main__':
    main()
