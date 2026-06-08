#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_param_checked_parse_usage.py')

# Normalized checker probes used by the coverage scan for checked-parse guardrails.
NORMALIZED_PROBES = (
    'forbidden checked-parse regression: ',
    'missing checked-parse guardrail: ',
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
                    'p->selectiveSAO = x265_atoi(value, bError);',
                    'OPT("scenecut-aware-qp") p->bEnableSceneCutAwareQp = x265_atoi(value, bError);',
                    'OPT("dup-threshold") p->dupThreshold = x265_atoi(value, bError);',
                    'static void assignParsedOptionLevels(const int parsed[3], int count, int target[3])',
                    'if (count == 1)\n        target[0] = target[1] = target[2] = parsed[0];',
                    'for (int level = 0; level < 3; level++)\n            target[level] = parsed[level];',
                    'int count = splitCommaOption(value, search, searchLengths, 3);',
                    'parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);',
                    'assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);',
                    'if (splitCommaOption(value, range, rangeLengths, 3) != 3)',
                    'parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);',
                    'assignParsedOptionLevels(parsed, 3, p->hmeRange);',
                    'static uint8_t parseOptionUint8Token(const char* token, size_t length, bool& bError)',
                    'static uint8_t parseOptionUint8Value(const char* value, bool& bError)',
                    'static int parseOptionIntValue(const char* value, bool& bError)',
                    'static int parseOptionIntValue(const char* value, bool& bError)\n{\n    if (!value)\n    {\n        bError = true;\n        return 0;\n    }',
                    'static uint8_t parseOptionUint8Value(const char* value, bool& bError)\n{\n    if (!value)\n    {\n        bError = true;\n        return 0;\n    }',
                    'int encoderBitDepth = parseOptionIntValue(value, bEncoderBitDepthError);',
                    'int framesToBeEncoded = parseOptionIntValue(value, bFramesToBeEncodedError);',
                    'int minQpAllowed = parseOptionIntValue(value, bMinQpAllowedError);',
                    'int maxQpAllowed = parseOptionIntValue(value, bMaxQpAllowedError);',
                    'int lookAheadDistance = parseOptionIntValue(value, bLookAheadDistanceError);',
                    'int intraPeriodLength = parseOptionIntValue(value, bIntraPeriodLengthError);',
                    'int qp = parseOptionIntValue(value, bQpValueError);',
                    'int bitrate = parseOptionIntValue(value, bBitrateValueError);',
                    'int searchAreaWidth = parseOptionIntValue(value, bSearchAreaWidthError);',
                    'int searchAreaHeight = parseOptionIntValue(value, bSearchAreaHeightError);',
                    'int hierarchicalLevels = parseOptionIntValue(value, bHierarchicalLevelsError);',
                    'int baseLayerSwitchMode = parseOptionIntValue(value, bBaseLayerSwitchModeError);',
                    'int vbvMaxrate = parseOptionIntValue(value, bVbvMaxrateError);',
                    'int vbvBufsize = parseOptionIntValue(value, bVbvBufsizeError);',
                    'int threadCount = parseOptionIntValue(value, bThreadCountError);',
                    'uint8_t predStructure = parseOptionUint8Value(value, bPredStructureError);',
                    'uint8_t useMasteringDisplayColorVolume = parseOptionUint8Value(value, bMasterDisplayError);',
                    'uint8_t useNaluFile = parseOptionUint8Value(value, bNaluFileError);',
                    'static bool parseTenthsOrIntegerLevel(const char* value, int& parsedLevel)',
                    'if (!parseTenthsOrIntegerLevel(value, p->levelIdc))',
                    'if (!parseTenthsOrIntegerLevel(value, p->dolbyProfile))',
                    'if (!parseTenthsOrIntegerLevel(value, svtHevcParam->level))',
                    'if (!parseTenthsOrIntegerLevel(value, svtHevcParam->dolbyVisionProfile))',
                    'static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)',
                    'static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)',
                    'bError |= !parseIndexedNameOrNumber(value, logLevelNames, -1, p->logLevel);',
                    'bError |= !parseIndexedNameOrNumber(value, logLevelNames, -1, p->logfLevel);',
                    'static uint32_t parseOptionUint32Token(const char* token, size_t length, bool& bError)',
                    'int frameNumThreads = parseOptionIntValue(value, bFrameNumThreadsError);',
                    'int totalFrames = parseOptionIntValue(value, bTotalFramesError);',
                    'bool bMaxCUSizeError = false;',
                    'uint32_t maxCUSize = parseOptionUint32Token(value, std::strlen(value), bMaxCUSizeError);',
                    'bool bMinCUSizeError = false;',
                    'uint32_t minCUSize = parseOptionUint32Token(value, std::strlen(value), bMinCUSizeError);',
                    'bool bTuQTMaxIntraDepthError = false;',
                    'uint32_t tuQTMaxIntraDepth = parseOptionUint32Token(value, std::strlen(value), bTuQTMaxIntraDepthError);',
                    'bool bTuQTMaxInterDepthError = false;',
                    'uint32_t tuQTMaxInterDepth = parseOptionUint32Token(value, std::strlen(value), bTuQTMaxInterDepthError);',
                    'bool bMaxTUSizeError = false;',
                    'uint32_t maxTUSize = parseOptionUint32Token(value, std::strlen(value), bMaxTUSizeError);',
                    'int subpelRefine = parseOptionIntValue(value, bSubpelRefineError);',
                    'int searchRange = parseOptionIntValue(value, bSearchRangeError);',
                    'bool bMaxNumMergeCandError = false;',
                    'uint32_t maxNumMergeCand = parseOptionUint32Token(value, std::strlen(value), bMaxNumMergeCandError);',
                    'OPT("lookahead-slices") p->lookaheadSlices = x265_atoi(value, bError);',
                    'OPT("temporal-layers") p->bEnableTemporalSubLayers = x265_atoi(value, bError);',
                    'OPT("keyint") p->keyframeMax = x265_atoi(value, bError);',
                    'OPT("min-keyint") p->keyframeMin = x265_atoi(value, bError);',
                    'OPT("rc-lookahead") p->lookaheadDepth = x265_atoi(value, bError);',
                    'OPT("bframes") p->bframes = x265_atoi(value, bError);',
                    'OPT("bframe-bias") p->bFrameBias = x265_atoi(value, bError);',
                    'static bool parseBoolOrIntValue(const char* value, int& parsedValue)',
                    'bError |= !parseBoolOrIntValue(value, p->scenecutThreshold);',
                    'bError |= !parseBoolOrIntValue(value, p->bFrameAdaptive);',
                    'static bool parseBoolOrNamedValue(const char* value, const char* const* names, int& parsedValue)',
                    'bError |= !parseBoolOrNamedValue(value, x265_interlace_names, p->interlaceMode);',
                    'OPT("ref") p->maxNumReferences = x265_atoi(value, bError);',
                    'OPT("limit-refs") p->limitReferences = x265_atoi(value, bError);',
                    'OPT("cbqpoffs") p->cbQpOffset = x265_atoi(value, bError);',
                    'OPT("crqpoffs") p->crQpOffset = x265_atoi(value, bError);',
                    'OPT("rd") p->rdLevel = x265_atoi(value, bError);',
                    'int qScaleMode = parseOptionIntValue(value, bQScaleModeError);',
                    'int qpStep = parseOptionIntValue(value, bQpStepError);',
                    'int aqMode = parseOptionIntValue(value, bAqModeError);',
                    'static bool parseBoolOrNumericInt(const char* value, int falseValue, int& parsedValue)',
                    'static bool parseBoolOrNumericDouble(const char* value, double falseValue, double& parsedValue)',
                    'bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel);',
                    'bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRd);',
                    'bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRdoq);',
                    'int psyScaleB = parseOptionIntValue(value, bPsyScaleBError);',
                    'int psyScaleP = parseOptionIntValue(value, bPsyScalePError);',
                    'int psyScaleI = parseOptionIntValue(value, bPsyScaleIError);',
                    'int decodedPictureHashSEI = parseOptionIntValue(value, bDecodedPictureHashSEIError);',
                    'OPT("qscale-mode") p->rc.qScaleMode = x265_atoi(value, bError);',
                    'OPT("qpstep") p->rc.qpStep = x265_atoi(value, bError);',
                    'OPT("aq-mode") p->rc.aqMode = x265_atoi(value, bError);',
                    'int rdPenalty = parseOptionIntValue(value, bRdPenaltyError);',
                    'int radl = parseOptionIntValue(value, bRadlError);',
                    'int parsedPass = parseOptionIntValue(value, bPassError);',
                    'int analysisSaveReuseLevel = parseOptionIntValue(value, bAnalysisSaveReuseLevelError);',
                    'int analysisLoadReuseLevel = parseOptionIntValue(value, bAnalysisLoadReuseLevelError);',
                    'OPT("qpmax")       p->rc.qpMax = x265_atoi(value, bError);',
                    'int qpMin = parseOptionIntValue(value, bQpMinError);',
                    'p->rc.bitrate = x265_atoi(value, bError);',
                    'p->rc.qp = x265_atoi(value, bError);',
                    'int csvLogLevel = parseOptionIntValue(value, bCsvLogLevelError);',
                    'int log2MaxPocLsb = parseOptionIntValue(value, bLog2MaxPocLsbError);',
                    'int maxSlices = parseOptionIntValue(value, bMaxSlicesError);',
                    'int limitTU = parseOptionIntValue(value, bLimitTUError);',
                    'int lookaheadThreads = parseOptionIntValue(value, bLookaheadThreadsError);',
                    'int analysisSaveReuseLevel = parseOptionIntValue(value, bAnalysisSaveReuseLevelError);',
                    'int analysisLoadReuseLevel = parseOptionIntValue(value, bAnalysisLoadReuseLevelError);',
                    'int noiseReductionIntra = parseOptionIntValue(value, bNoiseReductionIntraError);',
                    'int noiseReductionInter = parseOptionIntValue(value, bNoiseReductionInterError);',
                    'OPT("rdpenalty") p->rdPenalty = x265_atoi(value, bError);',
                    'OPT("vbv-maxrate") p->rc.vbvMaxBitrate = x265_atoi(value, bError);',
                    'OPT("vbv-bufsize") p->rc.vbvBufferSize = x265_atoi(value, bError);',
                    'int chromaSampleLocType = parseOptionIntValue(value, bChromaSampleLocTypeError);',
                    'int pass = x265_clip3(0, 3, x265_atoi(value, bError));',
                    'int qgSize = parseOptionIntValue(value, bQgSizeError);',
                    'OPT("min-luma") p->minLuma = parseOptionUint16Token(value, std::strlen(value), bError);',
                    'OPT("max-luma") p->maxLuma = parseOptionUint16Token(value, std::strlen(value), bError);',
                    'int ctuInfo = parseOptionIntValue(value, bCTUInfoError);',
                    'int scaleFactor = parseOptionIntValue(value, bScaleFactorError);',
                    'int intraRefine = parseOptionIntValue(value, bIntraRefineError);',
                    'int interRefine = parseOptionIntValue(value, bInterRefineError);',
                    'int mvRefine = parseOptionIntValue(value, bMvRefineError);',
                    'int forceFlush = parseOptionIntValue(value, bForceFlushError);',
                    'int gopLookahead = parseOptionIntValue(value, bGopLookaheadError);',
                    'OPT("radl") p->radl = x265_atoi(value, bError);',
                    'int preferredTransferCharacteristics = parseOptionIntValue(value, bPreferredTransferCharacteristicsError);',
                    'int pictureStructure = parseOptionIntValue(value, bPictureStructureError);',
                    'int chunkStart = parseOptionIntValue(value, bChunkStartError);',
                    'int chunkEnd = parseOptionIntValue(value, bChunkEndError);',
                    'int recursionSkipMode = parseOptionIntValue(value, bRecursionSkipModeError);',
                    'int edgeVarThreshold = parseOptionIntValue(value, bEdgeVarThresholdError);',
                    'int ctuDistortionRefine = parseOptionIntValue(value, bCtuDistortionRefineError);',
                    'int cpuid = parseCpuName(value, bCpuNameError, false);',
                    'p->cpuid = cpuid;',
                    'int selectiveSao = parseOptionIntValue(value, bSelectiveSaoError);',
                    'int dupThreshold = parseOptionIntValue(value, bDupThresholdError);',
                    'int format = parseOptionIntValue(value, bFormatError);',
                    'int numViews = parseOptionIntValue(value, bNumViewsError);',
                    'int bEnableSCC = parseOptionIntValue(value, bSccError);',
                    'int sceneCutAwareQp = parseOptionIntValue(value, bSceneCutAwareQpError);',
                    'OPT("aq-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.aqStrength);',
                    'OPT("aq-bias-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.aqBiasStrength);',
                    'OPT("limit-aq1-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.limitAq1Strength);',
                    'OPT("dynamic-rd") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->dynamicRd);',
                    'OPT("ipratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.ipFactor);',
                    'OPT("pbratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.pbFactor);',
                    'if (!parseOptionDoubleToken(value, std::strlen(value), qCompress))',
                    'OPT("cutree-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.cuTreeStrength);',
                    'OPT("cutree-minqpoffs") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.cuTreeMinQpOffset);',
                    'OPT("cutree-maxqpoffs") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.cuTreeMaxQpOffset);',
                    'OPT("cplxblur") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.complexityBlur);',
                    'OPT("qblur") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.qblur);',
                    'OPT("vbv-init")    bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.vbvBufferInit);',
                    'OPT("crf-max")     bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.rfConstantMax);',
                    'OPT("crf-min")     bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.rfConstantMin);',
                    'if (!parseOptionDoubleToken(value, std::strlen(value), p->rc.rfConstant))',
                    'OPT("vbv-end") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvBufferEnd);',
                    'OPT("vbv-end-fr-adj") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvEndFrameAdjust);',
                    'OPT("max-ausize-factor") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxAUSizeFactor);',
                    'OPT("qp-adaptation-range") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.qpAdaptationRange);',
                    'OPT("min-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->minVbvFullness);',
                    'OPT("max-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxVbvFullness);',
                    'OPT("scenecut-bias") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->scenecutBias);',
                    'p->rc.zones[i].startFrame = x265_atoi(c, bZoneValueError);',
                    'p->rc.zones[i].endFrame = x265_atoi(firstComma + 1, bZoneValueError);',
                    'p->rc.zones[i].qp = x265_atoi(modeValue, bZoneValueError);',
                    'p->rc.zones[i].bitrateFactor = x265_atof(modeValue, bZoneValueError);',
                    'svtHevcParam->vbvMaxrate = (uint32_t)x265_atoi(value, bError);',
                    'svtHevcParam->vbvBufsize = (uint32_t)x265_atoi(value, bError);',
                    'bVbvBufInitError = !parseOptionDoubleToken(value, std::strlen(value), vbvBufInit);',
                    'svtHevcParam->threadCount = (uint32_t)x265_atoi(value, bError);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/common/param.cpp': 'p->cpuid = parseCpuName(value, bError, false);\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden checked-parse regression')

    print('Checked parse guard tests passed')


if __name__ == '__main__':
    main()
