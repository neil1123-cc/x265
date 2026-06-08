#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("min-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->minVbvFullness);',
    'OPT("max-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxVbvFullness);',
    'CHECK(param->minVbvFullness < 0 || param->minVbvFullness > 100,',
    '"min-vbv-fullness must be a fraction 0 - 100");',
    'CHECK(param->maxVbvFullness < 0 || param->maxVbvFullness > 100,',
    '"max-vbv-fullness must be a fraction 0 - 100");',
)
FORBIDDEN_SNIPPETS = (
    'CHECK(param->minVbvFullness < 0 && param->minVbvFullness > 100,',
    'CHECK(param->maxVbvFullness < 0 && param->maxVbvFullness > 100,',
)
PARSE_REGION_START = 'OPT("min-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->minVbvFullness);'
PARSE_REGION_END = 'OPT("video-signal-type-preset")'
VALIDATION_REGION_START = 'CHECK(param->minVbvFullness < 0 || param->minVbvFullness > 100,'
VALIDATION_REGION_END = 'CHECK(param->rc.bitrate < 0,'


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
    parse_region = get_region(text, PARSE_REGION_START, PARSE_REGION_END)
    validation_region = get_region(text, VALIDATION_REGION_START, VALIDATION_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden vbv-fullness regression: {snippet}'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in parse_region and snippet not in validation_region:
            failures.append((TARGET.as_posix(), 0, f'missing vbv-fullness guardrail: {snippet}'))
    if has_in_order(
        parse_region,
        (
            'OPT("min-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->minVbvFullness);',
            'OPT("max-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxVbvFullness);',
        ),
    ) is False:
        failures.append((TARGET.as_posix(), 0, 'VBV fullness parsing must preserve the reviewed min-before-max parse order'))
    if has_in_order(
        validation_region,
        (
            'CHECK(param->minVbvFullness < 0 || param->minVbvFullness > 100,',
            '"min-vbv-fullness must be a fraction 0 - 100");',
            'CHECK(param->maxVbvFullness < 0 || param->maxVbvFullness > 100,',
            '"max-vbv-fullness must be a fraction 0 - 100");',
        ),
    ) is False:
        failures.append((TARGET.as_posix(), 0, 'VBV fullness validation must preserve the reviewed min-before-max range check order'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check vbv fullness parse safety guardrails')
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

    print('VBV fullness parse safety validated')


if __name__ == '__main__':
    main()
