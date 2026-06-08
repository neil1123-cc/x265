#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/common/param.cpp')
FORBIDDEN_SNIPPETS = (
    '#define atoi(str) x265_atoi(str, bError)',
    '#define atof(str) x265_atof(str, bError)',
)
GLOBAL_REQUIRED_SNIPPETS = (
    'int x265_param_parse(x265_param* p, const char* name, const char* value)',
)
PRIMARY_REQUIRED_SNIPPETS = (
    '#define atobool(str) (bNameWasBool = true, x265_atobool(str, bError))',
    'OPT("pmode")',
    'p->bDistributeModeAnalysis = x265_atobool(value, bError);',
    'OPT("pme")',
    'p->bDistributeMotionEstimation = x265_atobool(value, bError);',
    'OPT("high-tier")',
    'p->bHighTier = x265_atobool(value, bError);',
    'OPT("allow-non-conformance")',
    'p->bAllowNonConformance = x265_atobool(value, bError);',
    'OPT("rect")',
    'p->bEnableRectInter = x265_atobool(value, bError);',
    'OPT("amp")',
    'p->bEnableAMP = x265_atobool(value, bError);',
    'OPT("temporal-mvp")',
    'p->bEnableTemporalMvp = x265_atobool(value, bError);',
    'OPT("early-skip")',
    'p->bEnableEarlySkip = x265_atobool(value, bError);',
    'OPT("tskip")',
    'p->bEnableTransformSkip = x265_atobool(value, bError);',
    'OPT("no-tskip-fast")',
    'OPT("tskip-fast")',
    'p->bEnableTSkipFast = x265_atobool(value, bError);',
    'OPT("strong-intra-smoothing")',
    'p->bEnableStrongIntraSmoothing = x265_atobool(value, bError);',
    'OPT("lossless")',
    'p->bLossless = x265_atobool(value, bError);',
    'OPT("cu-lossless")',
    'p->bCULossless = x265_atobool(value, bError);',
    'OPT("constrained-intra")',
    'p->bEnableConstrainedIntra = x265_atobool(value, bError);',
    'OPT("fast-intra")',
    'p->bEnableFastIntra = x265_atobool(value, bError);',
    'OPT("open-gop")',
    'p->bOpenGOP = x265_atobool(value, bError);',
    'OPT("intra-refresh")',
    'p->bIntraRefresh = x265_atobool(value, bError);',
    'OPT("annexb")',
    'p->bAnnexB = x265_atobool(value, bError);',
    'OPT("repeat-headers")',
    'p->bRepeatHeaders = x265_atobool(value, bError);',
    'OPT("wpp")',
    'p->bEnableWavefront = x265_atobool(value, bError);',
    'OPT("limit-modes")',
    'p->limitModes = x265_atobool(value, bError);',
    'OPT("weightp")',
    'p->bEnableWeightedPred = x265_atobool(value, bError);',
    'OPT("weightb")',
    'p->bEnableWeightedBiPred = x265_atobool(value, bError);',
    'OPT("rd-refine")',
    'p->bEnableRdRefine = x265_atobool(value, bError);',
    'OPT("signhide")',
    'p->bEnableSignHiding = x265_atobool(value, bError);',
    'OPT("b-intra")',
    'p->bIntraInBFrames = x265_atobool(value, bError);',
    'OPT("sao")',
    'p->bEnableSAO = x265_atobool(value, bError);',
    'OPT("sao-non-deblock")',
    'p->bSaoNonDeblocked = x265_atobool(value, bError);',
    'OPT("ssim")',
    'p->bEnableSsim = x265_atobool(value, bError);',
    'OPT("psnr")',
    'p->bEnablePsnr = x265_atobool(value, bError);',
    'OPT("aud")',
    'p->bEnableAccessUnitDelimiters = x265_atobool(value, bError);',
    'OPT("info")',
    'p->bEmitInfoSEI = x265_atobool(value, bError);',
    'OPT("b-pyramid")',
    'p->bBPyramid = x265_atobool(value, bError);',
    'OPT("hrd")',
    'p->bEmitHRDSEI = x265_atobool(value, bError);',
    'OPT("hevc-aq")',
    'p->rc.hevcAq = x265_atobool(value, bError);',
    'OPT("limit-aq1")',
    'p->rc.limitAq1 = x265_atobool(value, bError);',
    'OPT("rc-grain")',
    'p->rc.bEnableGrain = x265_atobool(value, bError);',
    'OPT("cutree")',
    'p->rc.cuTree = x265_atobool(value, bError);',
    'OPT("slow-firstpass")',
    'p->rc.bEnableSlowFirstPass = x265_atobool(value, bError);',
)
PRIMARY_FORBIDDEN_SNIPPETS = (
    'OPT("pmode") p->bDistributeModeAnalysis = atobool(value);',
    'OPT("pme") p->bDistributeMotionEstimation = atobool(value);',
    'OPT("high-tier") p->bHighTier = atobool(value);',
    'OPT("allow-non-conformance") p->bAllowNonConformance = atobool(value);',
    'OPT("rect") p->bEnableRectInter = atobool(value);',
    'OPT("amp") p->bEnableAMP = atobool(value);',
    'OPT("temporal-mvp") p->bEnableTemporalMvp = atobool(value);',
    'OPT("early-skip") p->bEnableEarlySkip = atobool(value);',
    'OPT("tskip") p->bEnableTransformSkip = atobool(value);',
    'OPT("no-tskip-fast") p->bEnableTSkipFast = atobool(value);',
    'OPT("tskip-fast") p->bEnableTSkipFast = atobool(value);',
    'OPT("strong-intra-smoothing") p->bEnableStrongIntraSmoothing = atobool(value);',
    'OPT("lossless") p->bLossless = atobool(value);',
    'OPT("cu-lossless") p->bCULossless = atobool(value);',
    'OPT("constrained-intra") p->bEnableConstrainedIntra = atobool(value);',
    'OPT("fast-intra") p->bEnableFastIntra = atobool(value);',
    'OPT("open-gop") p->bOpenGOP = atobool(value);',
    'OPT("intra-refresh") p->bIntraRefresh = atobool(value);',
    'OPT("annexb") p->bAnnexB = atobool(value);',
    'OPT("repeat-headers") p->bRepeatHeaders = atobool(value);',
    'OPT("wpp") p->bEnableWavefront = atobool(value);',
    'OPT("limit-modes") p->limitModes = atobool(value);',
    'OPT("weightp") p->bEnableWeightedPred = atobool(value);',
    'OPT("weightb") p->bEnableWeightedBiPred = atobool(value);',
    'OPT("rd-refine") p->bEnableRdRefine = atobool(value);',
    'OPT("signhide") p->bEnableSignHiding = atobool(value);',
    'OPT("b-intra") p->bIntraInBFrames = atobool(value);',
    'OPT("sao") p->bEnableSAO = atobool(value);',
    'OPT("sao-non-deblock") p->bSaoNonDeblocked = atobool(value);',
    'OPT("ssim") p->bEnableSsim = atobool(value);',
    'OPT("psnr") p->bEnablePsnr = atobool(value);',
    'OPT("aud") p->bEnableAccessUnitDelimiters = atobool(value);',
    'OPT("info") p->bEmitInfoSEI = atobool(value);',
    'OPT("b-pyramid") p->bBPyramid = atobool(value);',
    'OPT("hrd") p->bEmitHRDSEI = atobool(value);',
    'OPT("hevc-aq") p->rc.hevcAq = atobool(value);',
    'OPT("limit-aq1") p->rc.limitAq1 = atobool(value);',
    'OPT("rc-grain") p->rc.bEnableGrain = atobool(value);',
    'OPT("cutree")    p->rc.cuTree = atobool(value);',
    'OPT("slow-firstpass") p->rc.bEnableSlowFirstPass = atobool(value);',
)
EXTRA_REQUIRED_SNIPPETS = (
    'OPT("uhd-bd")',
    'p->uhdBluray = x265_atobool(value, bError);',
    'OPT("analyze-src-pics")',
    'p->bSourceReferenceEstimation = x265_atobool(value, bError);',
    'OPT("vui-timing-info")',
    'p->bEmitVUITimingInfo = x265_atobool(value, bError);',
    'OPT("vui-hrd-info")',
    'p->bEmitVUIHRDInfo = x265_atobool(value, bError);',
)
EXTRA_FORBIDDEN_SNIPPETS = (
    'OPT("uhd-bd") p->uhdBluray = atobool(value);',
    'OPT("analyze-src-pics") p->bSourceReferenceEstimation = atobool(value);',
    'OPT("vui-timing-info") p->bEmitVUITimingInfo = atobool(value);',
    'OPT("vui-hrd-info") p->bEmitVUIHRDInfo = atobool(value);',
)


