#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/ratecontrol.cpp')
FORBIDDEN_SNIPPETS = (
    'if (p && sscanf(p, opt "=%d" , &i) && param_val != i)',
    'if (p && sscanf(p, opt "=%d%n" , &i, &consumedOpt) == 1 && (p[consumedOpt] == \' \' || p[consumedOpt] == \'\\0\') && param_val != i)',
)
HELPER_REQUIRED_SNIPPETS = (
    'static bool parseRateControlIntToken(const char* token, int& value);',
    'static bool parseFirstPassOptionValue(const char* p, const char* opt, int& value)',
    'size_t optLength = std::strlen(opt);',
    "if (std::strncmp(p, opt, optLength) || p[optLength] != '=')",
    "while (*end && *end != ' ')",
    'char token[16];',
    'return parseRateControlIntToken(token, value) && (*end == \' \' || *end == \'\\0\');',
)
MACRO_REQUIRED_SNIPPETS = (
    'bool bParsedFirstPassValue = false;',
    'if (p)',
    'bParsedFirstPassValue = parseFirstPassOptionValue(p, opt, i);',
    'if (!bParsedFirstPassValue || param_val != i)',
    'if (bErr)',
    'if (p && !bParsedFirstPassValue)',
    'x265_log(m_param, X265_LOG_ERROR, opt " specified in stats file not valid\\n");',
    'x265_log(m_param, X265_LOG_ERROR, "different " opt " setting than first pass (%d vs %d)\\n", param_val, i);',
)
HELPER_REGION_START = 'static bool parseRateControlIntToken(const char* token, int& value);'
HELPER_REGION_END = '#define CMP_OPT_FIRST_PASS(opt, param_val)\\'
MACRO_REGION_START = '#define CMP_OPT_FIRST_PASS(opt, param_val)\\'
MACRO_REGION_END = 'static bool parseStatsPrefix(const char* p, int& frameNumber, int& encodeOrder, int& consumedPrefix)'


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
    macro_region = get_region(text, MACRO_REGION_START, MACRO_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ratecontrol first-pass parse regression: {snippet}'))
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in helper_region:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol first-pass parse guardrail: {snippet}'))
    for snippet in MACRO_REQUIRED_SNIPPETS:
        if snippet not in macro_region:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol first-pass parse guardrail: {snippet}'))
    if all(snippet in helper_region for snippet in HELPER_REQUIRED_SNIPPETS):
        if not has_in_order(helper_region, HELPER_REQUIRED_SNIPPETS):
            failures.append((TARGET.as_posix(), 0, 'parseFirstPassOptionValue must isolate the option token before validating and comparing the parsed integer value'))
    if all(snippet in macro_region for snippet in MACRO_REQUIRED_SNIPPETS):
        if not has_in_order(
            macro_region,
            (
                'bool bParsedFirstPassValue = false;',
                'if (p)',
                'bParsedFirstPassValue = parseFirstPassOptionValue(p, opt, i);',
                'if (!bParsedFirstPassValue || param_val != i)',
                'if (bErr)',
                'if (p && !bParsedFirstPassValue)',
                'x265_log(m_param, X265_LOG_ERROR, opt " specified in stats file not valid\\n");',
                'x265_log(m_param, X265_LOG_ERROR, "different " opt " setting than first pass (%d vs %d)\\n", param_val, i);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'CMP_OPT_FIRST_PASS must parse the stats token before comparing values and must preserve the dedicated invalid-token error path'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed ratecontrol first-pass option parsing guardrails')
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

    print('Ratecontrol first-pass parse usage validated')


if __name__ == '__main__':
    main()
