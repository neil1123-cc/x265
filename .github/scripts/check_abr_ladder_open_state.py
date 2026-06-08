#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265.cpp')
REQUIRED_SNIPPETS = (
    'static bool checkAbrLadder(int argc, char **argv, FILE **abrConfig)',
    '*abrConfig = x265_fopen(optarg, "rb");',
    'if (!*abrConfig)',
    'x265_log_file(nullptr, X265_LOG_ERROR, "%s abr-ladder config file not found or error in opening config file\\n", optarg);',
    'else if (std::ferror(*abrConfig))',
    'bool closeFailed = std::ferror(*abrConfig) != 0;',
    'if (std::fclose(*abrConfig))',
    'closeFailed = true;',
    'if (closeFailed)',
    'x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file after open failure\\n");',
    '*abrConfig = nullptr;',
    'return true;',
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
            failures.append((TARGET.as_posix(), 0, f'missing abr ladder open-state guardrail: {snippet}'))

    open_pos = text.find('*abrConfig = x265_fopen(optarg, "rb");')
    null_pos = text.find('if (!*abrConfig)', open_pos if open_pos >= 0 else 0)
    null_log_pos = text.find('x265_log_file(nullptr, X265_LOG_ERROR, "%s abr-ladder config file not found or error in opening config file\\n", optarg);', null_pos if null_pos >= 0 else 0)
    null_return_pos = text.find('return true;', null_log_pos if null_log_pos >= 0 else 0)
    ferror_pos = text.find('else if (std::ferror(*abrConfig))', null_return_pos if null_return_pos >= 0 else 0)
    if -1 in (open_pos, null_pos, null_log_pos, null_return_pos, ferror_pos) or not (open_pos < null_pos < null_log_pos < null_return_pos < ferror_pos):
        failures.append((TARGET.as_posix(), 0, 'abr ladder open failure must log and return true before ferror handling'))

    close_failed_pos = text.find('bool closeFailed = std::ferror(*abrConfig) != 0;', ferror_pos if ferror_pos >= 0 else 0)
    fclose_pos = text.find('if (std::fclose(*abrConfig))', close_failed_pos if close_failed_pos >= 0 else 0)
    close_true_pos = text.find('closeFailed = true;', fclose_pos if fclose_pos >= 0 else 0)
    close_if_pos = text.find('if (closeFailed)', close_true_pos if close_true_pos >= 0 else 0)
    ferror_log_pos = text.find('x265_log(nullptr, X265_LOG_WARNING, "Unable to close abr ladder config file after open failure\\n");', close_if_pos if close_if_pos >= 0 else 0)
    reset_pos = text.find('*abrConfig = nullptr;', ferror_log_pos if ferror_log_pos >= 0 else 0)
    ferror_return_pos = text.find('return true;', reset_pos if reset_pos >= 0 else 0)
    if -1 in (ferror_pos, close_failed_pos, fclose_pos, close_true_pos, close_if_pos, ferror_log_pos, reset_pos, ferror_return_pos) or not (ferror_pos < close_failed_pos < fclose_pos < close_true_pos < close_if_pos < ferror_log_pos < reset_pos < ferror_return_pos):
        failures.append((TARGET.as_posix(), 0, 'abr ladder ferror path must test the error bit, still call fclose(), then null out and return true'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR ladder config open state')
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

    print('ABR ladder open-state guard validated')


if __name__ == '__main__':
    main()
