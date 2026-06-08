#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
HELPER_REQUIRED_SNIPPETS = (
    'static int parseName(const char* arg, const char* const* names, bool& bError)',
    'for (int i = 0; names[i]; i++)',
    'if (!arg)',
    'bError = true;',
    'return 0;',
    'return parseOptionIntToken(arg, std::strlen(arg), bError);',
)
ZONE_REQUIRED_SNIPPETS = (
    'OPT("me")',
    'bool bSearchMethodError = false;',
    'int searchMethod = parseName(value, x265_motion_est_names, bSearchMethodError);',
    'bError |= bSearchMethodError;',
    'if (!bSearchMethodError)',
    'p->searchMethod = searchMethod;',
)
MAIN_REQUIRED_SNIPPETS = (
    'OPT("input-csp")',
    'bool bInternalCspError = false;',
    'int internalCsp = parseName(value, x265_source_csp_names, bInternalCspError);',
    'OPT("me")',
    'bool bSearchMethodError = false;',
    'int searchMethod = parseName(value, x265_motion_est_names, bSearchMethodError);',
    'OPT("videoformat")',
    'bool bVideoFormatError = false;',
    'int videoFormat = parseName(value, x265_video_format_names, bVideoFormatError);',
    'OPT("range")',
    'bool bVideoFullRangeError = false;',
    'int videoFullRange = parseName(value, x265_fullrange_names, bVideoFullRangeError);',
    'OPT("colorprim")',
    'bool bColorPrimariesError = false;',
    'int colorPrimaries = parseName(value, x265_colorprim_names, bColorPrimariesError);',
    'OPT("transfer")',
    'bool bTransferCharacteristicsError = false;',
    'int transferCharacteristics = parseName(value, x265_transfer_names, bTransferCharacteristicsError);',
    'OPT("colormatrix")',
    'bool bMatrixCoeffsError = false;',
    'int matrixCoeffs = parseName(value, x265_colmatrix_names, bMatrixCoeffsError);',
)
FORBIDDEN_SNIPPETS = (
    'return x265_atoi(arg, bError);',
    'OPT("me") p->searchMethod = parseName(value, x265_motion_est_names, bError);',
    'OPT("input-csp") p->internalCsp = parseName(value, x265_source_csp_names, bError);',
    'p->vui.videoFormat = parseName(value, x265_video_format_names, bError);',
    'p->vui.bEnableVideoFullRangeFlag = parseName(value, x265_fullrange_names, bError);',
    'p->vui.colorPrimaries = parseName(value, x265_colorprim_names, bError);',
    'p->vui.transferCharacteristics = parseName(value, x265_transfer_names, bError);',
    'p->vui.matrixCoeffs = parseName(value, x265_colmatrix_names, bError);',
)
HELPER_REGION_START = 'static int parseName(const char* arg, const char* const* names, bool& bError)'
HELPER_REGION_END = 'static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)'
ZONE_REGION_START = 'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)'
ZONE_REGION_END = 'int x265_param_parse(x265_param* p, const char* name, const char* value)'
MAIN_REGION_START = 'OPT("input-csp")'
MAIN_REGION_END = 'OPT("chromaloc")'


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
    zone_region = get_region(text, ZONE_REGION_START, ZONE_REGION_END)
    main_region = get_region(text, MAIN_REGION_START, MAIN_REGION_END)
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, 'forbidden parseName regression: invalid names must not overwrite prior state'))
            return failures
    for snippet in HELPER_REQUIRED_SNIPPETS:
        if snippet not in helper_region:
            failures.append((TARGET.as_posix(), 0, f'missing parseName guardrail: {snippet}'))
    for snippet in ZONE_REQUIRED_SNIPPETS:
        if snippet not in zone_region:
            failures.append((TARGET.as_posix(), 0, f'missing parseName guardrail: {snippet}'))
    for snippet in MAIN_REQUIRED_SNIPPETS:
        if snippet not in main_region:
            failures.append((TARGET.as_posix(), 0, f'missing parseName guardrail: {snippet}'))
    if all(snippet in helper_region for snippet in HELPER_REQUIRED_SNIPPETS):
        if not has_in_order(
            helper_region,
            (
                'for (int i = 0; names[i]; i++)',
                'if (!arg)',
                'bError = true;',
                'return 0;',
                'return parseOptionIntToken(arg, std::strlen(arg), bError);',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'parseName must fall back to parseOptionIntToken only after the null-argument guard and must preserve the reviewed name lookup order'))
    if all(snippet in zone_region for snippet in ZONE_REQUIRED_SNIPPETS):
        if not has_in_order(
            zone_region,
            (
                'OPT("me")',
                'bool bSearchMethodError = false;',
                'int searchMethod = parseName(value, x265_motion_est_names, bSearchMethodError);',
                'bError |= bSearchMethodError;',
                'if (!bSearchMethodError)',
                'p->searchMethod = searchMethod;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Zone me parsing must stage the parsed search method and only assign it after the parseName error gate succeeds'))
    if all(snippet in main_region for snippet in MAIN_REQUIRED_SNIPPETS):
        if not has_in_order(
            main_region,
            (
                'OPT("input-csp")',
                'bool bInternalCspError = false;',
                'int internalCsp = parseName(value, x265_source_csp_names, bInternalCspError);',
                'bError |= bInternalCspError;',
                'if (!bInternalCspError)',
                'p->internalCsp = internalCsp;',
                'OPT("me")',
                'bool bSearchMethodError = false;',
                'int searchMethod = parseName(value, x265_motion_est_names, bSearchMethodError);',
                'bError |= bSearchMethodError;',
                'if (!bSearchMethodError)',
                'p->searchMethod = searchMethod;',
                'OPT("videoformat")',
                'bool bVideoFormatError = false;',
                'int videoFormat = parseName(value, x265_video_format_names, bVideoFormatError);',
                'bError |= bVideoFormatError;',
                'p->vui.bEnableVideoSignalTypePresentFlag = 1;',
                'if (!bVideoFormatError)',
                'p->vui.videoFormat = videoFormat;',
                'OPT("range")',
                'bool bVideoFullRangeError = false;',
                'int videoFullRange = parseName(value, x265_fullrange_names, bVideoFullRangeError);',
                'bError |= bVideoFullRangeError;',
                'p->vui.bEnableVideoSignalTypePresentFlag = 1;',
                'if (!bVideoFullRangeError)',
                'p->vui.bEnableVideoFullRangeFlag = videoFullRange;',
                'OPT("colorprim")',
                'bool bColorPrimariesError = false;',
                'int colorPrimaries = parseName(value, x265_colorprim_names, bColorPrimariesError);',
                'bError |= bColorPrimariesError;',
                'p->vui.bEnableVideoSignalTypePresentFlag = 1;',
                'p->vui.bEnableColorDescriptionPresentFlag = 1;',
                'if (!bColorPrimariesError)',
                'p->vui.colorPrimaries = colorPrimaries;',
                'OPT("transfer")',
                'bool bTransferCharacteristicsError = false;',
                'int transferCharacteristics = parseName(value, x265_transfer_names, bTransferCharacteristicsError);',
                'bError |= bTransferCharacteristicsError;',
                'p->vui.bEnableVideoSignalTypePresentFlag = 1;',
                'p->vui.bEnableColorDescriptionPresentFlag = 1;',
                'if (!bTransferCharacteristicsError)',
                'p->vui.transferCharacteristics = transferCharacteristics;',
                'OPT("colormatrix")',
                'bool bMatrixCoeffsError = false;',
                'int matrixCoeffs = parseName(value, x265_colmatrix_names, bMatrixCoeffsError);',
                'bError |= bMatrixCoeffsError;',
                'p->vui.bEnableVideoSignalTypePresentFlag = 1;',
                'p->vui.bEnableColorDescriptionPresentFlag = 1;',
                'if (!bMatrixCoeffsError)',
                'p->vui.matrixCoeffs = matrixCoeffs;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'x265_param_parse must stage parseName results in local variables and only publish motion/VUI enum values after the reviewed error gates succeed'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check parseName assignment safety guardrails')
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

    print('parseName assignment safety validated')


if __name__ == '__main__':
    main()
