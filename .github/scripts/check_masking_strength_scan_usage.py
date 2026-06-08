#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    '3 == sscanf(value, "%d,%lf,%lf", &window1[0], &refQpDelta1[0], &nonRefQpDelta1[0])',
    '18 == sscanf(value, "%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf"',
    '6 == sscanf(value, "%d,%lf,%lf,%d,%lf,%lf", &window1[0], &refQpDelta1[0], &nonRefQpDelta1[0], &window2[0], &refQpDelta2[0], &nonRefQpDelta2[0])',
    '36 == sscanf(value, "%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf"',
    '3 == sscanf(value, "%d,%lf,%lf%n", &window1[0], &refQpDelta1[0], &nonRefQpDelta1[0], &consumed)',
    '18 == sscanf(value, "%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf%n"',
    '6 == sscanf(value, "%d,%lf,%lf,%d,%lf,%lf%n", &window1[0], &refQpDelta1[0], &nonRefQpDelta1[0], &window2[0], &refQpDelta2[0], &nonRefQpDelta2[0], &consumed)',
    '36 == sscanf(value, "%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf,%d,%lf,%lf%n"',
    'window[i] = parseOptionIntToken(parts[i * 3], lengths[i * 3], bWindowError);',
    '!parseOptionDoubleToken(parts[i * 3 + 1], lengths[i * 3 + 1], refQpDelta[i])',
    '!parseOptionDoubleToken(parts[i * 3 + 2], lengths[i * 3 + 2], nonRefQpDelta[i])',
)
HELPER_REQUIRED_SNIPPETS = (
    'static bool parseOptionDoubleToken(const char* token, size_t length, double& value)',
    'static bool parseMaskingStrengthTriples(const char* value, int expectedTriples, int window[], double refQpDelta[], double nonRefQpDelta[])',
    'int parsedWindow[12];',
    'double parsedRefQpDelta[12];',
    'double parsedNonRefQpDelta[12];',
    'const int expectedValues = expectedTriples * 3;',
    'if (splitCommaOption(value, parts, lengths, expectedValues) != expectedValues)',
    'parsedWindow[i] = parseOptionIntToken(parts[i * 3], lengths[i * 3], bWindowError);',
    'if (bWindowError ||',
    'window[i] = parsedWindow[i];',
    'refQpDelta[i] = parsedRefQpDelta[i];',
    'nonRefQpDelta[i] = parsedNonRefQpDelta[i];',
    'return true;',
)
CALLER_REQUIRED_SNIPPETS = (
    'bool parseMaskingStrength(x265_param* p, const char* value)',
    'if (p->bEnableSceneCutAwareQp == FORWARD)',
    'if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))',
    'else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))',
    'else if (p->bEnableSceneCutAwareQp == BACKWARD)',
    'if (parseMaskingStrengthTriples(value, 2, window2, refQpDelta2, nonRefQpDelta2))',
    'else if (parseMaskingStrengthTriples(value, 12, window2, refQpDelta2, nonRefQpDelta2))',
    'applyCompactMaskingStrength(window2[1], refQpDelta2[1], nonRefQpDelta2[1],',
    'p->fwdScenecutWindow[i] = window2[i];',
    'p->fwdRefQpDelta[i] = refQpDelta2[i];',
    'p->bwdScenecutWindow[i] = window2[i + 6];',
    'p->bwdRefQpDelta[i] = refQpDelta2[i + 6];',
    'return bError;',
)
HELPER_REGION_START = 'static bool parseOptionDoubleToken(const char* token, size_t length, double& value)'
HELPER_REGION_END = 'static void applyCompactMaskingStrength'
CALLER_REGION_START = 'bool parseMaskingStrength(x265_param* p, const char* value)'
CALLER_REGION_END = 'void x265_copy_params'


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
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden masking-strength scan regression: {snippet}'))
            return failures
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in helper_region:
            failures.append((TARGET.as_posix(), 0, f'missing masking-strength scan guardrail: {snippet}'))
    for snippet in CALLER_REQUIRED_SNIPPETS:
        if snippet not in caller_region:
            failures.append((TARGET.as_posix(), 0, f'missing masking-strength scan guardrail: {snippet}'))
    if all(snippet in helper_region for snippet in HELPER_REQUIRED_SNIPPETS):
        if not has_in_order(
            helper_region,
            (
                'const int expectedValues = expectedTriples * 3;',
                'if (expectedTriples <= 0 || expectedTriples > 12)',
                'return false;',
                'if (splitCommaOption(value, parts, lengths, expectedValues) != expectedValues)',
                'return false;',
                'for (int i = 0; i < expectedTriples; i++)',
                'bool bWindowError = false;',
                'parsedWindow[i] = parseOptionIntToken(parts[i * 3], lengths[i * 3], bWindowError);',
                '!parseOptionDoubleToken(parts[i * 3 + 1], lengths[i * 3 + 1], parsedRefQpDelta[i])',
                '!parseOptionDoubleToken(parts[i * 3 + 2], lengths[i * 3 + 2], parsedNonRefQpDelta[i])',
                'return false;',
                'for (int i = 0; i < expectedTriples; i++)',
                'window[i] = parsedWindow[i];',
                'refQpDelta[i] = parsedRefQpDelta[i];',
                'nonRefQpDelta[i] = parsedNonRefQpDelta[i];',
                'return true;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseMaskingStrengthTriples must finish staged token parsing before publishing any window or delta values'))
    if all(snippet in caller_region for snippet in CALLER_REQUIRED_SNIPPETS):
        if not has_in_order(
            caller_region,
            (
                'if (p->bEnableSceneCutAwareQp == FORWARD)',
                'if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))',
                'applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],',
                'else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))',
                'applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,',
                'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                'bError = true;',
                'else if (p->bEnableSceneCutAwareQp == BACKWARD)',
                'if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))',
                'applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],',
                'else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))',
                'applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,',
                'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                'bError = true;',
                'else if (p->bEnableSceneCutAwareQp == BI_DIRECTIONAL)',
                'int window2[12];',
                'double refQpDelta2[12], nonRefQpDelta2[12];',
                'if (parseMaskingStrengthTriples(value, 2, window2, refQpDelta2, nonRefQpDelta2))',
                'applyCompactMaskingStrength(window2[0], refQpDelta2[0], nonRefQpDelta2[0],',
                'applyCompactMaskingStrength(window2[1], refQpDelta2[1], nonRefQpDelta2[1],',
                'else if (parseMaskingStrengthTriples(value, 12, window2, refQpDelta2, nonRefQpDelta2))',
                'p->fwdMaxScenecutWindow = 0;',
                'p->bwdMaxScenecutWindow = 0;',
                'for (int i = 0; i < 6; i++)',
                'p->fwdScenecutWindow[i] = window2[i];',
                'p->fwdRefQpDelta[i] = refQpDelta2[i];',
                'p->fwdNonRefQpDelta[i] = nonRefQpDelta2[i];',
                'p->bwdScenecutWindow[i] = window2[i + 6];',
                'p->bwdRefQpDelta[i] = refQpDelta2[i + 6];',
                'p->bwdNonRefQpDelta[i] = nonRefQpDelta2[i + 6];',
                'p->fwdMaxScenecutWindow += p->fwdScenecutWindow[i];',
                'p->bwdMaxScenecutWindow += p->bwdScenecutWindow[i];',
                'x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \\n");',
                'bError = true;',
                'return bError;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseMaskingStrength must preserve the reviewed compact-before-expanded branch order and directional array publishing flow'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check masking-strength sscanf guardrails in param.cpp')
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

    print('Masking-strength scan usage validated')


if __name__ == '__main__':
    main()
