#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    'for (init = buf; (tok = strtok_r(init, ",", &saveptr)); init = nullptr)',
)
REQUIRED_SNIPPETS = (
    'if (bError)',
    'char *buf = strdup(value);',
    'bError = 0;',
    'cpu = 0;',
    'for (char* scan = buf; scan && *scan; )',
    "char* separator = std::strchr(scan, ',');",
    "if (separator)\n                *separator = '\\0';",
    'tok = scan;',
    'scan = separator ? separator + 1 : nullptr;',
    'if (!*tok)',
    'cpu |= X265_NS::cpu_names[i].flags;',
    'free(buf);',
)
REGION_START = 'int parseCpuName(const char* value, bool& bError, bool bEnableavx512)'
REGION_END = 'static const int fixedRatios[][2] ='


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
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
    region = get_region(text, REGION_START, REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden CPU list parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing CPU list parse guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'if (bError)',
                'char *buf = strdup(value);',
                'bError = 0;',
                'cpu = 0;',
                'for (char* scan = buf; scan && *scan; )',
                "char* separator = std::strchr(scan, ',');",
                "if (separator)\n                *separator = '\\0';",
                'tok = scan;',
                'scan = separator ? separator + 1 : nullptr;',
                'if (!*tok)',
                'cpu |= X265_NS::cpu_names[i].flags;',
                'free(buf);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseCpuName must split the CPU list with the reviewed comma scanner and reject empty tokens before accumulating CPU flags'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed CPU list parsing guardrails in common/param.cpp')
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

    print('CPU list parse usage validated')


if __name__ == '__main__':
    main()
