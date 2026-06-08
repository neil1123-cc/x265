#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
PARSE_REQUIRED_SNIPPETS = (
    'OPT("analysis-save-reuse-level")',
    'bool bAnalysisSaveReuseLevelError = false;',
    'int analysisSaveReuseLevel = parseOptionIntValue(value, bAnalysisSaveReuseLevelError);',
    'if (!bAnalysisSaveReuseLevelError)',
    'p->analysisSaveReuseLevel = analysisSaveReuseLevel;',
    'OPT("analysis-load-reuse-level")',
    'bool bAnalysisLoadReuseLevelError = false;',
    'int analysisLoadReuseLevel = parseOptionIntValue(value, bAnalysisLoadReuseLevelError);',
    'if (!bAnalysisLoadReuseLevelError)',
    'p->analysisLoadReuseLevel = analysisLoadReuseLevel;',
    'OPT("scale-factor")',
    'bool bScaleFactorError = false;',
    'int scaleFactor = parseOptionIntValue(value, bScaleFactorError);',
    'if (!bScaleFactorError)',
    'p->scaleFactor = scaleFactor;',
    'OPT("refine-intra")',
    'bool bIntraRefineError = false;',
    'int intraRefine = parseOptionIntValue(value, bIntraRefineError);',
    'if (!bIntraRefineError)',
    'p->intraRefine = intraRefine;',
    'OPT("refine-inter")',
    'bool bInterRefineError = false;',
    'int interRefine = parseOptionIntValue(value, bInterRefineError);',
    'if (!bInterRefineError)',
    'p->interRefine = interRefine;',
    'OPT("refine-mv")',
    'bool bMvRefineError = false;',
    'int mvRefine = parseOptionIntValue(value, bMvRefineError);',
    'if (!bMvRefineError)',
    'p->mvRefine = mvRefine;',
    'OPT("refine-ctu-distortion")',
    'bool bCtuDistortionRefineError = false;',
    'int ctuDistortionRefine = parseOptionIntValue(value, bCtuDistortionRefineError);',
    'if (!bCtuDistortionRefineError)',
    'p->ctuDistortionRefine = ctuDistortionRefine;',
)
VALIDATION_REQUIRED_SNIPPETS = (
    'CHECK(strlen(param->analysisLoad) && (param->analysisLoadReuseLevel < 0 || param->analysisLoadReuseLevel > 10),',
    'CHECK(strlen(param->analysisLoad) && (param->mvRefine < 1 || param->mvRefine > 3),',
    'CHECK(param->scaleFactor < 0 || param->scaleFactor > 2, "Invalid scale-factor. Supports factor between 0 and 2");',
    'CHECK(param->interRefine > 3 || param->interRefine < 0,',
    'CHECK(param->intraRefine > 4 || param->intraRefine < 0,',
    'CHECK(param->ctuDistortionRefine < 0 || param->ctuDistortionRefine > 1,',
)
FORBIDDEN_SNIPPETS = (
    'OPT("analysis-save-reuse-level") p->analysisSaveReuseLevel = x265_atoi(value, bError);',
    'OPT("analysis-load-reuse-level") p->analysisLoadReuseLevel = x265_atoi(value, bError);',
    'OPT("scale-factor") p->scaleFactor = x265_atoi(value, bError);',
    'OPT("refine-intra")p->intraRefine = x265_atoi(value, bError);',
    'OPT("refine-inter")p->interRefine = x265_atoi(value, bError);',
    'OPT("refine-mv")p->mvRefine = x265_atoi(value, bError);',
    'OPT("refine-ctu-distortion") p->ctuDistortionRefine = x265_atoi(value, bError);',
)
PARSE_REGION_START = 'OPT("analysis-save-reuse-level")'
PARSE_REGION_END = 'OPT("hevc-aq")'
VALIDATION_REGION_START = 'CHECK(strlen(param->analysisLoad) && (param->analysisLoadReuseLevel < 0 || param->analysisLoadReuseLevel > 10),'
VALIDATION_REGION_END = 'CHECK(param->maxAUSizeFactor < 0.5 || param->maxAUSizeFactor > 1.0,'


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
    parse_region = get_region(text, PARSE_REGION_START, PARSE_REGION_END)
    validation_region = get_region(text, VALIDATION_REGION_START, VALIDATION_REGION_END)
    failures = []
    for forbidden in FORBIDDEN_SNIPPETS:
        if forbidden in text:
            failures.append((TARGET.as_posix(), 0, 'forbidden analysis/reuse/refine regression: invalid values must not overwrite prior state'))
            return failures
    for snippet in PARSE_REQUIRED_SNIPPETS:
        if snippet not in parse_region:
            failures.append((TARGET.as_posix(), 0, f'missing analysis/reuse/refine guardrail: {snippet}'))
    for snippet in VALIDATION_REQUIRED_SNIPPETS:
        if snippet not in validation_region:
            failures.append((TARGET.as_posix(), 0, f'missing analysis/reuse/refine guardrail: {snippet}'))
    if all(snippet in parse_region for snippet in PARSE_REQUIRED_SNIPPETS):
        if not has_in_order(
            parse_region,
            (
                'OPT("analysis-save-reuse-level")',
                'bool bAnalysisSaveReuseLevelError = false;',
                'int analysisSaveReuseLevel = parseOptionIntValue(value, bAnalysisSaveReuseLevelError);',
                'bError |= bAnalysisSaveReuseLevelError;',
                'if (!bAnalysisSaveReuseLevelError)',
                'p->analysisSaveReuseLevel = analysisSaveReuseLevel;',
                'OPT("analysis-load-reuse-level")',
                'bool bAnalysisLoadReuseLevelError = false;',
                'int analysisLoadReuseLevel = parseOptionIntValue(value, bAnalysisLoadReuseLevelError);',
                'bError |= bAnalysisLoadReuseLevelError;',
                'if (!bAnalysisLoadReuseLevelError)',
                'p->analysisLoadReuseLevel = analysisLoadReuseLevel;',
                'OPT("scale-factor")',
                'bool bScaleFactorError = false;',
                'int scaleFactor = parseOptionIntValue(value, bScaleFactorError);',
                'bError |= bScaleFactorError;',
                'if (!bScaleFactorError)',
                'p->scaleFactor = scaleFactor;',
                'OPT("refine-intra")',
                'bool bIntraRefineError = false;',
                'int intraRefine = parseOptionIntValue(value, bIntraRefineError);',
                'bError |= bIntraRefineError;',
                'if (!bIntraRefineError)',
                'p->intraRefine = intraRefine;',
                'OPT("refine-inter")',
                'bool bInterRefineError = false;',
                'int interRefine = parseOptionIntValue(value, bInterRefineError);',
                'bError |= bInterRefineError;',
                'if (!bInterRefineError)',
                'p->interRefine = interRefine;',
                'OPT("refine-mv")',
                'bool bMvRefineError = false;',
                'int mvRefine = parseOptionIntValue(value, bMvRefineError);',
                'bError |= bMvRefineError;',
                'if (!bMvRefineError)',
                'p->mvRefine = mvRefine;',
                'OPT("refine-ctu-distortion")',
                'bool bCtuDistortionRefineError = false;',
                'int ctuDistortionRefine = parseOptionIntValue(value, bCtuDistortionRefineError);',
                'bError |= bCtuDistortionRefineError;',
                'if (!bCtuDistortionRefineError)',
                'p->ctuDistortionRefine = ctuDistortionRefine;',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Analysis/reuse/refine parsing must stage parsed integers and only publish them after the reviewed error gates succeed'))
    if all(snippet in validation_region for snippet in VALIDATION_REQUIRED_SNIPPETS):
        if not has_in_order(
            validation_region,
            (
                'CHECK(strlen(param->analysisLoad) && (param->analysisLoadReuseLevel < 0 || param->analysisLoadReuseLevel > 10),',
                'CHECK(strlen(param->analysisLoad) && (param->mvRefine < 1 || param->mvRefine > 3),',
                'CHECK(param->scaleFactor < 0 || param->scaleFactor > 2, "Invalid scale-factor. Supports factor between 0 and 2");',
                'CHECK(param->interRefine > 3 || param->interRefine < 0,',
                'CHECK(param->intraRefine > 4 || param->intraRefine < 0,',
                'CHECK(param->ctuDistortionRefine < 0 || param->ctuDistortionRefine > 1,',
            ),
        ):
            failures.append((TARGET.as_posix(), 0, 'Analysis/reuse/refine range checks must stay aligned with the reviewed parsed-field validation order'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check analysis/reuse/refine parse safety guardrails')
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

    print('Analysis/reuse/refine parse safety validated')


if __name__ == '__main__':
    main()
