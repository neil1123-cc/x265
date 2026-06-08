#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/common.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(fh) || std::fclose(fh)',
    'bError |= std::ferror(fh) || std::fclose(fh);',
)
REQUIRED_SNIPPETS = (
    'else if (std::ferror(fh))',
    'bool closeFailed = std::ferror(fh) != 0;',
    'if (std::fclose(fh))',
    'closeFailed = true;',
    'x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after open failure\\n", filename);',
    'x265_log_file(nullptr, X265_LOG_ERROR, "unable to open file %s\\n", filename);',
    'bError |= std::fseek(fh, 0, SEEK_END) < 0;',
    'bError |= closeFailed;',
    'return buf;',
    'error:',
    'if (closeFailed)',
    'x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after read failure\\n", filename);',
    'x265_log(nullptr, X265_LOG_ERROR, "unable to read the file\\n");',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find('FILE *fh = x265_fopen(filename, "rb");')
    error_label = text.find('error:', region_start)
    region_end = text.find('return nullptr;', error_label)
    region = text[region_start:region_end] if -1 not in (region_start, error_label, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden common slurp short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing common slurp close guardrail: {snippet}'))
    if region.count('bool closeFailed = std::ferror(fh) != 0;') != 3:
        failures.append((TARGET.as_posix(), 0, 'expected guarded common slurp close handling in the open-failure, read-complete, and error-cleanup paths'))
    if region.count('if (std::fclose(fh))') != 3:
        failures.append((TARGET.as_posix(), 0, 'expected three guarded common slurp fclose calls'))

    error_branch = region.find('else if (std::ferror(fh))')
    seek_line = region.find('bError |= std::fseek(fh, 0, SEEK_END) < 0;')
    first_close = region.find('bool closeFailed = std::ferror(fh) != 0;')
    second_close = region.find('bool closeFailed = std::ferror(fh) != 0;', first_close + 1)
    return_buf = region.find('return buf;')
    error_label = region.find('error:')
    third_close = region.find('bool closeFailed = std::ferror(fh) != 0;', second_close + 1)
    if -1 not in (error_branch, seek_line, first_close, second_close, return_buf, error_label, third_close):
        if not (error_branch < first_close < seek_line < second_close < return_buf < error_label < third_close):
            failures.append((TARGET.as_posix(), 0, 'common slurp close guards must preserve the early open-failure, read-complete, and error-cleanup ordering'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check common slurp close state')
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

    print('Common slurp close guard validated')


if __name__ == '__main__':
    main()
