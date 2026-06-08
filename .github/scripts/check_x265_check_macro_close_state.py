#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/common.h')
FORBIDDEN_SNIPPETS = (
    'if (ferror(fp) || fclose(fp)) fprintf(stderr, "x265 [warning]: unable to close x265_check_failures.txt after open failure\\n");',
    'if (ferror(fp) || fclose(fp)) fprintf(stderr, "x265 [warning]: unable to finalize x265_check_failures.txt\\n");',
)
REQUIRED_SNIPPETS = (
    'if (ferror(fp)) {',
    'fprintf(fp, "%s:%d\\n", __FILE__, __LINE__);',
    'bool closeFailed = ferror(fp) != 0;',
    'if (fclose(fp)) closeFailed = true;',
    'if (closeFailed) fprintf(stderr, "x265 [warning]: unable to close x265_check_failures.txt after open failure\\n");',
    'if (closeFailed) fprintf(stderr, "x265 [warning]: unable to finalize x265_check_failures.txt\\n");',
    'g_checkFailures++; DEBUG_BREAK();',
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
            failures.append((TARGET.as_posix(), 0, f'forbidden X265_CHECK macro close short-circuit regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing X265_CHECK macro close guardrail: {snippet}'))
    if text.count('bool closeFailed = ferror(fp) != 0;') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected guarded X265_CHECK close handling in both the open-failure and finalize branches'))
    if text.count('if (fclose(fp)) closeFailed = true;') != 2:
        failures.append((TARGET.as_posix(), 0, 'expected two guarded X265_CHECK fclose calls'))

    open_warning = 'if (closeFailed) fprintf(stderr, "x265 [warning]: unable to close x265_check_failures.txt after open failure\\n");'
    final_warning = 'if (closeFailed) fprintf(stderr, "x265 [warning]: unable to finalize x265_check_failures.txt\\n");'
    else_branch = text.find('else {')
    open_warning_index = text.find(open_warning)
    final_warning_index = text.find(final_warning)
    log_line_index = text.find('fprintf(fp, "%s:%d\\n", __FILE__, __LINE__);')
    if -1 not in (else_branch, open_warning_index, final_warning_index, log_line_index):
        if not (open_warning_index < else_branch < log_line_index < final_warning_index):
            failures.append((TARGET.as_posix(), 0, 'X265_CHECK close guards must preserve the open-failure branch before the finalize branch'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check X265_CHECK macro close state')
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

    print('X265_CHECK macro close guard validated')


if __name__ == '__main__':
    main()
