#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/scalinglist.cpp')
FORBIDDEN_SNIPPETS = (
    'if (std::fscanf(fp, "%d,", &data) != 1)',
)
REQUIRED_SNIPPETS = (
    'static bool parseScalingListIntToken(const char* token, int& value)',
    'int parsedValue = x265_atoi(token, bError);',
    'if (bError || parsedValue <= 0)',
    'value = parsedValue;',
    'static bool readScalingListValue(FILE* fp, int& data)',
    'char token[32];',
    'if (std::fscanf(fp, " %31[^,\\r\\n],", token) != 1)',
    'return parseScalingListIntToken(token, data);',
    'if (!readScalingListValue(fp, data))',
    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);',
    'm_scalingListDC[sizeIdc][listIdc] = src[0];',
    'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);',
)
FORBIDDEN_SNIPPETS += (
    'data = x265_atoi(token, bError);',
    'int parsedData = x265_atoi(token, bError);',
)
HELPER_REGION_START = 'static bool parseScalingListIntToken(const char* token, int& value)'
HELPER_REGION_END = 'namespace X265_NS {'
CALLER_REGION_START = 'for (int i = 0; i < size; i++)'
CALLER_REGION_END = 'scalingListDC[sizeIdc][listIdc] = data;'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    return text[start:end + len(end_marker)]


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
    caller_region = get_region(text, CALLER_REGION_START, CALLER_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden scaling-list parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in helper_region and snippet not in caller_region:
            failures.append((TARGET.as_posix(), 0, f'missing scaling-list parse guardrail: {snippet}'))
    helper_order = (
        'static bool parseScalingListIntToken(const char* token, int& value)',
        'int parsedValue = x265_atoi(token, bError);',
        'if (bError || parsedValue <= 0)',
        'value = parsedValue;',
        'static bool readScalingListValue(FILE* fp, int& data)',
        'char token[32];',
        'if (std::fscanf(fp, " %31[^,\\r\\n],", token) != 1)',
        'return parseScalingListIntToken(token, data);',
    )
    if all(snippet in helper_region for snippet in helper_order):
        if not has_in_order(helper_region, helper_order):
            failures.append((TARGET.as_posix(), 0, 'Scaling-list helpers must preserve the reviewed token-parse flow before publishing parsed values'))
    caller_order = (
        'for (int i = 0; i < size; i++)',
        'int data;',
        'if (!readScalingListValue(fp, data))',
        'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after matrix parse failure\\n", filename);',
        'src[i] = data;',
        'm_scalingListDC[sizeIdc][listIdc] = src[0];',
        'int data;',
        'if (!readScalingListValue(fp, data))',
        'x265_log_file(nullptr, X265_LOG_WARNING, "can\'t close scaling list file %s after DC parse failure\\n", filename);',
        'scalingListDC[sizeIdc][listIdc] = data;',
    )
    if all(snippet in caller_region for snippet in caller_order):
        if not has_in_order(caller_region, caller_order):
            failures.append((TARGET.as_posix(), 0, 'Scaling-list parsing must preserve the reviewed matrix and DC read/close ordering around readScalingListValue failures'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed scaling-list parsing guardrails')
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

    print('Scaling-list parse usage validated')


if __name__ == '__main__':
    main()
