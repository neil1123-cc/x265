#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("vbv-end-fr-adj") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvEndFrameAdjust);',
    'CHECK(param->vbvEndFrameAdjust < 0 || param->vbvEndFrameAdjust > 1,',
    '"Valid vbv-end-fr-adj must be a fraction 0 - 1");',
    'CHECK(param->vbvBufferEnd > 0 && param->vbvEndFrameAdjust == 0,',
    '"vbv-end-fr-adj must be greater than 0 when vbv-end is enabled");',
)
FORBIDDEN_SNIPPETS = (
    'CHECK(param->vbvEndFrameAdjust < 0,',
    'OPT("vbv-end-fr-adj") p->vbvEndFrameAdjust = atof(value);',
)
PARSE_REGION_START = 'OPT("vbv-end-fr-adj") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvEndFrameAdjust);'
PARSE_REGION_END = 'OPT("copy-pic")'
VALIDATION_REGION_START = 'CHECK(param->vbvEndFrameAdjust < 0 || param->vbvEndFrameAdjust > 1,'
VALIDATION_REGION_END = 'if ((param->rc.vbvBufferSize > 0 || param->rc.vbvMaxBitrate > 0) && param->bThreadedME)'


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
            failures.append((TARGET.as_posix(), 0, f'forbidden vbv-end-fr-adj regression: {snippet}'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in parse_region and snippet not in validation_region:
            failures.append((TARGET.as_posix(), 0, f'missing vbv-end-fr-adj guardrail: {snippet}'))
    if has_in_order(
        validation_region,
        (
            'CHECK(param->vbvEndFrameAdjust < 0 || param->vbvEndFrameAdjust > 1,',
            '"Valid vbv-end-fr-adj must be a fraction 0 - 1");',
            'CHECK(param->vbvBufferEnd > 0 && param->vbvEndFrameAdjust == 0,',
            '"vbv-end-fr-adj must be greater than 0 when vbv-end is enabled");',
        ),
    ) is False:
        failures.append((TARGET.as_posix(), 0, 'vbv-end-fr-adj validation must keep the reviewed range check ahead of the vbv-end dependency check'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check vbv-end-fr-adj safety guardrails')
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

    print('VBV end frame adjust safety validated')


if __name__ == '__main__':
    main()
