#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/input/lavf.cpp')
FORBIDDEN_SNIPPETS = (
    'if (bError)',
)
REQUIRED_SNIPPETS = (
    'static bool parseLavfIntValue(const char* value, int& parsedValue)',
    'if (!value)',
    'int valueAsInt = x265_atoi(value, bError);',
    'if (bError || valueAsInt < 0)',
    'const char* metadataValue = entry->value ? entry->value : "<null>";',
    'if (!parseLavfIntValue(entry->value, frameCount))',
    'general_log(nullptr, "lavf", X265_LOG_WARNING, "Ignoring invalid NUMBER_OF_FRAMES metadata: %s\\n", metadataValue);',
    'info.frameCount = 0;',
    'info.frameCount = frameCount;',
)
HELPER_REGION_START = 'static bool parseLavfIntValue(const char* value, int& parsedValue)'
HELPER_REGION_END = 'static enum AVPixelFormat convertPixelFormat'
CALLER_REGION_START = 'if (!s->nb_frames) {'
CALLER_REGION_END = '/* show video info */'


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
    caller_region = get_region(text, CALLER_REGION_START, CALLER_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in helper_region and 'if (bError || valueAsInt < 0)' not in helper_region:
            failures.append((TARGET.as_posix(), 0, f'forbidden lavf framecount parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in helper_region and snippet not in caller_region:
            failures.append((TARGET.as_posix(), 0, f'missing lavf framecount parse guardrail: {snippet}'))
    helper_order = (
        'static bool parseLavfIntValue(const char* value, int& parsedValue)',
        'if (!value)',
        'int valueAsInt = x265_atoi(value, bError);',
        'if (bError || valueAsInt < 0)',
        'parsedValue = valueAsInt;',
    )
    if all(snippet in helper_region for snippet in helper_order):
        if not has_in_order(helper_region, helper_order):
            failures.append((TARGET.as_posix(), 0, 'lavf framecount helper must preserve the reviewed null-check and non-negative parse flow before publishing parsedValue'))
    caller_order = (
        'const char* metadataValue = entry->value ? entry->value : "<null>";',
        'if (!parseLavfIntValue(entry->value, frameCount))',
        'general_log(nullptr, "lavf", X265_LOG_WARNING, "Ignoring invalid NUMBER_OF_FRAMES metadata: %s\\n", metadataValue);',
        'info.frameCount = 0;',
        'info.frameCount = frameCount;',
    )
    if all(snippet in caller_region for snippet in caller_order):
        if not has_in_order(caller_region, caller_order):
            failures.append((TARGET.as_posix(), 0, 'lavf framecount metadata handling must preserve the reviewed parse/log/reset/success assignment ordering'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check lavf framecount parse safety guardrails')
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

    print('Lavf framecount parse safety validated')


if __name__ == '__main__':
    main()
