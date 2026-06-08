#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265.cpp')
SHARED_TARGET = Path('source/x265cli.h')
SHARED_REQUIRED_SNIPPETS = (
    'static inline bool hasCliExitRequest(int argc, char** argv)',
    "if (c == 'h' || c == 'V')",
    '!std::strcmp(long_options[long_options_index].name, "fullhelp")',
)
MAIN_REQUIRED_SNIPPETS = (
    'bool isCliExitRequest = hasCliExitRequest(argc, argv);',
    'bool isAbrLadder = !isCliExitRequest && checkAbrLadder(argc, argv, &abrConfig);',
    'else if (cliopt[0].parseExitCode >= 0)',
    'ret = cliopt[0].parseExitCode;',
)
FORBIDDEN_SNIPPETS = (
    'bool isAbrLadder = checkAbrLadder(argc, argv, &abrConfig);',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    shared_path = repo_root / SHARED_TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]
    if not shared_path.is_file():
        return [(SHARED_TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    shared_text = shared_path.read_text(encoding='utf-8', errors='ignore')
    helper_start = shared_text.find('static inline bool hasCliExitRequest(int argc, char** argv)')
    reject_start = shared_text.find('static inline bool rejectCliExitRequest(', helper_start if helper_start != -1 else 0)
    helper_text = shared_text[helper_start:reject_start] if -1 not in (helper_start, reject_start) else shared_text
    main_start = text.find('int main(int argc, char **argv)')
    cleanup_start = text.find('cleanup:', main_start if main_start != -1 else 0)
    main_text = text[main_start:cleanup_start] if -1 not in (main_start, cleanup_start) else text
    failures = []
    for snippet in SHARED_REQUIRED_SNIPPETS:
        if snippet not in helper_text:
            failures.append((SHARED_TARGET.as_posix(), 0, f'missing abr/help precedence guardrail: {snippet}'))
    for snippet in MAIN_REQUIRED_SNIPPETS:
        if snippet not in main_text:
            failures.append((TARGET.as_posix(), 0, f'missing abr/help precedence guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in main_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden abr/help precedence regression: {snippet}'))

    helper_pos = helper_text.find('static inline bool hasCliExitRequest(int argc, char** argv)')
    help_pos = helper_text.find("if (c == 'h' || c == 'V')", helper_pos if helper_pos >= 0 else 0)
    fullhelp_pos = helper_text.find('!std::strcmp(long_options[long_options_index].name, "fullhelp")', help_pos if help_pos >= 0 else 0)
    request_pos = main_text.find('bool isCliExitRequest = hasCliExitRequest(argc, argv);')
    abr_pos = main_text.find('bool isAbrLadder = !isCliExitRequest && checkAbrLadder(argc, argv, &abrConfig);', request_pos if request_pos >= 0 else 0)
    exit_branch_pos = main_text.find('else if (cliopt[0].parseExitCode >= 0)', abr_pos if abr_pos >= 0 else 0)
    exit_assign_pos = main_text.find('ret = cliopt[0].parseExitCode;', exit_branch_pos if exit_branch_pos >= 0 else 0)
    if -1 in (helper_pos, help_pos, fullhelp_pos, request_pos, abr_pos):
        failures.append((TARGET.as_posix(), 0, 'x265 main must detect explicit help/version/fullhelp before abr-ladder parsing'))
    elif not (helper_pos < help_pos < fullhelp_pos and request_pos < abr_pos):
        failures.append((TARGET.as_posix(), 0, 'x265 main must detect explicit help/version/fullhelp before abr-ladder parsing'))
    if -1 in (exit_branch_pos, exit_assign_pos) or not (exit_branch_pos < exit_assign_pos):
        failures.append((TARGET.as_posix(), 0, 'x265 main must preserve parseExitCode handling after CLI parse returns'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check ABR ladder precedence against explicit help/version exits')
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

    print('ABR/help precedence guard validated')


if __name__ == '__main__':
    main()