def extract_param_macro_region(text):
    marker = 'int x265_param_parse(x265_param* p, const char* name, const char* value)'
    index = text.find(marker)
    if index < 0:
        return '', ''
    start = text.rfind('/* internal versions of string-to-int with additional error checking */', 0, index)
    if start < 0:
        start = 0
    return text[start:index], text[index:]


def extract_bool_cleanup_window(text):
    start_marker = '    OPT("pmode")'
    end_marker = '    OPT("strict-cbr")'
    start = text.find(start_marker)
    if start < 0:
        return ''
    end = text.find(end_marker, start)
    if end < 0:
        return text[start:]
    return text[start:end]


def extract_extra_bool_cleanup_window(text):
    start_marker = '    OPT("uhd-bd")'
    end_marker = '        OPT("slices")'
    start = text.find(start_marker)
    if start < 0:
        return ''
    end = text.find(end_marker, start)
    if end < 0:
        return text[start:]
    return text[start:end]


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    macro_text, after_text = extract_param_macro_region(text)
    if not after_text:
        return [(TARGET.as_posix(), 0, 'missing x265_param_parse parser')]

    failures = []
    bool_window = extract_bool_cleanup_window(after_text)
    if not bool_window:
        failures.append((TARGET.as_posix(), 0, 'missing param parse bool cleanup window'))
        return failures
    extra_bool_window = extract_extra_bool_cleanup_window(after_text)
    if not extra_bool_window:
        failures.append((TARGET.as_posix(), 0, 'missing param parse extra bool cleanup window'))
        return failures
    for snippet in GLOBAL_REQUIRED_SNIPPETS:
        if snippet not in after_text and snippet not in macro_text:
            failures.append((TARGET.as_posix(), 0, f'missing param parse cleanup guardrail: {snippet}'))
    for snippet in PRIMARY_REQUIRED_SNIPPETS:
        if snippet not in bool_window and snippet not in macro_text:
            failures.append((TARGET.as_posix(), 0, f'missing param parse cleanup guardrail: {snippet}'))
    for snippet in EXTRA_REQUIRED_SNIPPETS:
        if snippet not in extra_bool_window and snippet not in macro_text:
            failures.append((TARGET.as_posix(), 0, f'missing param parse cleanup guardrail: {snippet}'))
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in macro_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden param parse macro regression: {snippet}'))
    for snippet in PRIMARY_FORBIDDEN_SNIPPETS:
        if snippet in bool_window:
            failures.append((TARGET.as_posix(), 0, f'forbidden param parse bool macro regression: {snippet}'))
    for snippet in EXTRA_FORBIDDEN_SNIPPETS:
        if snippet in extra_bool_window:
            failures.append((TARGET.as_posix(), 0, f'forbidden param parse bool macro regression: {snippet}'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check x265_param_parse macro cleanup guardrails')
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

    print('param parse macro cleanup validated')


if __name__ == '__main__':
    main()
