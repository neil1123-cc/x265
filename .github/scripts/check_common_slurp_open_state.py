#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/common.cpp')
REQUIRED_SNIPPETS = (
    'bool closeFailed = false;',
    'FILE *fh = x265_fopen(filename, "rb");',
    'else if (std::ferror(fh))',
    'closeFailed = std::ferror(fh) != 0;',
    'if (std::fclose(fh))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after open failure\\n", filename);',
    'x265_log_file(nullptr, X265_LOG_ERROR, "unable to open file %s\\n", filename);',
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
            failures.append((TARGET.as_posix(), 0, f'missing common slurp open-state guardrail: {snippet}'))

    close_decl = text.find('bool closeFailed = false;')
    open_pos = text.find('FILE *fh = x265_fopen(filename, "rb");', close_decl if close_decl != -1 else 0)
    error_branch = text.find('else if (std::ferror(fh))', open_pos if open_pos != -1 else 0)
    close_assign = text.find('closeFailed = std::ferror(fh) != 0;', error_branch if error_branch != -1 else 0)
    fclose_pos = text.find('if (std::fclose(fh))', close_assign if close_assign != -1 else 0)
    close_true = text.find('closeFailed = true;', fclose_pos if fclose_pos != -1 else 0)
    close_warn = text.find(
        'x265_log_file(nullptr, X265_LOG_WARNING, "unable to close file %s after open failure\\n", filename);',
        close_true if close_true != -1 else 0,
    )
    open_error = text.find(
        'x265_log_file(nullptr, X265_LOG_ERROR, "unable to open file %s\\n", filename);',
        close_warn if close_warn != -1 else 0,
    )
    if -1 in (close_decl, open_pos, error_branch, close_assign, fclose_pos, close_true, close_warn, open_error) or not (
        close_decl < open_pos < error_branch < close_assign < fclose_pos < close_true < close_warn < open_error
    ):
        failures.append((TARGET.as_posix(), 0, 'common slurp open-state guard must preserve close-state initialization before open-failure cleanup'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check common slurp open state')
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

    print('Common slurp open-state guard validated')


if __name__ == '__main__':
    main()
