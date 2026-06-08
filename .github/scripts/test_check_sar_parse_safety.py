#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_sar_parse_safety.py')

# Normalized checker probe used by the coverage scan for generic guardrail failures.
NORMALIZED_PROBES = (
    'missing sar guardrail: ',
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
                    'OPT("sar")',
                    '{',
                    '    bool bSarNameError = false;',
                    '    int aspectRatioIdc = parseName(value, x265_sar_names, bSarNameError);',
                    '    if (!bSarNameError)',
                    '        p->vui.aspectRatioIdc = aspectRatioIdc;',
                    '    else',
                    '    {',
                    '        int sarWidth = 0;',
                    '        int sarHeight = 0;',
                    '        bool bLocalError = !parseOptionIntPair(value, \':\', sarWidth, sarHeight);',
                    '        if (!bLocalError)',
                    '        {',
                    '            p->vui.aspectRatioIdc = X265_EXTENDED_SAR;',
                    '            p->vui.sarWidth = sarWidth;',
                    '            p->vui.sarHeight = sarHeight;',
                    '        }',
                    '        bError |= bLocalError;',
                    '    }',
                    '}',
                    'OPT("overscan")',
                    'CHECK((param->vui.aspectRatioIdc < 0',
                    '       || param->vui.aspectRatioIdc > 16)',
                    '      && param->vui.aspectRatioIdc != X265_EXTENDED_SAR,',
                    '      "Sample Aspect Ratio must be 0-16 or 255");',
                    'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarWidth <= 0,',
                    '      "Sample Aspect Ratio width must be greater than 0");',
                    'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarHeight <= 0,',
                    '      "Sample Aspect Ratio height must be greater than 0");',
                    'CHECK(param->vui.videoFormat < 0 || param->vui.videoFormat > 5,',
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
                    'OPT("sar")',
                    '{',
                    '    p->vui.aspectRatioIdc = parseName(value, x265_sar_names, bError);',
                    '    if (bError)',
                    '    {',
                    '        p->vui.aspectRatioIdc = X265_EXTENDED_SAR;',
                    '        bool bLocalError = false;',
                    '        const char* separator = std::strchr(value, \':\');',
                    '        if (!separator)',
                    '            bLocalError = true;',
                    '        else',
                    '        {',
                    '            size_t leftLength = (size_t)(separator - value);',
                    '            size_t rightLength = std::strlen(separator + 1);',
                    '            if (!leftLength || !rightLength)',
                    '                bLocalError = true;',
                    '            else',
                    '            {',
                    '                p->vui.sarWidth = parseOptionIntToken(value, leftLength, bLocalError);',
                    '                p->vui.sarHeight = parseOptionIntToken(separator + 1, rightLength, bLocalError);',
                    '            }',
                    '        }',
                    '        bError = bLocalError;',
                    '    }',
                    '}',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden sar regression: invalid SAR input must not partially mutate VUI state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join(((
                    'OPT("sar")',
                    '{',
                    '    bool bSarNameError = false;',
                    '    int aspectRatioIdc = parseName(value, x265_sar_names, bSarNameError);',
                    '    if (!bSarNameError)',
                    '        p->vui.aspectRatioIdc = aspectRatioIdc;',
                    '    else',
                    '    {',
                    '        int sarWidth = 0;',
                    '        int sarHeight = 0;',
                    '        bool bLocalError = !parseOptionIntPair(value, \':\', sarWidth, sarHeight);',
                    '        if (!bLocalError)',
                    '        {',
                    '            p->vui.sarWidth = sarWidth;',
                    '            p->vui.aspectRatioIdc = X265_EXTENDED_SAR;',
                    '            p->vui.sarHeight = sarHeight;',
                    '        }',
                    '        bError |= bLocalError;',
                    '    }',
                    '}',
                    'OPT("overscan")',
                    'CHECK((param->vui.aspectRatioIdc < 0',
                    '       || param->vui.aspectRatioIdc > 16)',
                    '      && param->vui.aspectRatioIdc != X265_EXTENDED_SAR,',
                    '      "Sample Aspect Ratio must be 0-16 or 255");',
                    'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarWidth <= 0,',
                    '      "Sample Aspect Ratio width must be greater than 0");',
                    'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarHeight <= 0,',
                    '      "Sample Aspect Ratio height must be greater than 0");',
                    'CHECK(param->vui.videoFormat < 0 || param->vui.videoFormat > 5,',
                ))) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SAR parsing must preserve the reviewed named-SAR fallback ordering before publishing extended SAR state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join(((
                    'OPT("sar")',
                    '{',
                    '    bool bSarNameError = false;',
                    '    int aspectRatioIdc = parseName(value, x265_sar_names, bSarNameError);',
                    '    if (!bSarNameError)',
                    '        p->vui.aspectRatioIdc = aspectRatioIdc;',
                    '    else',
                    '    {',
                    '        int sarWidth = 0;',
                    '        int sarHeight = 0;',
                    '        bool bLocalError = !parseOptionIntPair(value, \':\', sarWidth, sarHeight);',
                    '        if (!bLocalError)',
                    '        {',
                    '            p->vui.aspectRatioIdc = X265_EXTENDED_SAR;',
                    '            p->vui.sarWidth = sarWidth;',
                    '            p->vui.sarHeight = sarHeight;',
                    '        }',
                    '        bError |= bLocalError;',
                    '    }',
                    '}',
                    'OPT("overscan")',
                    'CHECK((param->vui.aspectRatioIdc < 0',
                    '       || param->vui.aspectRatioIdc > 16)',
                    '      && param->vui.aspectRatioIdc != X265_EXTENDED_SAR,',
                    '      "Sample Aspect Ratio must be 0-16 or 255");',
                    'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarHeight <= 0,',
                    '      "Sample Aspect Ratio height must be greater than 0");',
                    'CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarWidth <= 0,',
                    '      "Sample Aspect Ratio width must be greater than 0");',
                    'CHECK(param->vui.videoFormat < 0 || param->vui.videoFormat > 5,',
                ))) + '\n',
            },
        )
        expect_fail(run_checker(root), 'SAR validation must preserve the reviewed aspect-ratio-idc, width, and height guard ordering')

    print('SAR parse safety tests passed')


if __name__ == '__main__':
    main()
