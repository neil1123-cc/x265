#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    '#include <charconv>',
    'static bool parseOptionNonNegativeIntToken(const char* token, size_t length, int maxValue, int& value)',
    'static uint16_t parseOptionUint16Token(const char* token, size_t length, bool& bError)',
    'const char* digitsBegin = begin;',
    'std::from_chars_result parsed = std::from_chars(digitsBegin, end, magnitude, base);',
    'if (parsed.ec != std::errc() || parsed.ptr != end)',
    'int parsedValue = parseOptionIntToken(token, length, bLocalError);',
    'if (bLocalError || parsedValue < 0 || parsedValue > maxValue)',
    'if (!parseOptionNonNegativeIntToken(token, length, UINT16_MAX, value))',
    'return (uint16_t)value;',
    'static uint8_t parseOptionUint8Token(const char* token, size_t length, bool& bError)',
    'static uint8_t parseOptionUint8Value(const char* value, bool& bError)',
    'static uint8_t parseOptionUint8Value(const char* value, bool& bError)\n{\n    if (!value)\n    {\n        bError = true;\n        return 0;\n    }',
    'if (!parseOptionNonNegativeIntToken(token, length, UINT8_MAX, value))',
    'return (uint8_t)value;',
    'static uint32_t parseOptionUint32Token(const char* token, size_t length, bool& bError)',
    'if (!parseOptionNonNegativeIntToken(token, length, INT_MAX, value))',
    'return (uint32_t)value;',
    'uint32_t maxCUSize = parseOptionUint32Token(value, std::strlen(value), bMaxCUSizeError);',
    'p->maxCUSize = maxCUSize;',
    'uint16_t minLuma = parseOptionUint16Token(value, std::strlen(value), bMinLumaError);',
    'p->minLuma = minLuma;',
    'uint16_t maxLuma = parseOptionUint16Token(value, std::strlen(value), bMaxLumaError);',
    'p->maxLuma = maxLuma;',
    'static bool parseOptionUint16Pair(const char* value, char separatorChar, uint16_t& first, uint16_t& second)',
    "bool bLocalError = !parseOptionUint16Pair(value, ',', maxCLL, maxFALL);",
    'svtHevcParam->maxCLL = maxCLL;',
    'svtHevcParam->maxFALL = maxFALL;',
    'uint8_t predStructure = parseOptionUint8Value(value, bPredStructureError);',
    'svtHevcParam->predStructure = predStructure;',
)


def find_function(text, signature, next_signature):
    start = text.find(signature)
    if start == -1:
        return None
    end = text.find(next_signature, start)
    return text[start:end if end != -1 else None]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    uint16_function = find_function(
        text,
        'static uint16_t parseOptionUint16Token(const char* token, size_t length, bool& bError)',
        'static uint8_t parseOptionUint8Token',
    )
    int_token_function = find_function(
        text,
        'static int parseOptionIntToken(const char* token, size_t length, bool& bError)',
        'static const char* parsePresetIndexName',
    )
    uint8_function = find_function(
        text,
        'static uint8_t parseOptionUint8Token(const char* token, size_t length, bool& bError)',
        'static uint32_t parseOptionUint32Token',
    )
    uint32_function = find_function(
        text,
        'static uint32_t parseOptionUint32Token(const char* token, size_t length, bool& bError)',
        'static bool parseOptionIntPair',
    )
    if int_token_function is None or uint16_function is None or uint8_function is None or uint32_function is None:
        failures.append((TARGET.as_posix(), 0, 'missing uint token helper definition'))
        return failures

    if 'int value = parseOptionIntToken(token, length, bError);' in uint16_function:
        failures.append((TARGET.as_posix(), 0, 'forbidden uint16 token regression: wrapper must use shared non-negative token helper'))
    if 'int value = parseOptionIntToken(token, length, bError);' in uint8_function:
        failures.append((TARGET.as_posix(), 0, 'forbidden uint8 token regression: wrapper must use shared non-negative token helper'))
    if 'int value = parseOptionIntToken(token, length, bError);' in uint32_function:
        failures.append((TARGET.as_posix(), 0, 'forbidden uint32 token regression: wrapper must use shared non-negative token helper'))
    for snippet in (
        'char number[16];',
        'std::memcpy(number, token, length);',
        'return x265_atoi(number, bError);',
    ):
        if snippet in int_token_function:
            failures.append((TARGET.as_posix(), 0, f'forbidden uint token regression: {snippet}'))
    for snippet in (
        'OPT("min-luma") p->minLuma = parseOptionUint16Token(value, std::strlen(value), bError);',
        'OPT("max-luma") p->maxLuma = parseOptionUint16Token(value, std::strlen(value), bError);',
        'p->maxCLL = parseOptionUint16Token(value, leftLength, bLocalError);',
        'p->maxFALL = parseOptionUint16Token(separator + 1, rightLength, bLocalError);',
        'svtHevcParam->maxCLL = parseOptionUint16Token(value, leftLength, bLocalError);',
        'svtHevcParam->maxFALL = parseOptionUint16Token(separator + 1, rightLength, bLocalError);',
    ):
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden uint token regression: {snippet}'))

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing uint token guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check unsigned token helper safety guardrails')
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

    print('Unsigned token helper safety validated')


if __name__ == '__main__':
    main()
