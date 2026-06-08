#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    'temp1 = strtok(pools, ",");',
    'temp2 = strtok(nullptr, ",");',
    'svtHevcParam->logicalProcessors = atoi(temp2);',
    'svtHevcParam->logicalProcessors = atoi(temp1);',
)
REQUIRED_SNIPPETS = (
    'if (count > 1)',
    'else if (count == 1)',
    "char* separator = std::strchr(pools, ',');",
    'if (!separator || separator == pools || !separator[1])',
    "*separator = '\\0';",
    'temp1 = pools;',
    'temp2 = separator + 1;',
    'int logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);',
    'svtHevcParam->targetSocket = 1;',
    'svtHevcParam->logicalProcessors = logicalProcessors;',
    'int logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);',
    'svtHevcParam->targetSocket = 0;',
    'svtHevcParam->logicalProcessors = logicalProcessors;',
)
REGION_START = 'if (count > 1)'
REGION_END = 'free(pools);'


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
            failures.append((TARGET.as_posix(), 0, f'forbidden SVT pools parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing SVT pools parse guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'if (count > 1)',
                'else if (count == 1)',
                "char* separator = std::strchr(pools, ',');",
                'if (!separator || separator == pools || !separator[1])',
                "*separator = '\\0';",
                'temp1 = pools;',
                'temp2 = separator + 1;',
                'int logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);',
                'svtHevcParam->targetSocket = 1;',
                'svtHevcParam->logicalProcessors = logicalProcessors;',
                'int logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);',
                'svtHevcParam->targetSocket = 0;',
                'svtHevcParam->logicalProcessors = logicalProcessors;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'SVT pools parsing must split the two-socket form with the reviewed separator logic and only publish logicalProcessors after the checked integer parse succeeds'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed SVT pools parsing guardrails in common/param.cpp')
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

    print('SVT pools parse usage validated')


if __name__ == '__main__':
    main()
