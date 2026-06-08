#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
PARSE_REQUIRED_SNIPPETS = (
    'OPT("format")',
    'bool bFormatError = false;',
    'int format = parseOptionIntValue(value, bFormatError);',
    'bError |= bFormatError;',
    'if (!bFormatError)',
    'p->format = format;',
    'OPT("num-views")',
    'bool bNumViewsError = false;',
    'int numViews = parseOptionIntValue(value, bNumViewsError);',
    'bError |= bNumViewsError;',
    'if (!bNumViewsError)',
    'p->numViews = numViews;',
    'OPT("scc")',
    'bool bSccError = false;',
    'int bEnableSCC = parseOptionIntValue(value, bSccError);',
    'bError |= bSccError;',
    'if (!bSccError)',
    'p->bEnableSCC = bEnableSCC;',
)
VALIDATION_REQUIRED_SNIPPETS = (
    'CHECK((param->numViews < 1), "Multi-View Encoding requires at least one view");',
    'CHECK((param->numViews > 2), "Multi-View Encoding currently support only 2 views");',
    'CHECK((param->format < 0 || param->format > 2), "Multi-View input format must be 0 (normal), 1 (side-by-side), or 2 (over-under)");',
    'CHECK(param->format && param->numViews <= 1, "Multi-View input format requires more than one view");',
)
FORBIDDEN_SNIPPETS = (
    'OPT("format")\n            p->format = x265_atoi(value, bError);',
    'p->format = x265_atoi(value, bError);',
    'p->numViews = x265_atoi(value, bError);',
    'p->bEnableSCC = x265_atoi(value, bError);',
)
PARSE_REGION_START = 'OPT("format")'
PARSE_REGION_END = 'OPT("frame-rc")'
VALIDATION_REGION_START = 'CHECK((param->numViews < 1), "Multi-View Encoding requires at least one view");'
VALIDATION_REGION_END = 'if (param->numViews > 1)'


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
            failures.append((TARGET.as_posix(), 0, 'forbidden multiview/SCC regression: invalid values must not overwrite prior state'))
            return failures
    for snippet in PARSE_REQUIRED_SNIPPETS:
        if snippet not in parse_region:
            failures.append((TARGET.as_posix(), 0, f'missing multiview/SCC guardrail: {snippet}'))
    for snippet in VALIDATION_REQUIRED_SNIPPETS:
        if snippet not in validation_region:
            failures.append((TARGET.as_posix(), 0, f'missing multiview/SCC guardrail: {snippet}'))
    if all(snippet in parse_region for snippet in PARSE_REQUIRED_SNIPPETS):
        if not has_in_order(
            parse_region,
            (
                'OPT("format")',
                'bool bFormatError = false;',
                'int format = parseOptionIntValue(value, bFormatError);',
                'bError |= bFormatError;',
                'if (!bFormatError)',
                'p->format = format;',
                'OPT("num-views")',
                'bool bNumViewsError = false;',
                'int numViews = parseOptionIntValue(value, bNumViewsError);',
                'bError |= bNumViewsError;',
                'if (!bNumViewsError)',
                'p->numViews = numViews;',
                'OPT("scc")',
                'bool bSccError = false;',
                'int bEnableSCC = parseOptionIntValue(value, bSccError);',
                'bError |= bSccError;',
                'if (!bSccError)',
                'p->bEnableSCC = bEnableSCC;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Multiview/SCC parsing must stage parsed integers and only publish them after the reviewed error gates succeed'))
    if all(snippet in validation_region for snippet in VALIDATION_REQUIRED_SNIPPETS):
        if not has_in_order(
            validation_region,
            (
                'CHECK((param->numViews < 1), "Multi-View Encoding requires at least one view");',
                'CHECK((param->numViews > 2), "Multi-View Encoding currently support only 2 views");',
                'CHECK((param->format < 0 || param->format > 2), "Multi-View input format must be 0 (normal), 1 (side-by-side), or 2 (over-under)");',
                'CHECK(param->format && param->numViews <= 1, "Multi-View input format requires more than one view");',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Multiview validation must preserve the reviewed numViews/format constraint ordering'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check multiview and SCC parse safety guardrails')
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

    print('Multiview and SCC parse safety validated')


if __name__ == '__main__':
    main()
