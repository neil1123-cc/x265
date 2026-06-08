#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_analysis_reuse_refine_parse_safety.py')


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


PASS_SOURCE = '\n'.join((
    'OPT("analysis-save-reuse-level")',
    '{',
    '    bool bAnalysisSaveReuseLevelError = false;',
    '    int analysisSaveReuseLevel = parseOptionIntValue(value, bAnalysisSaveReuseLevelError);',
    '    bError |= bAnalysisSaveReuseLevelError;',
    '    if (!bAnalysisSaveReuseLevelError)',
    '        p->analysisSaveReuseLevel = analysisSaveReuseLevel;',
    '}',
    'OPT("analysis-load-reuse-level")',
    '{',
    '    bool bAnalysisLoadReuseLevelError = false;',
    '    int analysisLoadReuseLevel = parseOptionIntValue(value, bAnalysisLoadReuseLevelError);',
    '    bError |= bAnalysisLoadReuseLevelError;',
    '    if (!bAnalysisLoadReuseLevelError)',
    '        p->analysisLoadReuseLevel = analysisLoadReuseLevel;',
    '}',
    'OPT("scale-factor")',
    '{',
    '    bool bScaleFactorError = false;',
    '    int scaleFactor = parseOptionIntValue(value, bScaleFactorError);',
    '    bError |= bScaleFactorError;',
    '    if (!bScaleFactorError)',
    '        p->scaleFactor = scaleFactor;',
    'CHECK(param->scaleFactor < 0 || param->scaleFactor > 2, "Invalid scale-factor. Supports factor between 0 and 2");',
    '}',
    'OPT("refine-intra")',
    '{',
    '    bool bIntraRefineError = false;',
    '    int intraRefine = parseOptionIntValue(value, bIntraRefineError);',
    '    bError |= bIntraRefineError;',
    '    if (!bIntraRefineError)',
    '        p->intraRefine = intraRefine;',
    '}',
    'OPT("refine-inter")',
    '{',
    '    bool bInterRefineError = false;',
    '    int interRefine = parseOptionIntValue(value, bInterRefineError);',
    '    bError |= bInterRefineError;',
    '    if (!bInterRefineError)',
    '        p->interRefine = interRefine;',
    '}',
    'OPT("refine-mv")',
    '{',
    '    bool bMvRefineError = false;',
    '    int mvRefine = parseOptionIntValue(value, bMvRefineError);',
    '    bError |= bMvRefineError;',
    '    if (!bMvRefineError)',
    '        p->mvRefine = mvRefine;',
    '}',
    'OPT("refine-ctu-distortion")',
    '{',
    '    bool bCtuDistortionRefineError = false;',
    '    int ctuDistortionRefine = parseOptionIntValue(value, bCtuDistortionRefineError);',
    '    bError |= bCtuDistortionRefineError;',
    '    if (!bCtuDistortionRefineError)',
    '        p->ctuDistortionRefine = ctuDistortionRefine;',
    '}',
    'OPT("hevc-aq")',
    'CHECK(strlen(param->analysisLoad) && (param->analysisLoadReuseLevel < 0 || param->analysisLoadReuseLevel > 10),',
    '    "Invalid analysis load refine level. Value must be between 1 and 10 (inclusive)");',
    'CHECK(strlen(param->analysisLoad) && (param->mvRefine < 1 || param->mvRefine > 3),',
    '    "Invalid mv refinement level. Value must be between 1 and 3 (inclusive)");',
    'CHECK(param->scaleFactor < 0 || param->scaleFactor > 2, "Invalid scale-factor. Supports factor between 0 and 2");',
    'CHECK(param->interRefine > 3 || param->interRefine < 0,',
    '    "Invalid refine-inter value, refine-inter levels 0 to 3 supported");',
    'CHECK(param->intraRefine > 4 || param->intraRefine < 0,',
    '    "Invalid refine-intra value, refine-intra levels 0 to 3 supported");',
    'CHECK(param->ctuDistortionRefine < 0 || param->ctuDistortionRefine > 1,',
    '    "Invalid refine-ctu-distortion value, must be either 0 or 1");',
    'CHECK(param->maxAUSizeFactor < 0.5 || param->maxAUSizeFactor > 1.0,',
)) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/common/param.cpp': PASS_SOURCE})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '    bool bScaleFactorError = false;',
                    '    bool bOtherScaleFactorError = false;',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'missing analysis/reuse/refine guardrail: bool bScaleFactorError = false;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': '\n'.join((
                    'OPT("analysis-save-reuse-level") p->analysisSaveReuseLevel = x265_atoi(value, bError);',
                    'OPT("analysis-load-reuse-level") p->analysisLoadReuseLevel = x265_atoi(value, bError);',
                    'OPT("scale-factor") p->scaleFactor = x265_atoi(value, bError);',
                    'OPT("refine-intra")p->intraRefine = x265_atoi(value, bError);',
                    'OPT("refine-inter")p->interRefine = x265_atoi(value, bError);',
                    'OPT("refine-mv")p->mvRefine = x265_atoi(value, bError);',
                    'OPT("refine-ctu-distortion") p->ctuDistortionRefine = x265_atoi(value, bError);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden analysis/reuse/refine regression: invalid values must not overwrite prior state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    '    if (!bAnalysisLoadReuseLevelError)\n'
                    '        p->analysisLoadReuseLevel = analysisLoadReuseLevel;',
                    '        p->analysisLoadReuseLevel = analysisLoadReuseLevel;\n'
                    '    if (!bAnalysisLoadReuseLevelError)',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'Analysis/reuse/refine parsing must stage parsed integers and only publish them after the reviewed error gates succeed')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': PASS_SOURCE.replace(
                    'CHECK(strlen(param->analysisLoad) && (param->mvRefine < 1 || param->mvRefine > 3),\n'
                    '    "Invalid mv refinement level. Value must be between 1 and 3 (inclusive)");\n'
                    'CHECK(param->scaleFactor < 0 || param->scaleFactor > 2, "Invalid scale-factor. Supports factor between 0 and 2");\n',
                    'CHECK(param->scaleFactor < 0 || param->scaleFactor > 2, "Invalid scale-factor. Supports factor between 0 and 2");\n'
                    'CHECK(strlen(param->analysisLoad) && (param->mvRefine < 1 || param->mvRefine > 3),\n'
                    '    "Invalid mv refinement level. Value must be between 1 and 3 (inclusive)");\n',
                    1,
                ),
            },
        )
        expect_fail(run_checker(root), 'Analysis/reuse/refine range checks must stay aligned with the reviewed parsed-field validation order')

    print('Analysis/reuse/refine parse safety tests passed')

if __name__ == '__main__':
    main()
