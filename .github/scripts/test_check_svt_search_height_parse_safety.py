#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_svt_search_height_parse_safety.py')


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
                    'OPT("svt-search-height") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \\n", name);',
                    'OPT("svt-search-height")',
                    '{',
                    '    bool bSearchAreaHeightError = false;',
                    '    int searchAreaHeight = parseOptionIntValue(value, bSearchAreaHeightError);',
                    '    bError |= bSearchAreaHeightError;',
                    '    if (!bSearchAreaHeightError)',
                    '        svtHevcParam->searchAreaHeight = searchAreaHeight;',
                    '}',
                    'OPT("svt-compressed-ten-bit-format")',
                    '{',
                    '}',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'OPT("svt-search-height") svtHevcParam->searchAreaHeight = x265_atoi(value, bError);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden SVT search-height regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("svt-search-height")',
                    '{',
                    '    x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \\n", name);',
                    '    warning_only();',
                    '}',
                    'OPT("svt-compressed-ten-bit-format")',
                    '{',
                    '    something_else();',
                    '}',
                    'OPT("svt-search-height")',
                    '{',
                    '    bool bSearchAreaHeightError = false;',
                    '    int searchAreaHeight = parseOptionIntValue(value, bSearchAreaHeightError);',
                    '    bError |= bSearchAreaHeightError;',
                    '    if (!bSearchAreaHeightError)',
                    '        svtHevcParam->searchAreaHeight = searchAreaHeight;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SVT search-height parse block must gate assignment on parseOptionIntValue success')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'void helper()',
                    '{',
                    '    OPT("svt-search-height")',
                    '    {',
                    '        bool bSearchAreaHeightError = false;',
                    '        int searchAreaHeight = parseOptionIntValue(value, bSearchAreaHeightError);',
                    '        bError |= bSearchAreaHeightError;',
                    '        if (!bSearchAreaHeightError)',
                    '            svtHevcParam->searchAreaHeight = searchAreaHeight;',
                    '    }',
                    '}',
                    'int svt_param_parse(x265_param* param, const char* name, const char* value)',
                    '{',
                    '    OPT("svt-search-height")',
                    '    {',
                    '        int searchAreaHeight = parseOptionIntValue(value, bSearchAreaHeightError);',
                    '        bError |= bSearchAreaHeightError;',
                    '        if (!bSearchAreaHeightError)',
                    '            svtHevcParam->searchAreaHeight = searchAreaHeight;',
                    '    }',
                    '    return bError ? X265_PARAM_BAD_VALUE : 0;',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing SVT search-height guardrail in parse block: bool bSearchAreaHeightError = false;')

    print('SVT search-height parse safety tests passed')


if __name__ == '__main__':
    main()
