#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("atc-sei")',
    'bool bPreferredTransferCharacteristicsError = false;',
    'int preferredTransferCharacteristics = parseOptionIntValue(value, bPreferredTransferCharacteristicsError);',
    'const bool bPreferredTransferCharacteristicsRangeError = preferredTransferCharacteristics < -1',
    '|| preferredTransferCharacteristics > UINT8_MAX;',
    'bError |= bPreferredTransferCharacteristicsError || bPreferredTransferCharacteristicsRangeError;',
    'if (!bPreferredTransferCharacteristicsError && !bPreferredTransferCharacteristicsRangeError)',
    'p->preferredTransferCharacteristics = preferredTransferCharacteristics;',
)
FORBIDDEN_SNIPPETS = (
    'OPT("atc-sei") p->preferredTransferCharacteristics = x265_atoi(value, bError);',
    'if (!bPreferredTransferCharacteristicsError)\n                p->preferredTransferCharacteristics = preferredTransferCharacteristics;',
)
REGION_START = 'OPT("atc-sei")'
REGION_END = 'OPT("pic-struct")'


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
            failures.append((TARGET.as_posix(), 0, 'forbidden atc-sei regression: invalid values must not overwrite prior state'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing atc-sei guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'OPT("atc-sei")',
                'bool bPreferredTransferCharacteristicsError = false;',
                'int preferredTransferCharacteristics = parseOptionIntValue(value, bPreferredTransferCharacteristicsError);',
                'const bool bPreferredTransferCharacteristicsRangeError = preferredTransferCharacteristics < -1',
                '|| preferredTransferCharacteristics > UINT8_MAX;',
                'bError |= bPreferredTransferCharacteristicsError || bPreferredTransferCharacteristicsRangeError;',
                'if (!bPreferredTransferCharacteristicsError && !bPreferredTransferCharacteristicsRangeError)',
                'p->preferredTransferCharacteristics = preferredTransferCharacteristics;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'atc-sei parsing must keep the combined parse/range gate ahead of preferredTransferCharacteristics publication'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check atc-sei parse safety guardrails')
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

    print('ATC-SEI parse safety validated')


if __name__ == '__main__':
    main()
