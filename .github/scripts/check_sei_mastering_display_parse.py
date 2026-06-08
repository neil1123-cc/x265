#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/sei.h')
FORBIDDEN_SNIPPETS = (
    'return std::sscanf(value, "G(%hu,%hu)B(%hu,%hu)R(%hu,%hu)WP(%hu,%hu)L(%u,%u)",',
    'return std::sscanf(value, "G(%hu,%hu)B(%hu,%hu)R(%hu,%hu)WP(%hu,%hu)L(%u,%u)%n",',
)
HELPER_REQUIRED_SNIPPETS = (
    'static bool parseSeiUnsignedToken(const char*& cursor, uint32_t& value)',
    'static bool consumeSeiLiteral(const char*& cursor, const char* literal)',
)
PARSE_REQUIRED_SNIPPETS = (
    'class SEIMasteringDisplayColorVolume : public SEI',
    'bool parse(const char* value)',
    'const char* cursor = value;',
    'uint32_t values[10];',
    'if (!consumeSeiLiteral(cursor, "G(") ||',
    '!consumeSeiLiteral(cursor, ")L(") ||',
    '!parseSeiUnsignedToken(cursor, values[9]) ||',
    "!consumeSeiLiteral(cursor, \")\") ||",
    "*cursor != '\\0')",
    'for (int i = 0; i < 3; i++)',
    'if (values[i * 2] > UINT16_MAX || values[i * 2 + 1] > UINT16_MAX)',
    'displayPrimaryX[i] = (uint16_t)values[i * 2];',
    'displayPrimaryY[i] = (uint16_t)values[i * 2 + 1];',
    'if (values[6] > UINT16_MAX || values[7] > UINT16_MAX)',
    'whitePointX = (uint16_t)values[6];',
    'whitePointY = (uint16_t)values[7];',
    'maxDisplayMasteringLuminance = values[8];',
    'minDisplayMasteringLuminance = values[9];',
    'return true;',
)
REGION_START = 'class SEIMasteringDisplayColorVolume : public SEI'
REGION_END = 'class SEIContentLightLevel : public SEI'


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
    region = get_region(text, REGION_START, REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in region:
            failures.append((TARGET.as_posix(), 0, f'forbidden mastering-display parse regression: {snippet}'))
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing mastering-display parse guardrail: {snippet}'))
    for snippet in PARSE_REQUIRED_SNIPPETS:
        if snippet not in region:
            failures.append((TARGET.as_posix(), 0, f'missing mastering-display parse guardrail: {snippet}'))
    if all(snippet in region for snippet in PARSE_REQUIRED_SNIPPETS):
        if not has_in_order(
            region,
            (
                'const char* cursor = value;',
                'uint32_t values[10];',
                'if (!consumeSeiLiteral(cursor, "G(") ||',
                '!consumeSeiLiteral(cursor, ")L(") ||',
                '!parseSeiUnsignedToken(cursor, values[9]) ||',
                "!consumeSeiLiteral(cursor, \")\") ||",
                "*cursor != '\\0')",
                'for (int i = 0; i < 3; i++)',
                'if (values[i * 2] > UINT16_MAX || values[i * 2 + 1] > UINT16_MAX)',
                'displayPrimaryX[i] = (uint16_t)values[i * 2];',
                'displayPrimaryY[i] = (uint16_t)values[i * 2 + 1];',
                'if (values[6] > UINT16_MAX || values[7] > UINT16_MAX)',
                'whitePointX = (uint16_t)values[6];',
                'whitePointY = (uint16_t)values[7];',
                'maxDisplayMasteringLuminance = values[8];',
                'minDisplayMasteringLuminance = values[9];',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'SEIMasteringDisplayColorVolume::parse must fully consume and validate the mastering-display token stream before publishing white-point and luminance values'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check strict mastering-display parsing guardrails')
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

    print('Mastering-display parse usage validated')


if __name__ == '__main__':
    main()
