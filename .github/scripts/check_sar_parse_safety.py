#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'OPT("sar")',
    'bool bSarNameError = false;',
    'int aspectRatioIdc = parseName(value, x265_sar_names, bSarNameError);',
    'if (!bSarNameError)',
    'p->vui.aspectRatioIdc = aspectRatioIdc;',
    'int sarWidth = 0;',
    'int sarHeight = 0;',
    "bool bLocalError = !parseOptionIntPair(value, ':', sarWidth, sarHeight);",
    'if (!bLocalError)',
    'p->vui.aspectRatioIdc = X265_EXTENDED_SAR;',
    'p->vui.sarWidth = sarWidth;',
    'p->vui.sarHeight = sarHeight;',
    'bError |= bLocalError;',
    'CHECK((param->vui.aspectRatioIdc < 0',
    '&& param->vui.aspectRatioIdc != X265_EXTENDED_SAR,',
    'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarWidth <= 0,',
    'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarHeight <= 0,',
)
FORBIDDEN_SNIPPETS = (
    'OPT("sar")\n    {\n        p->vui.aspectRatioIdc = parseName(value, x265_sar_names, bError);\n        if (bError)\n        {\n            p->vui.aspectRatioIdc = X265_EXTENDED_SAR;',
    "const char* separator = std::strchr(value, ':');",
    '        bError = bLocalError;',
)
PARSE_REGION_START = 'OPT("sar")'
PARSE_REGION_END = 'OPT("overscan")'
VALIDATION_REGION_START = 'CHECK((param->vui.aspectRatioIdc < 0'
VALIDATION_REGION_END = 'CHECK(param->vui.videoFormat < 0 || param->vui.videoFormat > 5,'


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
    failures = []
    if 'OPT("sar")' not in text:
        return [(TARGET.as_posix(), 0, 'missing sar option block')]

    sar_block = get_region(text, PARSE_REGION_START, PARSE_REGION_END)
    validation_region = get_region(text, VALIDATION_REGION_START, VALIDATION_REGION_END)
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in sar_block:
            failures.append((TARGET.as_posix(), 0, 'forbidden sar regression: invalid SAR input must not partially mutate VUI state'))
            return failures
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in sar_block and snippet not in validation_region:
            failures.append((TARGET.as_posix(), 0, f'missing sar guardrail: {snippet}'))
    if has_in_order(
        sar_block,
        (
            'OPT("sar")',
            'bool bSarNameError = false;',
            'int aspectRatioIdc = parseName(value, x265_sar_names, bSarNameError);',
            'if (!bSarNameError)',
            'p->vui.aspectRatioIdc = aspectRatioIdc;',
            'else',
            'int sarWidth = 0;',
            'int sarHeight = 0;',
            "bool bLocalError = !parseOptionIntPair(value, ':', sarWidth, sarHeight);",
            'if (!bLocalError)',
            'p->vui.aspectRatioIdc = X265_EXTENDED_SAR;',
            'p->vui.sarWidth = sarWidth;',
            'p->vui.sarHeight = sarHeight;',
            'bError |= bLocalError;',
        ),
    ) is False:
        failures.append((TARGET.as_posix(), 0, 'SAR parsing must preserve the reviewed named-SAR fallback ordering before publishing extended SAR state'))
    if has_in_order(
        validation_region,
        (
            'CHECK((param->vui.aspectRatioIdc < 0',
            '&& param->vui.aspectRatioIdc != X265_EXTENDED_SAR,',
            'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarWidth <= 0,',
            'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarHeight <= 0,',
        ),
    ) is False:
        failures.append((TARGET.as_posix(), 0, 'SAR validation must preserve the reviewed aspect-ratio-idc, width, and height guard ordering'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check SAR parse safety guardrails')
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

    print('SAR parse safety validated')


if __name__ == '__main__':
    main()
