#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ratecontrol_stats_parse_usage.py')

# Coverage probes used by the scan for ratecontrol stats parsing guardrails.
NORMALIZED_PROBES = (
    'expected checked token slicing in both reviewed stats int parsers',
    'expected checked token buffers in both reviewed stats int parsers',
    'forbidden ratecontrol stats parse regression: ',
    'missing ratecontrol stats parse guardrail: ',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'static bool parseStatsIntValue(const char* p, const char* prefix, int& value)',
                    'static bool parseStatsLineIntValue(const char*& cursor, const char* label, int& value)',
                    'static bool parseStatsUintPair(const char* p, const char* prefix, char separator, uint32_t& first, uint32_t& second)',
                    'static bool parseStatsOptionalIntValue(const char* opts, const char* prefix, int& value)',
                    'static bool parseStatsOptionalUintValue(const char* opts, const char* prefix, uint32_t& value)',
                    "while (*end && *end != ' ')",
                    "while (*end && *end != ' ')",
                    'char token[16];',
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
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': 'sscanf(p, " input-res=%dx%d%n", &i, &j, &consumed) != 2\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden ratecontrol stats parse regression')

    print('Ratecontrol stats parse guard tests passed')


if __name__ == '__main__':
    main()
