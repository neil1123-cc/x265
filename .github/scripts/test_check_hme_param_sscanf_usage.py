#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_hme_param_sscanf_usage.py')

# Coverage probes used by the scan for HME sscanf guardrails.
NORMALIZED_PROBES = (
    'forbidden HME sscanf regression: ',
    'missing HME sscanf guardrail: ',
    'HME helper parsing must split comma-delimited tokens, normalize named search-method substrings, and fan out single-value levels with the reviewed helpers',
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
                'source/common/param.cpp': '\n'.join((
                    'static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)',
                    'int count = 0;',
                    "const char* comma = std::strchr(token, ',');",
                    'parts[count] = token;',
                    'lengths[count] = length;',
                    'count++;',
                    'token = comma ? comma + 1 : nullptr;',
                    'static int parseHmeSearchMethodToken(const char* token, size_t length, bool& bError)',
                    'char name[5];',
                    "name[length] = '\\0';",
                    'return parseName(name, x265_motion_est_names, bError);',
                    'static int parseOptionIntToken(const char* token, size_t length, bool& bError)',
                    'static void assignParsedOptionLevels(const int parsed[3], int count, int target[3])',
                    'if (count == 1)',
                    'target[0] = target[1] = target[2] = parsed[0];',
                    'static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)',
                    'OPT("hme-search")',
                    'int count = splitCommaOption(value, search, searchLengths, 3);',
                    'if (count == 1 || count == 3)',
                    'if (bNumeric)',
                    'int parsed[3];',
                    'parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);',
                    'if (!bLocalError)',
                    'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                    'parsed[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bLocalError);',
                    'if (!bLocalError)',
                    'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                    'OPT("hme-range")',
                    'if (splitCommaOption(value, range, rangeLengths, 3) != 3)',
                    'bLocalError = true;',
                    'int parsed[3];',
                    'parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);',
                    'OPT("vbv-live-multi-pass")',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'else if (sscanf(value, "%d", &p->hmeSearchMethod[0]) || sscanf(value, "%s", search[0]))',
                    'sscanf(value, "%d,%d,%d", &p->hmeRange[0], &p->hmeRange[1], &p->hmeRange[2]);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden HME sscanf regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)',
                    'int count = 0;',
                    "const char* comma = std::strchr(token, ',');",
                    'parts[count] = token;',
                    'lengths[count] = length;',
                    'count++;',
                    'token = comma ? comma + 1 : nullptr;',
                    'static int parseHmeSearchMethodToken(const char* token, size_t length, bool& bError)',
                    'char name[5];',
                    "name[length] = '\\0';",
                    'return parseName(name, x265_motion_est_names, bError);',
                    'static int parseOptionIntToken(const char* token, size_t length, bool& bError)',
                    'static void assignParsedOptionLevels(const int parsed[3], int count, int target[3])',
                    'if (count == 1)',
                    'target[0] = target[1] = target[2] = parsed[0];',
                    'static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)',
                    'OPT("hme-search")',
                    'int count = splitCommaOption(value, search, searchLengths, 3);',
                    'if (count == 1 || count == 3)',
                    'if (bNumeric)',
                    'int parsed[3];',
                    'if (!bLocalError)',
                    'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                    'parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);',
                    'parsed[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bLocalError);',
                    'if (!bLocalError)',
                    'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                    'OPT("hme-range")',
                    'if (splitCommaOption(value, range, rangeLengths, 3) != 3)',
                    'bLocalError = true;',
                    'int parsed[3];',
                    'parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);',
                    'OPT("vbv-live-multi-pass")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'HME option parsing must route hme-search and hme-range through the reviewed comma-splitting helpers instead of legacy sscanf tokenization')

    print('HME sscanf guard tests passed')


if __name__ == '__main__':
    main()
