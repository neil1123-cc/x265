#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/common.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(fp) || std::fclose(fp)',
    'std::fputs(buffer, fp) == EOF || std::ferror(fp) || std::fclose(fp)',
)
REQUIRED_SNIPPETS = (
    'if (std::ferror(fp))',
    'bool closeFailed = std::ferror(fp) != 0;',
    'std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);',
    'bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);',
    'if (std::fclose(fp))',
    'closeFailed = true;',
    'if (closeFailed)',
    'std::fputs("x265 [warning]: unable to finalize log file state\\n", stderr);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find('FILE* fp = x265_fopen(param->logfn, "ab");')
    region_end = text.find('        }\n    }\n}', region_start)
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden common logfile short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing common logfile close guardrail: {snippet}'))
    if region.count('if (std::fclose(fp))') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected guarded log-file fclose handling in both the open-failure and finalize branches'))

    open_close = 'bool closeFailed = std::ferror(fp) != 0;'
    open_warning = 'std::fputs("x265 [warning]: unable to close log file after open failure\\n", stderr);'
    final_close = 'bool closeFailed = std::fputs(buffer, fp) == EOF || std::ferror(fp);'
    final_warning = 'std::fputs("x265 [warning]: unable to finalize log file state\\n", stderr);'
    open_close_index = region.find(open_close)
    open_warning_index = region.find(open_warning)
    else_branch = region.find('else\n            {', open_warning_index)
    if else_branch == -1:
        else_branch = region.find('else', open_warning_index)
    final_close_index = region.find(final_close)
    final_warning_index = region.find(final_warning)
    if -1 not in (else_branch, open_close_index, open_warning_index, final_close_index, final_warning_index):
        if not (open_close_index < open_warning_index < else_branch < final_close_index < final_warning_index):
            failures.append((TARGET.as_posix(), 0, 'common logfile close guards must preserve the open-failure branch before the finalize branch'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check common logfile close state')
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

    print('Common logfile close guard validated')


if __name__ == '__main__':
    main()
