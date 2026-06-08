#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/x265cli.cpp')
FORBIDDEN_SNIPPETS = (
    'std::strcpy(inputfn[0], optarg);',
    'std::strcpy(inputfn[0], argv[optind++]);',
    'inputfn[0] = optarg;',
)
HELPER_REQUIRED_SNIPPETS = (
    'static bool copyCLIString(char* dst, size_t dstSize, const char* src, const char* context)',
    'if (!dst || !dstSize || !src)',
    'size_t length = std::strlen(src);',
    'if (length >= dstSize)',
    'x265_log(nullptr, X265_LOG_ERROR, "%s exceeds supported length\\n", context);',
    'std::memcpy(dst, src, length + 1);',
    'return true;',
)
OPTION_REQUIRED_SNIPPETS = (
    'OPT("input")',
    'if (!copyCLIString(inputfn[0], 1024, optarg, "Input filename"))',
    'return true;',
)
POSITIONAL_REQUIRED_SNIPPETS = (
    '#if !ENABLE_MULTIVIEW',
    'if (optind < argc && !(*inputfn[0]))',
    'if (!copyCLIString(inputfn[0], 1024, argv[optind++], "Input filename"))',
    'if (optind < argc && !outputfn)',
)
HELPER_REGION_START = 'static bool copyCLIString(char* dst, size_t dstSize, const char* src, const char* context)'
HELPER_REGION_END = 'static bool tokenizeConfigFileArgs(char* start, char** args, int maxArgs, int& argCount, const char* context)'
OPTION_REGION_START = 'OPT("input")'
OPTION_REGION_END = 'OPT("recon")'
POSITIONAL_REGION_START = '#if !ENABLE_MULTIVIEW'
POSITIONAL_REGION_END = 'if (optind < argc && !outputfn)'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    end += len(end_marker)
    return text[start:end]


def has_in_order(text, snippets):
    pos = -1
    for snippet in snippets:
        pos = text.find(snippet, pos + 1)
        if pos == -1:
            return False
    return True


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    helper_region = get_region(text, HELPER_REGION_START, HELPER_REGION_END)
    option_region = get_region(text, OPTION_REGION_START, OPTION_REGION_END)
    positional_region = get_region(text, POSITIONAL_REGION_START, POSITIONAL_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden input filename copy regression: {snippet}'))
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in helper_region:
            failures.append((TARGET.as_posix(), 0, f'missing input filename copy guardrail: {snippet}'))
    for snippet in OPTION_REQUIRED_SNIPPETS:
        if snippet not in option_region:
            failures.append((TARGET.as_posix(), 0, f'missing input filename copy guardrail: {snippet}'))
    for snippet in POSITIONAL_REQUIRED_SNIPPETS:
        if snippet not in positional_region:
            failures.append((TARGET.as_posix(), 0, f'missing input filename copy guardrail: {snippet}'))
    if all(snippet in helper_region for snippet in HELPER_REQUIRED_SNIPPETS):
        if not has_in_order(
            helper_region,
            (
                'if (!dst || !dstSize || !src)',
                'size_t length = std::strlen(src);',
                'if (length >= dstSize)',
                'x265_log(nullptr, X265_LOG_ERROR, "%s exceeds supported length\\n", context);',
                'std::memcpy(dst, src, length + 1);',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'copyCLIString must reject null and oversized input before copying bytes into the CLI filename buffer'))
    if all(snippet in option_region for snippet in OPTION_REQUIRED_SNIPPETS):
        if not has_in_order(
            option_region,
            (
                'OPT("input")',
                'if (!copyCLIString(inputfn[0], 1024, optarg, "Input filename"))',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, '--input handling must route optarg through copyCLIString before returning on overflow'))
    if all(snippet in positional_region for snippet in POSITIONAL_REQUIRED_SNIPPETS):
        if not has_in_order(
            positional_region,
            (
                '#if !ENABLE_MULTIVIEW',
                'if (optind < argc && !(*inputfn[0]))',
                'if (!copyCLIString(inputfn[0], 1024, argv[optind++], "Input filename"))',
                'return true;',
                'if (optind < argc && !outputfn)',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Positional input filename parsing must use copyCLIString before advancing to output filename handling'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check input filename copy guardrails in x265cli.cpp')
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

    print('Input filename copy usage validated')


if __name__ == '__main__':
    main()
