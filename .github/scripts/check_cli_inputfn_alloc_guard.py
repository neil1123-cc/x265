#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
REQUIRED_SNIPPETS = (
    'bool CLIOptions::parse(int argc, char **argv)',
    'for (int view = 0; view < MAX_VIEWS; view++)',
    'inputfn[view] = X265_MALLOC(char, sizeof(char) * 1024);',
    'if (!inputfn[view])',
    'x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate input filename buffer\\n");',
    'return true;',
    'std::fill_n(inputfn[view], 1024, char(0));',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    parse_start = text.find('bool CLIOptions::parse(int argc, char **argv)')
    zone_param_start = text.find('bool CLIOptions::parseZoneParam(', parse_start if parse_start != -1 else 0)
    zone_file_start = text.find('bool CLIOptions::parseZoneFile()', parse_start if parse_start != -1 else 0)
    parse_end = zone_param_start if zone_param_start != -1 else zone_file_start
    parse_text = text[parse_start:parse_end] if -1 not in (parse_start, parse_end) else text
    failures = []
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in parse_text:
            failures.append((TARGET.as_posix(), 0, f'missing cli inputfn alloc guardrail: {snippet}'))

    loop_pos = parse_text.find('for (int view = 0; view < MAX_VIEWS; view++)')
    alloc_pos = parse_text.find('inputfn[view] = X265_MALLOC(char, sizeof(char) * 1024);', loop_pos if loop_pos != -1 else 0)
    check_pos = parse_text.find('if (!inputfn[view])', alloc_pos if alloc_pos != -1 else 0)
    fill_pos = parse_text.find('std::fill_n(inputfn[view], 1024, char(0));', check_pos if check_pos != -1 else 0)
    if -1 in (loop_pos, alloc_pos, check_pos, fill_pos) or not (loop_pos < alloc_pos < check_pos < fill_pos):
        failures.append((TARGET.as_posix(), 0, 'CLI input filename buffer must be checked before zero-fill'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check CLI input filename allocation guardrail')
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

    print('CLI input filename allocation guard validated')


if __name__ == '__main__':
    main()
