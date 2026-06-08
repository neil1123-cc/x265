#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/scalinglist.cpp')
FORBIDDEN_SNIPPETS = (
    'std::ferror(fp) || std::fclose(fp)',
)
REQUIRED_SNIPPETS = (
    'closeFailed = std::ferror(fp) != 0;',
    'if (std::fclose(fp))',
    'closeFailed = true;',
    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);',
    'x265_log_file(nullptr, X265_LOG_ERROR, "can\'t open scaling list file %s\\n", filename);',
    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix read failure\\n", filename);',
    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);',
    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC read failure\\n", filename);',
    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);',
    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t finalize scaling list file %s\\n", filename);',
    'm_bEnabled = true;',
    'm_bDataPresent = true;',
    'return true;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find('else if (std::ferror(fp))')
    region_end = text.find('m_bDataPresent = true;', region_start)
    if region_end != -1:
        region_end += len('m_bDataPresent = true;')
    region = text[region_start:region_end] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden scaling list short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing scaling list close guardrail: {snippet}'))
    if region.count('closeFailed = std::ferror(fp) != 0;') != 6:
        failures.append((TARGET.as_posix(), 0, 'expected six guarded scaling-list close paths'))
    if region.count('if (std::fclose(fp))') != 6:
        failures.append((TARGET.as_posix(), 0, 'expected six guarded scaling-list fclose calls'))

    open_warning = region.find('x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after open failure\\n", filename);')
    matrix_read = region.find('x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix read failure\\n", filename);')
    matrix_parse = region.find('x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);')
    dc_read = region.find('x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC read failure\\n", filename);')
    dc_parse = region.find('x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);')
    finalize = region.find('x265_log_file(nullptr, X265_LOG_WARNING, "can\'t finalize scaling list file %s\\n", filename);')
    enabled = region.find('m_bEnabled = true;')
    if -1 not in (open_warning, matrix_read, matrix_parse, dc_read, dc_parse, finalize, enabled):
        if not (open_warning < matrix_read < matrix_parse < dc_read < dc_parse < finalize < enabled):
            failures.append((TARGET.as_posix(), 0, 'scaling list close guards must preserve open-failure, parse-failure, and finalize ordering before enabling the scaling list'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check scaling list close state')
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

    print('Scaling list close guard validated')


if __name__ == '__main__':
    main()
