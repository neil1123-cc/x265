#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    'sscanf(value, "%d", &p->hmeSearchMethod[0]) || sscanf(value, "%s", search[0])',
    'sscanf(value, "%d,%d,%d", &p->hmeRange[0], &p->hmeRange[1], &p->hmeRange[2]);',
    '3 == sscanf(value, "%d,%d,%d", &p->hmeSearchMethod[0], &p->hmeSearchMethod[1], &p->hmeSearchMethod[2])',
    '3 == sscanf(value, "%4[^,],%4[^,],%4[^,]", search[0], search[1], search[2])',
    'sscanf(value, "%d", &p->hmeSearchMethod[0]) == 1 || sscanf(value, "%4s", search[0]) == 1',
    'sscanf(value, "%d,%d,%d", &p->hmeRange[0], &p->hmeRange[1], &p->hmeRange[2]) != 3;',
    'sscanf(value, "%d,%d,%d%n", &p->hmeSearchMethod[0], &p->hmeSearchMethod[1], &p->hmeSearchMethod[2], &consumed)',
    'sscanf(value, "%4[^,],%4[^,],%4[^,]%n", search[0], search[1], search[2], &consumed)',
    'sscanf(value, "%d%n", &p->hmeSearchMethod[0], &consumed)',
    'sscanf(value, "%4[^,]%n", search[0], &consumed)',
    'sscanf(value, "%d,%d,%d%n", &p->hmeRange[0], &p->hmeRange[1], &p->hmeRange[2], &consumed)',
)
HELPER_REQUIRED_SNIPPETS = (
    'static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)',
    'static int parseHmeSearchMethodToken(const char* token, size_t length, bool& bError)',
    'static int parseOptionIntToken(const char* token, size_t length, bool& bError)',
    'static void assignParsedOptionLevels(const int parsed[3], int count, int target[3])',
    'int count = 0;',
    'const char* comma = std::strchr(token, \',\');',
    'char name[5];',
    "name[length] = '\\0';",
    'if (count == 1)',
    'target[0] = target[1] = target[2] = parsed[0];',
)
MAIN_REQUIRED_SNIPPETS = (
    'OPT("hme-search")',
    'int count = splitCommaOption(value, search, searchLengths, 3);',
    'if (count == 1 || count == 3)',
    'parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);',
    'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
    'parsed[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bLocalError);',
    'OPT("hme-range")',
    'if (splitCommaOption(value, range, rangeLengths, 3) != 3)',
    'parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);',
    'int parsed[3];',
)
HELPER_REGION_START = 'static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)'
HELPER_REGION_END = 'static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)'
MAIN_REGION_START = 'OPT("hme-search")'
MAIN_REGION_END = 'OPT("vbv-live-multi-pass")'


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
    helper_region = get_region(text, HELPER_REGION_START, HELPER_REGION_END)
    main_region = get_region(text, MAIN_REGION_START, MAIN_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden HME sscanf regression: {snippet}'))
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in helper_region:
            failures.append((TARGET.as_posix(), 0, f'missing HME sscanf guardrail: {snippet}'))
    for snippet in MAIN_REQUIRED_SNIPPETS:
        if snippet not in main_region:
            failures.append((TARGET.as_posix(), 0, f'missing HME sscanf guardrail: {snippet}'))
    if all(snippet in helper_region for snippet in HELPER_REQUIRED_SNIPPETS):
        if not has_in_order(
            helper_region,
            (
                'static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)',
                'int count = 0;',
                'const char* comma = std::strchr(token, \',\');',
                'parts[count] = token;',
                'lengths[count] = length;',
                'count++;',
                'token = comma ? comma + 1 : nullptr;',
                'static int parseHmeSearchMethodToken(const char* token, size_t length, bool& bError)',
                'char name[5];',
                "name[length] = '\\0';",
                'return parseName(name, x265_motion_est_names, bError);',
                'static void assignParsedOptionLevels(const int parsed[3], int count, int target[3])',
                'if (count == 1)',
                'target[0] = target[1] = target[2] = parsed[0];',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HME helper parsing must split comma-delimited tokens, normalize named search-method substrings, and fan out single-value levels with the reviewed helpers'))
    if all(snippet in main_region for snippet in MAIN_REQUIRED_SNIPPETS):
        if not has_in_order(
            main_region,
            (
                'OPT("hme-search")',
                'int count = splitCommaOption(value, search, searchLengths, 3);',
                'if (count == 1 || count == 3)',
                'if (bNumeric)',
                'int parsed[3];',
                'parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);',
                'if (!bLocalError)',
                'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                'parsed[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bLocalError);',
                'if (!bLocalError)',
                'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                'OPT("hme-range")',
                'if (splitCommaOption(value, range, rangeLengths, 3) != 3)',
                'bLocalError = true;',
                'int parsed[3];',
                'parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'HME option parsing must route hme-search and hme-range through the reviewed comma-splitting helpers instead of legacy sscanf tokenization'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check HME sscanf parsing guardrails in param.cpp')
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

    print('HME sscanf usage validated')


if __name__ == '__main__':
    main()
