#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("chromaloc")',
    'bool bChromaSampleLocTypeError = false;',
    'int chromaSampleLocType = parseOptionIntValue(value, bChromaSampleLocTypeError);',
    'bError |= bChromaSampleLocTypeError;',
    'if (!bChromaSampleLocTypeError)',
    'p->vui.bEnableChromaLocInfoPresentFlag = 1;',
    'p->vui.chromaSampleLocTypeTopField = chromaSampleLocType;',
    'p->vui.chromaSampleLocTypeBottomField = chromaSampleLocType;',
)
FORBIDDEN_SNIPPETS = (
    'p->vui.bEnableChromaLocInfoPresentFlag = 1;\n        p->vui.chromaSampleLocTypeTopField = x265_atoi(value, bError);',
    'p->vui.chromaSampleLocTypeBottomField = p->vui.chromaSampleLocTypeTopField;',
)
REGION_START = 'OPT("chromaloc")'
REGION_END = 'OPT("display-window")'


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
    for forbidden in FORBIDDEN_SNIPPETS:
        if forbidden in region:
            failures.append((TARGET.as_posix(), 0, 'forbidden chromaloc regression: invalid values must not update VUI chroma location state'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing chromaloc guardrail: {snippet}'))
    if all(snippet in region for snippet in REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'OPT("chromaloc")',
                'bool bChromaSampleLocTypeError = false;',
                'int chromaSampleLocType = parseOptionIntValue(value, bChromaSampleLocTypeError);',
                'bError |= bChromaSampleLocTypeError;',
                'if (!bChromaSampleLocTypeError)',
                'p->vui.bEnableChromaLocInfoPresentFlag = 1;',
                'p->vui.chromaSampleLocTypeTopField = chromaSampleLocType;',
                'p->vui.chromaSampleLocTypeBottomField = chromaSampleLocType;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'chromaloc parsing must keep the parse gate ahead of VUI chroma-location state publication'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check chromaloc parse safety guardrails')
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

    print('Chromaloc parse safety validated')


if __name__ == '__main__':
    main()
