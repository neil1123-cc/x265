#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/ratecontrol.cpp')
FORBIDDEN_SNIPPETS = (
    'e = sscanf(p, " in:%d out:%d", &frameNumber, &encodeOrder);',
    'e = sscanf(p, " in:%d out:%d%n", &frameNumber, &encodeOrder, &consumedPrefix);',
)
HELPER_REQUIRED_SNIPPETS = (
    'static bool parseStatsPrefix(const char* p, int& frameNumber, int& encodeOrder, int& consumedPrefix)',
    'if (!p)',
    "while (*cursor == ' ' || *cursor == '\\r' || *cursor == '\\n')",
    'if (std::strncmp(cursor, "in:", 3))',
    'if (!tokenLength || tokenLength >= 16 || std::strncmp(end, " out:", 5))',
    'if (!parseRateControlIntToken(token, frameNumber))',
    "if (!tokenLength || tokenLength >= 16 || *end != ' ')",
    'if (!parseRateControlIntToken(token, encodeOrder))',
    'consumedPrefix = (int)(end - p);',
    'return consumedPrefix > 0;',
)
CALLER_REQUIRED_SNIPPETS = (
    'int frameNumber = -1;',
    'int encodeOrder = -1;',
    'int e = -1;',
    'int consumedPrefix = 0;',
    'if (!parseStatsPrefix(p, frameNumber, encodeOrder, consumedPrefix))',
    'if (frameNumber < 0 || frameNumber >= m_numEntries)',
    'if (encodeOrder < 0 || encodeOrder >= m_numEntries)',
    'e = 2;',
    'rce = &m_rce2Pass[encodeOrder];',
)
HELPER_REGION_START = 'static bool parseStatsPrefix(const char* p, int& frameNumber, int& encodeOrder, int& consumedPrefix)'
HELPER_REGION_END = 'static bool parseStatsLineLabel(const char*& cursor, const char* label)'
CALLER_REGION_START = 'int frameNumber = -1;'
CALLER_REGION_END = 'rce = &m_rce2Pass[encodeOrder];'


def get_region(text, start_marker, end_marker):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker))
    if -1 in (start, end):
        return text
    end += len(end_marker)
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
    caller_region = get_region(text, CALLER_REGION_START, CALLER_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ratecontrol stats-prefix parse regression: {snippet}'))
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in helper_region:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol stats-prefix parse guardrail: {snippet}'))
    for snippet in CALLER_REQUIRED_SNIPPETS:
        if snippet not in caller_region:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol stats-prefix parse guardrail: {snippet}'))
    if all(snippet in helper_region for snippet in HELPER_REQUIRED_SNIPPETS):
        if not has_in_order(helper_region, HELPER_REQUIRED_SNIPPETS):
            failures.append((TARGET.as_posix(), 0, 'parseStatsPrefix must tokenize and validate the frame and encode-order prefix before publishing consumedPrefix'))
    if all(snippet in caller_region for snippet in CALLER_REQUIRED_SNIPPETS):
        if not has_in_order(
            caller_region,
            (
                'int frameNumber = -1;',
                'int encodeOrder = -1;',
                'int e = -1;',
                'int consumedPrefix = 0;',
                'if (!parseStatsPrefix(p, frameNumber, encodeOrder, consumedPrefix))',
                'e = -1;',
                'e = 2;',
                'if (frameNumber < 0 || frameNumber >= m_numEntries)',
                'if (encodeOrder < 0 || encodeOrder >= m_numEntries)',
                'rce = &m_rce2Pass[encodeOrder];',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'stats-file loading must derive frameNumber and encodeOrder from parseStatsPrefix before accepting the prefix and indexing m_rce2Pass'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed ratecontrol stats-prefix parsing guardrails')
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

    print('Ratecontrol stats-prefix parse usage validated')


if __name__ == '__main__':
    main()
