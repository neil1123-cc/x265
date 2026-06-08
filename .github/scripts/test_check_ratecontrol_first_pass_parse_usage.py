#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_ratecontrol_first_pass_parse_usage.py')

# Coverage probes used by the scan for first-pass option parsing guardrails.
NORMALIZED_PROBES = (
    'forbidden ratecontrol first-pass parse regression: ',
    'missing ratecontrol first-pass parse guardrail: ',
    'parseFirstPassOptionValue must isolate the option token before validating and comparing the parsed integer value',
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
                    'static bool parseRateControlIntToken(const char* token, int& value);',
                    'static bool parseFirstPassOptionValue(const char* p, const char* opt, int& value)',
                    'size_t optLength = std::strlen(opt);',
                    "if (std::strncmp(p, opt, optLength) || p[optLength] != '=')",
                    "while (*end && *end != ' ')",
                    'char token[16];',
                    "return parseRateControlIntToken(token, value) && (*end == ' ' || *end == '\\0');",
                    '#define CMP_OPT_FIRST_PASS(opt, param_val)\\',
                    'bool bParsedFirstPassValue = false;',
                    'if (p)',
                    'bParsedFirstPassValue = parseFirstPassOptionValue(p, opt, i);',
                    'if (!bParsedFirstPassValue || param_val != i)',
                    'if (bErr)',
                    'if (p && !bParsedFirstPassValue)',
                    'x265_log(m_param, X265_LOG_ERROR, opt " specified in stats file not valid\\n");',
                    'x265_log(m_param, X265_LOG_ERROR, "different " opt " setting than first pass (%d vs %d)\\n", param_val, i);',
                    'static bool parseStatsPrefix(const char* p, int& frameNumber, int& encodeOrder, int& consumedPrefix)',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/ratecontrol.cpp': 'if (p && sscanf(p, opt "=%d%n" , &i, &consumedOpt) == 1 && (p[consumedOpt] == \' \' || p[consumedOpt] == \'\\0\') && param_val != i)\n'})
        expect_fail(run_checker(root), 'forbidden ratecontrol first-pass parse regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/ratecontrol.cpp': '\n'.join((
                    'static bool parseRateControlIntToken(const char* token, int& value);',
                    'static bool parseFirstPassOptionValue(const char* p, const char* opt, int& value)',
                    'size_t optLength = std::strlen(opt);',
                    "if (std::strncmp(p, opt, optLength) || p[optLength] != '=')",
                    "while (*end && *end != ' ')",
                    'char token[16];',
                    "return parseRateControlIntToken(token, value) && (*end == ' ' || *end == '\\0');",
                    '#define CMP_OPT_FIRST_PASS(opt, param_val)\\',
                    'bool bParsedFirstPassValue = false;',
                    'if (p)',
                    'if (!bParsedFirstPassValue || param_val != i)',
                    'bParsedFirstPassValue = parseFirstPassOptionValue(p, opt, i);',
                    'if (bErr)',
                    'if (p && !bParsedFirstPassValue)',
                    'x265_log(m_param, X265_LOG_ERROR, opt " specified in stats file not valid\\n");',
                    'x265_log(m_param, X265_LOG_ERROR, "different " opt " setting than first pass (%d vs %d)\\n", param_val, i);',
                    'static bool parseStatsPrefix(const char* p, int& frameNumber, int& encodeOrder, int& consumedPrefix)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'CMP_OPT_FIRST_PASS must parse the stats token before comparing values and must preserve the dedicated invalid-token error path')

    print('Ratecontrol first-pass parse guard tests passed')


if __name__ == '__main__':
    main()
