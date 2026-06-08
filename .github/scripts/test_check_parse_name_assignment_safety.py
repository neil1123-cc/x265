#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_parse_name_assignment_safety.py')

# Coverage probes used by the scan for parseName assignment guardrails.
NORMALIZED_PROBES = (
    'forbidden parseName regression: invalid names must not overwrite prior state',
    'missing parseName guardrail: ',
    'Zone me parsing must stage the parsed search method and only assign it after the parseName error gate succeeds',
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
                    'static int parseName(const char* arg, const char* const* names, bool& bError)',
                    'for (int i = 0; names[i]; i++)',
                    'if (!arg)',
                    'bError = true;',
                    'return 0;',
                    'return parseOptionIntToken(arg, std::strlen(arg), bError);',
                    'static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)',
                    'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)',
                    'OPT("me")',
                    'bool bSearchMethodError = false;',
                    'int searchMethod = parseName(value, x265_motion_est_names, bSearchMethodError);',
                    'bError |= bSearchMethodError;',
                    'if (!bSearchMethodError)',
                    'p->searchMethod = searchMethod;',
                    'int x265_param_parse(x265_param* p, const char* name, const char* value)',
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
                    'OPT("chromaloc")',
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
                    'OPT("me") p->searchMethod = parseName(value, x265_motion_est_names, bError);',
                    'OPT("input-csp") p->internalCsp = parseName(value, x265_source_csp_names, bError);',
                    'p->vui.videoFormat = parseName(value, x265_video_format_names, bError);',
                    'p->vui.bEnableVideoFullRangeFlag = parseName(value, x265_fullrange_names, bError);',
                    'p->vui.colorPrimaries = parseName(value, x265_colorprim_names, bError);',
                    'p->vui.transferCharacteristics = parseName(value, x265_transfer_names, bError);',
                    'p->vui.matrixCoeffs = parseName(value, x265_colmatrix_names, bError);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden parseName regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static int parseName(const char* arg, const char* const* names, bool& bError)',
                    'for (int i = 0; names[i]; i++)',
                    'return parseOptionIntToken(arg, std::strlen(arg), bError);',
                    'if (!arg)',
                    'bError = true;',
                    'return 0;',
                    'static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)',
                    'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)',
                    'OPT("me")',
                    'bool bSearchMethodError = false;',
                    'int searchMethod = parseName(value, x265_motion_est_names, bSearchMethodError);',
                    'bError |= bSearchMethodError;',
                    'if (!bSearchMethodError)',
                    'p->searchMethod = searchMethod;',
                    'int x265_param_parse(x265_param* p, const char* name, const char* value)',
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
                    'OPT("chromaloc")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'parseName must fall back to parseOptionIntToken only after the null-argument guard and must preserve the reviewed name lookup order')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'static int parseName(const char* arg, const char* const* names, bool& bError)',
                    'for (int i = 0; names[i]; i++)',
                    'if (!arg)',
                    'bError = true;',
                    'return 0;',
                    'return parseOptionIntToken(arg, std::strlen(arg), bError);',
                    'static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)',
                    'int x265_zone_param_parse(x265_param* p, const char* name, const char* value)',
                    'OPT("me")',
                    'bool bSearchMethodError = false;',
                    'bError |= bSearchMethodError;',
                    'int searchMethod = parseName(value, x265_motion_est_names, bSearchMethodError);',
                    'if (!bSearchMethodError)',
                    'p->searchMethod = searchMethod;',
                    'int x265_param_parse(x265_param* p, const char* name, const char* value)',
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
                    'p->vui.bEnableColorDescriptionPresentFlag = 1;',
                    'p->vui.bEnableVideoSignalTypePresentFlag = 1;',
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
                    'p->vui.matrixCoeffs = matrixCoeffs;',
                    'if (!bMatrixCoeffsError)',
                    'OPT("chromaloc")',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'x265_param_parse must stage parseName results in local variables and only publish motion/VUI enum values after the reviewed error gates succeed')

    print('parseName assignment safety tests passed')


if __name__ == '__main__':
    main()
