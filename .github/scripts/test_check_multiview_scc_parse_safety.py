#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_multiview_scc_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing multiview/SCC guardrail: ',
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
                    'OPT("format")',
                    '{',
                    '    bool bFormatError = false;',
                    '    int format = parseOptionIntValue(value, bFormatError);',
                    '    bError |= bFormatError;',
                    '    if (!bFormatError)',
                    '        p->format = format;',
                    '}',
                    'OPT("num-views")',
                    '{',
                    '    bool bNumViewsError = false;',
                    '    int numViews = parseOptionIntValue(value, bNumViewsError);',
                    '    bError |= bNumViewsError;',
                    '    if (!bNumViewsError)',
                    '        p->numViews = numViews;',
                    '}',
                    'OPT("scc")',
                    '{',
                    '    bool bSccError = false;',
                    '    int bEnableSCC = parseOptionIntValue(value, bSccError);',
                    '    bError |= bSccError;',
                    '    if (!bSccError)',
                    '        p->bEnableSCC = bEnableSCC;',
                    '}',
                    'CHECK((param->numViews < 1), "Multi-View Encoding requires at least one view");',
                    'CHECK((param->numViews > 2), "Multi-View Encoding currently support only 2 views");',
                    'CHECK((param->format < 0 || param->format > 2), "Multi-View input format must be 0 (normal), 1 (side-by-side), or 2 (over-under)");',
                    'CHECK(param->format && param->numViews <= 1, "Multi-View input format requires more than one view");',
                    'if (param->numViews > 1)',
                    'OPT("frame-rc")',
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
                    'OPT("format")',
                    '    p->format = x265_atoi(value, bError);',
                    'OPT("num-views")',
                    '{',
                    '    p->numViews = x265_atoi(value, bError);',
                    '}',
                    'OPT("scc")',
                    '{',
                    '    p->bEnableSCC = x265_atoi(value, bError);',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden multiview/SCC regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("format")',
                    '{',
                    '    bool bFormatError = false;',
                    '    int format = parseOptionIntValue(value, bFormatError);',
                    '    bError |= bFormatError;',
                    '    if (!bFormatError)',
                    '        p->format = format;',
                    '}',
                    'OPT("num-views")',
                    '{',
                    '    bool bNumViewsError = false;',
                    '    int numViews = parseOptionIntValue(value, bNumViewsError);',
                    '    bError |= bNumViewsError;',
                    '        p->numViews = numViews;',
                    '    if (!bNumViewsError)',
                    '}',
                    'OPT("scc")',
                    '{',
                    '    bool bSccError = false;',
                    '    int bEnableSCC = parseOptionIntValue(value, bSccError);',
                    '    bError |= bSccError;',
                    '    if (!bSccError)',
                    '        p->bEnableSCC = bEnableSCC;',
                    '}',
                    'OPT("frame-rc")',
                    'CHECK((param->numViews < 1), "Multi-View Encoding requires at least one view");',
                    'CHECK((param->numViews > 2), "Multi-View Encoding currently support only 2 views");',
                    'CHECK((param->format < 0 || param->format > 2), "Multi-View input format must be 0 (normal), 1 (side-by-side), or 2 (over-under)");',
                    'CHECK(param->format && param->numViews <= 1, "Multi-View input format requires more than one view");',
                    'if (param->numViews > 1)',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Multiview/SCC parsing must stage parsed integers and only publish them after the reviewed error gates succeed')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("format")',
                    '{',
                    '    bool bFormatError = false;',
                    '    int format = parseOptionIntValue(value, bFormatError);',
                    '    bError |= bFormatError;',
                    '    if (!bFormatError)',
                    '        p->format = format;',
                    '}',
                    'OPT("num-views")',
                    '{',
                    '    bool bNumViewsError = false;',
                    '    int numViews = parseOptionIntValue(value, bNumViewsError);',
                    '    bError |= bNumViewsError;',
                    '    if (!bNumViewsError)',
                    '        p->numViews = numViews;',
                    '}',
                    'OPT("scc")',
                    '{',
                    '    bool bSccError = false;',
                    '    int bEnableSCC = parseOptionIntValue(value, bSccError);',
                    '    bError |= bSccError;',
                    '    if (!bSccError)',
                    '        p->bEnableSCC = bEnableSCC;',
                    '}',
                    'CHECK((param->numViews < 1), "Multi-View Encoding requires at least one view");',
                    'CHECK((param->format < 0 || param->format > 2), "Multi-View input format must be 0 (normal), 1 (side-by-side), or 2 (over-under)");',
                    'CHECK((param->numViews > 2), "Multi-View Encoding currently support only 2 views");',
                    'CHECK(param->format && param->numViews <= 1, "Multi-View input format requires more than one view");',
                    'if (param->numViews > 1)',
                    'OPT("frame-rc")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'Multiview validation must preserve the reviewed numViews/format constraint ordering')

    print('Multiview and SCC parse safety tests passed')


if __name__ == '__main__':
    main()
