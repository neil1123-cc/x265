#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'parseExitCode = -1;',
    'parseExitCode = 1;',
    'parseExitCode = 0;',
    'showHelp(param);',
    'x265_report_simd(param);',
    'return false;',
    "case 'h':",
    'OPT("fullhelp")',
)
FORBIDDEN_SNIPPETS = (
    'std::exit(0);',
    'std::exit(1);',
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
            failures.append((TARGET.as_posix(), 0, f'missing CLI help-exit cleanup guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden CLI help-exit cleanup regression: {snippet}'))

    version_pos = text.find("case 'V':")
    report_pos = text.find('x265_report_simd(param);', version_pos if version_pos >= 0 else 0)
    return_pos = text.find('return false;', version_pos if version_pos >= 0 else 0)
    exitcode_pos = text.find('parseExitCode = 0;', report_pos if report_pos >= 0 else 0, return_pos if return_pos >= 0 else len(text))
    if -1 in (version_pos, report_pos, exitcode_pos, return_pos) or not (version_pos < report_pos < exitcode_pos < return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI version path must set parseExitCode and return false without terminating the process'))

    help_pos = text.find("case 'h':")
    help_return_pos = text.find('return false;', help_pos if help_pos >= 0 else 0)
    help_exit_pos = text.find('parseExitCode = 0;', help_pos if help_pos >= 0 else 0, help_return_pos if help_return_pos >= 0 else len(text))
    if -1 in (help_pos, help_exit_pos, help_return_pos) or not (help_pos < help_exit_pos < help_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI help path must exit successfully after printing help'))

    fullhelp_pos = text.find('OPT("fullhelp")')
    fullhelp_return_pos = text.find('return false;', fullhelp_pos if fullhelp_pos >= 0 else 0)
    fullhelp_exit_pos = text.find('parseExitCode = 0;', fullhelp_pos if fullhelp_pos >= 0 else 0, fullhelp_return_pos if fullhelp_return_pos >= 0 else len(text))
    if -1 in (fullhelp_pos, fullhelp_exit_pos, fullhelp_return_pos) or not (fullhelp_pos < fullhelp_exit_pos < fullhelp_return_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI fullhelp path must exit successfully after printing help'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI help/version cleanup routing')
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

    print('CLI help/version cleanup guard validated')


if __name__ == '__main__':
    main()
