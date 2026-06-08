#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/ratecontrol.cpp')
FORBIDDEN_SNIPPETS = (
    'sscanf(p, " input-res=%dx%d", &i, &j) != 2',
    'sscanf(p, " fps=%u/%u", &k, &l) != 2',
    'sscanf(p, " vbv-maxrate=%d", &m) != 1',
    'sscanf(p, " input-res=%dx%d%n", &i, &j, &consumed)',
    'sscanf(p, " fps=%u/%u%n", &k, &l, &consumed)',
    'sscanf(p, " vbv-maxrate=%d%n", &m, &consumed)',
)
REQUIRED_SNIPPETS = (
    'static bool parseStatsIntValue(const char* p, const char* prefix, int& value)',
    'static bool parseStatsLineIntValue(const char*& cursor, const char* label, int& value)',
    'static bool parseStatsUintPair(const char* p, const char* prefix, char separator, uint32_t& first, uint32_t& second)',
    'static bool parseStatsOptionalIntValue(const char* opts, const char* prefix, int& value)',
    'static bool parseStatsOptionalUintValue(const char* opts, const char* prefix, uint32_t& value)',
    "while (*end && *end != ' ')",
    'char token[16];',
    "return parseRateControlIntToken(token, value) && (*end == ' ' || *end == '\\0');",
    'if (!parseRateControlIntToken(token, value))',
    'if ((p = strstr(opts, " input-res=")) == 0 || !parseStatsUintPair(p, " input-res=", \'x\', k, l))',
    'uint32_t currentSourceWidth = (uint32_t)(m_param->sourceWidth - sps.conformanceWindow.rightOffset);',
    'uint32_t currentSourceHeight = (uint32_t)(m_param->sourceHeight - sps.conformanceWindow.bottomOffset);',
    'if (k != currentSourceWidth || l != currentSourceHeight)',
    'if ((p = strstr(opts, " fps=")) == 0 || !parseStatsUintPair(p, " fps=", \'/\', k, l))',
    'if (((p = strstr(opts, " vbv-maxrate=")) == 0 || !parseStatsIntValue(p, " vbv-maxrate=", m) || m <= 0) && m_param->rc.rateControlMode == X265_RC_CRF)',
    'if (!parseStatsOptionalIntValue(opts, "ref=", i))',
    'if (i < 1 || i > m_param->maxNumReferences)',
    'if (!parseStatsOptionalUintValue(opts, "ctu=", k))',
    'if (parseStatsOptionalIntValue(opts, "b-adapt=", i) && i >= X265_B_ADAPT_NONE && i <= X265_B_ADAPT_TRELLIS)',
    'else if (std::strstr(opts, "b-adapt="))',
    'x265_log(m_param, X265_LOG_ERROR, "b-adapt method specified in stats file not valid\\n");',
    'if (parseStatsOptionalIntValue(opts, "rc-lookahead=", i) && i >= 0 && i <= X265_LOOKAHEAD_MAX)',
    'else if (std::strstr(opts, "rc-lookahead="))',
    'x265_log(m_param, X265_LOG_ERROR, "rc-lookahead specified in stats file not valid\\n");',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    if text.count("while (*end && *end != ' ')") < 2:
        failures.append((TARGET.as_posix(), 0, 'expected checked token slicing in both reviewed stats int parsers'))
    if text.count('char token[16];') < 2:
        failures.append((TARGET.as_posix(), 0, 'expected checked token buffers in both reviewed stats int parsers'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden ratecontrol stats parse regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing ratecontrol stats parse guardrail: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check reviewed ratecontrol stats parsing guardrails')
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

    print('Ratecontrol stats parse usage validated')


if __name__ == '__main__':
    main()
