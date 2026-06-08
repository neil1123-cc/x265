#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    'ferror(lfn) || fclose(lfn)',
)
REQUIRED_SNIPPETS = (
    'bool closeFailed = ferror(lfn) != 0;',
    'if (fclose(lfn))',
    'closeFailed = true;',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after open failure\\n");',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after incomplete parse\\n");',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after truncated parse\\n");',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after invalid value\\n");',
    'x265_log(param, X265_LOG_WARNING, "unable to close lambda file after oversized table\\n");',
    'x265_log(param, X265_LOG_WARNING, "unable to finalize lambda file state\\n");',
    'x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\\n", param->rc.lambdaFileName);',
    'x265_log(param, X265_LOG_ERROR, "lambda file is incomplete\\n");',
    'x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\\n", tok);',
    'x265_log(param, X265_LOG_ERROR, "lambda file contains too many values\\n");',
    'return true;',
    'return false;',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    region_start = text.find('FILE *lfn = x265_fopen(param->rc.lambdaFileName, "r");')
    region_end = text.rfind('return false;')
    region = text[region_start:region_end + len('return false;')] if -1 not in (region_start, region_end) else text
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden lambda file short-circuit close regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing lambda file close guardrail: {snippet}'))
    if region.count('bool closeFailed = ferror(lfn) != 0;') != 7:
        failures.append((TARGET.as_posix(), 0, 'expected seven guarded lambda-file close paths'))
    if region.count('if (fclose(lfn))') != 7:
        failures.append((TARGET.as_posix(), 0, 'expected seven guarded lambda-file fclose calls'))
    if region.count('return true;') != 7:
        failures.append((TARGET.as_posix(), 0, 'expected seven lambda-file error returns'))
    if region.count('return false;') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two lambda-file false returns for truncated parse and successful completion'))

    open_warning = region.find('x265_log(param, X265_LOG_WARNING, "unable to close lambda file after open failure\\n");')
    read_warning = region.find('x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\\n");')
    incomplete_warning = region.find('x265_log(param, X265_LOG_WARNING, "unable to close lambda file after incomplete parse\\n");')
    truncated_warning = region.find('x265_log(param, X265_LOG_WARNING, "unable to close lambda file after truncated parse\\n");')
    invalid_warning = region.find('x265_log(param, X265_LOG_WARNING, "unable to close lambda file after invalid value\\n");')
    oversized_warning = region.find('x265_log(param, X265_LOG_WARNING, "unable to close lambda file after oversized table\\n");')
    finalize_warning = region.find('x265_log(param, X265_LOG_WARNING, "unable to finalize lambda file state\\n");')
    if -1 not in (open_warning, read_warning, incomplete_warning, truncated_warning, invalid_warning, oversized_warning, finalize_warning):
        if not (open_warning < read_warning < incomplete_warning < truncated_warning < invalid_warning < oversized_warning < finalize_warning):
            failures.append((TARGET.as_posix(), 0, 'lambda-file close guards must preserve open-failure, parse-failure, and finalize ordering'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check lambda file close state')
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

    print('Lambda file close guard validated')


if __name__ == '__main__':
    main()
