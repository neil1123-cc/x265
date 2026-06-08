#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
REQUIRED_SNIPPETS = (
    'static bool splitOptionPair(const char* value, char separatorChar,',
    'if (!value)',
    'const char* separator = std::strchr(value, separatorChar);',
    'if (!separator)',
    'firstToken = value;',
    'firstLength = (size_t)(separator - value);',
    'secondToken = separator + 1;',
    'secondLength = std::strlen(secondToken);',
    'return firstLength && secondLength;',
    'static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)',
    'if (!splitOptionPair(value, separatorChar, firstToken, firstLength, secondToken, secondLength))',
    'int parsedFirst = parseOptionIntToken(firstToken, firstLength, bLocalError);',
    'int parsedSecond = parseOptionIntToken(secondToken, secondLength, bLocalError);',
    'if (bLocalError)',
    'first = parsedFirst;',
    'second = parsedSecond;',
    'static bool parseOptionUintPair(const char* value, char separatorChar, uint32_t& first, uint32_t& second)',
    'if (!parseOptionIntPair(value, separatorChar, parsedFirst, parsedSecond) || parsedFirst < 0 || parsedSecond < 0)',
    'static bool parseOptionIntQuad(const char* value, int& first, int& second, int& third, int& fourth)',
    'int parsedThird = parseOptionIntToken(parts[2], lengths[2], bLocalError);',
    'int parsedFourth = parseOptionIntToken(parts[3], lengths[3], bLocalError);',
    'third = parsedThird;',
    'fourth = parsedFourth;',
    "bError |= !parseOptionIntPair(value, 'x', p->sourceWidth, p->sourceHeight);",
    "if (!parseOptionIntPair(value, 'x', sourceWidth, sourceHeight))",
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

    int_pair = find_function(
        text,
        'static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)',
        'static bool parseOptionUintPair',
    )
    split_pair = find_function(
        text,
        'static bool splitOptionPair(const char* value, char separatorChar,',
        'static uint8_t parseOptionUint8Token',
    )
    uint_pair = find_function(
        text,
        'static bool parseOptionUintPair(const char* value, char separatorChar, uint32_t& first, uint32_t& second)',
        'static bool parseOptionIntQuad',
    )
    if split_pair is None or int_pair is None or uint_pair is None:
        failures.append((TARGET.as_posix(), 0, 'missing pair helper definition'))
        return failures

    if 'return firstLength && secondLength;' not in split_pair:
        failures.append((TARGET.as_posix(), 0, 'forbidden pair parse regression: missing empty-side guard'))
    if 'first = parseOptionIntToken(firstToken, firstLength, bLocalError);' in int_pair or 'second = parseOptionIntToken(secondToken, secondLength, bLocalError);' in int_pair:
        failures.append((TARGET.as_posix(), 0, 'forbidden pair parse regression: direct pair helper writes'))
    if 'parsedFirst < 0 || parsedSecond < 0' not in uint_pair:
        failures.append((TARGET.as_posix(), 0, 'forbidden uint pair regression: missing negative-value guard'))

    quad = find_function(
        text,
        'static bool parseOptionIntQuad(const char* value, int& first, int& second, int& third, int& fourth)',
        'static bool parseOptionDoubleToken',
    )
    if quad is None:
        failures.append((TARGET.as_posix(), 0, 'missing quad helper definition'))
    elif any(snippet in quad for snippet in (
        'first = parseOptionIntToken(parts[0], lengths[0], bLocalError);',
        'second = parseOptionIntToken(parts[1], lengths[1], bLocalError);',
        'third = parseOptionIntToken(parts[2], lengths[2], bLocalError);',
        'fourth = parseOptionIntToken(parts[3], lengths[3], bLocalError);',
    )):
        failures.append((TARGET.as_posix(), 0, 'forbidden quad parse regression: direct quad helper writes'))

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing pair parse guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check pair parse helper safety guardrails')
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

    print('Pair parse helper safety validated')


if __name__ == '__main__':
    main()
