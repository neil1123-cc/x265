#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_hme_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing HME parse guardrail: ',
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
                    'static void assignParsedOptionLevels(const int parsed[3], int count, int target[3])',
                    'OPT("hme-search")',
                    '{',
                    '    const char* search[3];',
                    '    size_t searchLengths[3];',
                    '    int count = splitCommaOption(value, search, searchLengths, 3);',
                    '    bool bLocalError = false;',
                    '    if (count == 1 || count == 3)',
                    '    {',
                    '        bool bNumeric = true;',
                    '        if (bNumeric)',
                    '        {',
                    '            int parsed[3];',
                    '            for (int level = 0; level < count; level++)',
                    '                parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);',
                    '            if (!bLocalError)',
                    '                assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                    '        }',
                    '        else',
                    '        {',
                    '            int parsed[3];',
                    '            for (int level = 0; level < count; level++)',
                    '                parsed[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bLocalError);',
                    '            if (!bLocalError)',
                    '                assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                    '        }',
                    '    }',
                    '    else',
                    '        bLocalError = true;',
                    '    bError |= bLocalError;',
                    '    if (!bLocalError)',
                    '        p->bEnableHME = true;',
                    '}',
                    'OPT("hme-range")',
                    '{',
                    '    const char* range[3];',
                    '    size_t rangeLengths[3];',
                    '    bool bLocalError = false;',
                    '    if (splitCommaOption(value, range, rangeLengths, 3) != 3)',
                    '        bLocalError = true;',
                    '    else',
                    '    {',
                    '        int parsed[3];',
                    '        for (int level = 0; level < 3; level++)',
                    '            parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);',
                    '        if (!bLocalError)',
                    '            assignParsedOptionLevels(parsed, 3, p->hmeRange);',
                    '    }',
                    '    bError |= bLocalError;',
                    '    if (!bLocalError)',
                    '        p->bEnableHME = true;',
                    '}',
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
                    'OPT("hme-search")',
                    '{',
                    '    for (int level = 0; level < count; level++)',
                    '        p->hmeSearchMethod[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bError);',
                    '    p->bEnableHME = true;',
                    '}',
                    'OPT("hme-range")',
                    '{',
                    '    if (splitCommaOption(value, range, rangeLengths, 3) != 3)',
                    '        bError = true;',
                    '    else',
                    '        p->hmeRange[level] = x265_atoi(number, bLocalError);',
                    '    p->bEnableHME = true;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden HME parse regression: invalid values must not partially mutate arrays or force-enable HME')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static void assignParsedOptionLevels(const int parsed[3], int count, int target[3])',
                    'OPT("hme-search")',
                    '{',
                    '    const char* search[3];',
                    '    size_t searchLengths[3];',
                    '    int count = splitCommaOption(value, search, searchLengths, 3);',
                    '    bool bLocalError = false;',
                    '    if (count == 1 || count == 3)',
                    '    {',
                    '        bool bNumeric = true;',
                    '        if (bNumeric)',
                    '        {',
                    '            int parsed[3];',
                    '            for (int level = 0; level < count; level++)',
                    '                parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);',
                    '            if (!bLocalError)',
                    '                assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                    '        }',
                    '        else',
                    '        {',
                    '            int parsed[3];',
                    '            for (int level = 0; level < count; level++)',
                    '                parsed[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bLocalError);',
                    '            if (!bLocalError)',
                    '                assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                    '        }',
                    '    }',
                    '    else',
                    '        bLocalError = true;',
                    '    if (!bLocalError)',
                    '        p->bEnableHME = true;',
                    '    bError |= bLocalError;',
                    '}',
                    'OPT("hme-range")',
                    '{',
                    '    const char* range[3];',
                    '    size_t rangeLengths[3];',
                    '    bool bLocalError = false;',
                    '    if (splitCommaOption(value, range, rangeLengths, 3) != 3)',
                    '        bLocalError = true;',
                    '    else',
                    '    {',
                    '        int parsed[3];',
                    '        for (int level = 0; level < 3; level++)',
                    '            parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);',
                    '        if (!bLocalError)',
                    '            assignParsedOptionLevels(parsed, 3, p->hmeRange);',
                    '    }',
                    '    bError |= bLocalError;',
                    '    if (!bLocalError)',
                    '        p->bEnableHME = true;',
                    '}',
                    'OPT("vbv-live-multi-pass")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'HME search/range parsing must finish staged token parsing and gated array assignment before enabling HME for the current parameter set')

    print('HME parse safety tests passed')


if __name__ == '__main__':
    main()
