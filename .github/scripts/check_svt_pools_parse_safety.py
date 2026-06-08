#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'int logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);',
    'int logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);',
    'bError |= bLogicalProcessorsError;',
    'if (!bLogicalProcessorsError)',
    'svtHevcParam->targetSocket = 1;',
    'svtHevcParam->targetSocket = 0;',
    'svtHevcParam->logicalProcessors = logicalProcessors;',
)
FORBIDDEN_SNIPPETS = (
    'svtHevcParam->targetSocket = 1;\n                            svtHevcParam->logicalProcessors = x265_atoi(temp2, bLogicalProcessorsError);',
    'svtHevcParam->targetSocket = 0;\n                    svtHevcParam->logicalProcessors = x265_atoi(temp1, bLogicalProcessorsError);',
    'svtHevcParam->targetSocket = 1;\n                            svtHevcParam->logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);',
    'svtHevcParam->targetSocket = 0;\n                        svtHevcParam->logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);',
)


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
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, 'forbidden SVT pools regression: invalid logical-processor counts must not overwrite target socket state'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing SVT pools guardrail: {snippet}'))
    if text.count('bError |= bLogicalProcessorsError;') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing SVT pools guardrail: logical-processor parse errors must propagate in both socket branches'))
    if text.count('if (!bLogicalProcessorsError)') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing SVT pools guardrail: logical-processor assignments must stay behind both validation branches'))
    if text.count('svtHevcParam->logicalProcessors = logicalProcessors;') < 2:
        failures.append((TARGET.as_posix(), 0, 'missing SVT pools guardrail: validated logical-processor counts must be assigned in both socket branches'))

    temp2_parse = text.find('int logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);')
    temp1_parse = text.find('int logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);')
    temp2_branch = text[temp2_parse:temp1_parse] if -1 not in (temp2_parse, temp1_parse) else ''
    temp1_branch = text[temp1_parse:] if temp1_parse != -1 else ''
    if temp2_branch and not has_in_order(
        temp2_branch,
        (
            'int logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);',
            'bError |= bLogicalProcessorsError;',
            'if (!bLogicalProcessorsError)',
            'svtHevcParam->targetSocket = 1;',
            'svtHevcParam->logicalProcessors = logicalProcessors;',
        ),
    ):
        failures.append((TARGET.as_posix(), 0, 'SVT pools temp2 branch must validate logical-processor counts before updating socket state'))
    if temp1_branch and not has_in_order(
        temp1_branch,
        (
            'int logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);',
            'bError |= bLogicalProcessorsError;',
            'if (!bLogicalProcessorsError)',
            'svtHevcParam->targetSocket = 0;',
            'svtHevcParam->logicalProcessors = logicalProcessors;',
        ),
    ):
        failures.append((TARGET.as_posix(), 0, 'SVT pools temp1 branch must validate logical-processor counts before updating socket state'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SVT pools parse safety guardrails')
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

    print('SVT pools parse safety validated')


if __name__ == '__main__':
    main()
