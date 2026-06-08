/*****************************************************************************
 * Copyright (C) 2013-2020 MulticoreWare, Inc
 *
 * Authors: Deepthi Nandakumar <deepthi@multicorewareinc.com>
 *          Min Chen <min.chen@multicorewareinc.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02111, USA.
 *
 * This program is also available under a commercial proprietary license.
 * For more information, contact us at license @ x265.com.
 *****************************************************************************/

#include "common.h"
#include "slice.h"
#include "threading.h"
#include "threadpool.h"
#include "param.h"
#include "cpu.h"
#include "x265.h"
#include "svt.h"

#include <charconv>
#include <cctype>
#include <cerrno>

#if _MSC_VER
#pragma warning(disable: 4996) // POSIX functions are just fine, thanks
#pragma warning(disable: 4706) // assignment within conditional
#pragma warning(disable: 4127) // conditional expression is constant
#endif

#if _WIN32
#define strcasecmp _stricmp
#endif

#if !defined(HAVE_STRTOK_R)

/*
 * adapted from public domain strtok_r() by Charlie Gordon
 *
 *   from comp.lang.c  9/14/2007
 *
 *      http://groups.google.com/group/comp.lang.c/msg/2ab1ecbb86646684
 *
 *     (Declaration that it's public domain):
 *      http://groups.google.com/group/comp.lang.c/msg/7c7b39328fefab9c
 */

#undef strtok_r
static char* strtok_r(char* str, const char* delim, char** nextp)
{
    if (!str)
        str = *nextp;

    str += strspn(str, delim);

    if (!*str)
        return nullptr;

    char *ret = str;

    str += strcspn(str, delim);

    if (*str)
        *str++ = '\0';

    *nextp = str;

    return ret;
}

#endif // if !defined(HAVE_STRTOK_R)

#if EXPORT_C_API

/* these functions are exported as C functions (default) */
using namespace X265_NS;
extern "C" {

#else

/* these functions exist within private namespace (multilib) */
namespace X265_NS {

#endif

struct ParamInstance
{
    x265_param* param;
    ParamInstance* next;
};

static Lock g_paramInstanceLock;
static ParamInstance* g_paramInstances;

static bool registerParamInstance(x265_param* param)
{
    if (!param)
        return false;

    ScopedLock lock(g_paramInstanceLock);
    for (ParamInstance* entry = g_paramInstances; entry; entry = entry->next)
    {
        if (entry->param == param)
            return true;
    }

    ParamInstance* entry = (ParamInstance*)x265_malloc(sizeof(ParamInstance));
    if (!entry)
        return false;
    entry->param = param;
    entry->next = g_paramInstances;
    g_paramInstances = entry;
    return true;
}

static void unregisterParamInstance(x265_param* param)
{
    ScopedLock lock(g_paramInstanceLock);
    ParamInstance** current = &g_paramInstances;
    while (*current)
    {
        ParamInstance* entry = *current;
        if (entry->param == param)
        {
            *current = entry->next;
            x265_free(entry);
            return;
        }
        current = &entry->next;
    }
}

bool isAllocatedParamInstance(const x265_param* param)
{
    if (!param)
        return false;

    ScopedLock lock(g_paramInstanceLock);
    for (ParamInstance* entry = g_paramInstances; entry; entry = entry->next)
        if (entry->param == param)
            return true;
    return false;
}

#ifdef SVT_HEVC
struct SvtHevcParamStorage
{
    x265_param* owner;
    EB_H265_ENC_CONFIGURATION* storage;
    SvtHevcParamStorage* next;
};

static Lock g_svtHevcParamStorageLock;
static SvtHevcParamStorage* g_svtHevcParamStorage;

static EB_H265_ENC_CONFIGURATION* getSvtHevcParamStorage(x265_param* param)
{
    ScopedLock lock(g_svtHevcParamStorageLock);
    for (SvtHevcParamStorage* entry = g_svtHevcParamStorage; entry; entry = entry->next)
        if (entry->owner == param)
            return entry->storage;
    return nullptr;
}

static bool registerSvtHevcParamStorage(x265_param* param, EB_H265_ENC_CONFIGURATION* storage)
{
    if (!param || !storage)
        return false;

    ScopedLock lock(g_svtHevcParamStorageLock);
    for (SvtHevcParamStorage* entry = g_svtHevcParamStorage; entry; entry = entry->next)
    {
        if (entry->owner == param)
        {
            entry->storage = storage;
            return true;
        }
    }

    SvtHevcParamStorage* entry = (SvtHevcParamStorage*)x265_malloc(sizeof(SvtHevcParamStorage));
    if (!entry)
        return false;
    entry->owner = param;
    entry->storage = storage;
    entry->next = g_svtHevcParamStorage;
    g_svtHevcParamStorage = entry;
    return true;
}

static EB_H265_ENC_CONFIGURATION* unregisterSvtHevcParamStorage(x265_param* param)
{
    ScopedLock lock(g_svtHevcParamStorageLock);
    SvtHevcParamStorage** current = &g_svtHevcParamStorage;
    while (*current)
    {
        SvtHevcParamStorage* entry = *current;
        if (entry->owner == param)
        {
            EB_H265_ENC_CONFIGURATION* storage = entry->storage;
            *current = entry->next;
            x265_free(entry);
            return storage;
        }
        current = &entry->next;
    }
    return nullptr;
}

static void freeSvtHevcParamStorage(x265_param* param)
{
    if (!param)
        return;

    EB_H265_ENC_CONFIGURATION* storage = unregisterSvtHevcParamStorage(param);
    if (!storage)
        storage = (EB_H265_ENC_CONFIGURATION*)param->svtHevcParam;
    x265_free(storage);
    param->svtHevcParam = nullptr;
}

static EB_H265_ENC_CONFIGURATION* ensureSvtHevcParam(x265_param* param, bool trackStorage = true)
{
    if (!param)
        return nullptr;

    EB_H265_ENC_CONFIGURATION* svtParam = (EB_H265_ENC_CONFIGURATION*)param->svtHevcParam;
    if (svtParam)
    {
        if (trackStorage && !registerSvtHevcParamStorage(param, svtParam))
            return nullptr;
        return svtParam;
    }

    svtParam = (EB_H265_ENC_CONFIGURATION*)x265_malloc(sizeof(EB_H265_ENC_CONFIGURATION));
    if (!svtParam)
        return nullptr;
    std::fill_n(reinterpret_cast<uint8_t*>(svtParam), sizeof(EB_H265_ENC_CONFIGURATION), uint8_t(0));
    if (trackStorage && !registerSvtHevcParamStorage(param, svtParam))
    {
        x265_free(svtParam);
        return nullptr;
    }
    param->svtHevcParam = svtParam;
    svt_param_default(param);

    return svtParam;
}

static bool copySvtHevcParamStorage(x265_param* dst, const x265_param* src)
{
    EB_H265_ENC_CONFIGURATION* srcSvtParam = src ? (EB_H265_ENC_CONFIGURATION*)src->svtHevcParam : nullptr;
    if (!srcSvtParam)
    {
        freeSvtHevcParamStorage(dst);
        return true;
    }

    EB_H265_ENC_CONFIGURATION* dstSvtParam = ensureSvtHevcParam(dst, false);
    if (!dstSvtParam)
        return false;

    memcpy(dstSvtParam, srcSvtParam, sizeof(EB_H265_ENC_CONFIGURATION));
    return true;
}
#endif

void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src)
{
    if (!zoneParam)
        return;

    resetZoneParamDetachedState(zoneParam);

#ifdef SVT_HEVC
    if (src && !copySvtHevcParamStorage(zoneParam, src))
        x265_log(nullptr, X265_LOG_ERROR, "unable to allocate SVT parameter storage\n");
#else
    (void)src;
#endif
}

static bool ensureZoneCopyDestination(x265_param* dst, const x265_param* src, bool zonefileCopy)
{
    if (!dst || !src)
        return false;

    const int zoneAllocCount = zonefileCopy ? src->rc.zonefileCount : src->rc.zoneCount;
    if (!zoneAllocCount)
        return true;

    bool canReuse = dst->rc.zones != nullptr;
    if (canReuse)
    {
        const int dstZoneAllocCount = zonefileCopy ? dst->rc.zonefileCount : dst->rc.zoneCount;
        canReuse = dstZoneAllocCount == zoneAllocCount;
        if (canReuse && zonefileCopy)
        {
            for (int i = 0; i < zoneAllocCount; i++)
            {
                if (!dst->rc.zones[i].zoneParam)
                {
                    canReuse = false;
                    break;
                }
            }
        }
        if (!canReuse)
            x265_zone_free(dst);
    }

    if (!dst->rc.zones)
    {
        dst->rc.zones = x265_zone_alloc(zoneAllocCount, zonefileCopy);
        if (!dst->rc.zones)
        {
            x265_log(nullptr, X265_LOG_ERROR, "unable to allocate zone storage\n");
            return false;
        }
        if (zonefileCopy)
            dst->rc.zonefileCount = zoneAllocCount;
        else
            dst->rc.zoneCount = zoneAllocCount;
    }

    return true;
}

static bool prepareFreshParamCopyDestination(x265_param* dst, const x265_param* src)
{
    if (!dst || !src)
        return false;

    std::fill_n(reinterpret_cast<uint8_t*>(dst), sizeof(x265_param), uint8_t(0));
#ifdef SVT_HEVC
    if (src->svtHevcParam && !ensureSvtHevcParam(dst))
    {
        x265_log(nullptr, X265_LOG_ERROR, "unable to allocate SVT parameter storage\n");
        return false;
    }
#endif

    const bool preserveDstZones = (src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig) ||
                                  (src->rc.zoneCount && src->rc.zones);
    const bool zonefileCopy = src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig;
    if (preserveDstZones && !ensureZoneCopyDestination(dst, src, zonefileCopy))
        return false;

    return true;
}

static const char* parsePresetIndexName(const char* preset);

x265_param *x265_param_alloc()
{
    x265_param* param = (x265_param*)x265_malloc(sizeof(x265_param));
    if (!param)
        return nullptr;

    std::fill_n(reinterpret_cast<uint8_t*>(param), sizeof(x265_param), uint8_t(0));
    if (!registerParamInstance(param))
    {
        x265_free(param);
        return nullptr;
    }
    return param;
}

void x265_param_free(x265_param* p)
{
    if (!p)
        return;

    x265_zone_free(p);
    if (p->logfn)
    {
        free(p->logfn);
        p->logfn = nullptr;
    }
    if (p->pgfn)
    {
        free(p->pgfn);
        p->pgfn = nullptr;
    }
#ifdef SVT_HEVC
    freeSvtHevcParamStorage(p);
#endif
    unregisterParamInstance(p);
    x265_free(p);
}

#if ENABLE_SCC_EXT
enum SCCProfileName
{
    NONE = 0,
    // The following are SCC profiles, which would map to the MAINSCC profile idc.
    // The enumeration indicates the bit-depth constraint in the bottom 2 digits
    //                           the chroma format in the next digit
    //                           the intra constraint in the next digit
    //                           If it is a SCC profile there is a '2' for the next digit.
    //                           If it is a highthroughput , there is a '2' for the top digit else '1' for the top digit
    SCC_MAIN = 121108,
    SCC_MAIN_10 = 121110,
    SCC_MAIN_444 = 121308,
    SCC_MAIN_444_10 = 121310,
};

static const SCCProfileName validSCCProfileNames[1][4/* bit depth constraint 8=0, 10=1, 12=2, 14=3*/][4/*chroma format*/] =
{
   {
        { NONE,         SCC_MAIN,      NONE,      SCC_MAIN_444                     }, // 8-bit  intra for 400, 420, 422 and 444
        { NONE,         SCC_MAIN_10,   NONE,      SCC_MAIN_444_10                  }, // 10-bit intra for 400, 420, 422 and 444
        { NONE,         NONE,          NONE,      NONE                             }, // 12-bit intra for 400, 420, 422 and 444
        { NONE,         NONE,          NONE,      NONE                             }  // 16-bit intra for 400, 420, 422 and 444
    },
};
#endif

void x265_param_default(x265_param* param)
{
    if (!param)
    {
        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default requires a non-null parameter struct\n");
        return;
    }

#ifdef SVT_HEVC
    EB_H265_ENC_CONFIGURATION* svtParam = getSvtHevcParamStorage(param);
#endif

    std::fill_n(reinterpret_cast<uint8_t*>(param), sizeof(x265_param), uint8_t(0));

    /* Applying default values to all elements in the param structure */
    param->cpuid = X265_NS::cpu_detect(false);
    param->bEnableWavefront = 1;
    param->frameNumThreads = 0;

    param->logLevel = X265_LOG_INFO;
    param->logfn = nullptr;
    param->logfLevel = X265_LOG_INFO;
    param->pgfn = nullptr;
    param->csvLogLevel = 0;
    param->csvfn[0] = 0;
    param->rc.lambdaFileName[0] = 0;
    param->decodedPictureHashSEI = 0;

    /* Quality Measurement Metrics */
    param->bEnablePsnr = 0;
    param->bEnableSsim = 0;

    /* Source specifications */
    param->internalBitDepth = X265_DEPTH;
    param->sourceBitDepth = 8;
    param->internalCsp = X265_CSP_I420;
    param->levelIdc = 0; //Auto-detect level
    param->uhdBluray = 0;
    param->bHighTier = 1; //Allow high tier by default
    param->interlaceMode = 0;
    param->bField = 0;
    param->bAnnexB = 1;
    param->bRepeatHeaders = 0;
    param->bEnableAccessUnitDelimiters = 0;
    param->bEnableEndOfBitstream = 0;
    param->bEnableEndOfSequence = 0;
    param->bEmitHRDSEI = 0;
    param->bEmitInfoSEI = 1;
    param->bEmitHDR10SEI = 0;
    param->bEmitIDRRecoverySEI = 0;

    /* CU definitions */
    param->maxCUSize = 64;
    param->minCUSize = 8;
    param->tuQTMaxInterDepth = 1;
    param->tuQTMaxIntraDepth = 1;
    param->maxTUSize = 32;

    /* Coding Structure */
    param->keyframeMin = 0;
    param->keyframeMax = 250;
    param->gopLookahead = 0;
    param->bOpenGOP = 1;
	param->craNal = 0;
    param->bframes = 4;
    param->lookaheadDepth = 20;
    param->bFrameAdaptive = X265_B_ADAPT_TRELLIS;
    param->bBPyramid = 1;
    param->scenecutThreshold = 40; /* Magic number pulled in from x264 */
    param->bHistBasedSceneCut = 0;
    param->lookaheadSlices = 8;
    param->lookaheadThreads = 0;
    param->scenecutBias = 5.0;
    param->radl = 0;
    param->chunkStart = 0;
    param->chunkEnd = 0;
    param->bEnableHRDConcatFlag = 0;
    param->bEnableFades = 0;
    param->bEnableSceneCutAwareQp = 0;
    param->fwdMaxScenecutWindow = 1200;
    param->bwdMaxScenecutWindow = 600;
    param->mcstfFrameRange = 2;
    for (int i = 0; i < 6; i++)
    {
        int deltas[6] = { 5, 4, 3, 2, 1, 0 };

        param->fwdScenecutWindow[i] = 200;
        param->fwdRefQpDelta[i] = deltas[i];
        param->fwdNonRefQpDelta[i] = param->fwdRefQpDelta[i] + (SLICE_TYPE_DELTA * param->fwdRefQpDelta[i]);

        param->bwdScenecutWindow[i] = 100;
        param->bwdRefQpDelta[i] = -1;
        param->bwdNonRefQpDelta[i] = -1;
    }

    /* Intra Coding Tools */
    param->bEnableConstrainedIntra = 0;
    param->bEnableStrongIntraSmoothing = 1;
    param->bEnableFastIntra = 0;
    param->bEnableSplitRdSkip = 0;

    /* Inter Coding tools */
    param->searchMethod = X265_HEX_SEARCH;
    param->subpelRefine = 2;
    param->searchRange = 57;
    param->maxNumMergeCand = 3;
    param->limitReferences = 1;
    param->limitModes = 0;
    param->bEnableWeightedPred = 1;
    param->bEnableWeightedBiPred = 0;
    param->bEnableEarlySkip = 1;
    param->recursionSkipMode = 1;
    param->edgeVarThreshold = 0.05f;
    param->bEnableAMP = 0;
    param->bEnableRectInter = 0;
    param->rdLevel = 3;
    param->rdoqLevel = 0;
    param->bEnableSignHiding = 1;
    param->bEnableTransformSkip = 0;
    param->bEnableTSkipFast = 0;
    param->maxNumReferences = 3;
    param->bEnableTemporalMvp = 1;
    param->bEnableHME = 0;
    param->hmeSearchMethod[0] = X265_HEX_SEARCH;
    param->hmeSearchMethod[1] = param->hmeSearchMethod[2] = X265_UMH_SEARCH;
    param->hmeRange[0] = 16;
    param->hmeRange[1] = 32;
    param->hmeRange[2] = 48;
    param->bSourceReferenceEstimation = 0;
    param->limitTU = 0;
    param->dynamicRd = 0;

    /* Loop Filter */
    param->bEnableLoopFilter = 1;

    /* SAO Loop Filter */
    param->bEnableSAO = 1;
    param->bSaoNonDeblocked = 0;
    param->bLimitSAO = 0;
    param->selectiveSAO = 0;

    /* Coding Quality */
    param->cbQpOffset = 0;
    param->crQpOffset = 0;
    param->rdPenalty = 0;
    param->psyRd = 2.0;
    param->psyRdoq = 0.0;
    param->psyScaleB = 300;
    param->psyScaleP = 256;
    param->psyScaleI = 96;
    param->analysisMultiPassRefine = 0;
    param->analysisMultiPassDistortion = 0;
    param->analysisReuseFileName[0] = 0;
    param->analysisSave[0] = 0;
    param->analysisLoad[0] = 0;
    param->bIntraInBFrames = 1;
    param->bLossless = 0;
    param->bCULossless = 0;
    param->bEnableTemporalSubLayers = 0;
    param->bEnableRdRefine = 0;
    param->bMultiPassOptRPS = 0;
    param->bSsimRd = 0;

    /* Rate control options */
    param->rc.vbvMaxBitrate = 0;
    param->rc.vbvBufferSize = 0;
    param->rc.vbvBufferInit = 0.9;
    param->vbvBufferEnd = 0;
    param->vbvEndFrameAdjust = 0;
    param->minVbvFullness = 50;
    param->maxVbvFullness = 80;
    param->rc.rfConstant = 28;
    param->rc.bitrate = 0;
    param->rc.qCompress = 0.6;
    param->rc.ipFactor = 1.4f;
    param->rc.pbFactor = 1.3f;
    param->rc.qpStep = 4;
    param->rc.rateControlMode = X265_RC_CRF;
    param->rc.qp = 32;
    param->rc.aqMode = X265_AQ_AUTO_VARIANCE;
    param->rc.hevcAq = 0;
    param->rc.qgSize = 32;
    param->rc.aqStrength = 1.0;
    param->rc.aqBiasStrength = 1.0;
    param->rc.qpAdaptationRange = 1.0;
    param->rc.cuTree = 1;
    param->rc.cuTreeStrength = (param->rc.hevcAq ? 6.0 : 5.0) * (1.0 - param->rc.qCompress);
    param->rc.cuTreeMinQpOffset = -QP_MAX_MAX;
    param->rc.cuTreeMaxQpOffset = QP_MAX_MAX;
    param->rc.qScaleMode = 0;
    param->rc.limitAq1 = 0;
    param->rc.limitAq1Strength = 1.0;
    param->rc.rfConstantMax = 0;
    param->rc.rfConstantMin = 0;
    param->rc.bStatRead = 0;
    param->rc.bStatWrite = 0;
    param->rc.dataShareMode = X265_SHARE_MODE_FILE;
    param->rc.statFileName[0] = 0;
    param->rc.sharedMemName[0] = 0;
    param->rc.bEncFocusedFramesOnly = 0;
    param->rc.complexityBlur = 20;
    param->rc.qblur = 0.5;
    param->rc.zoneCount = 0;
    param->rc.zonefileCount = 0;
    param->rc.zones = nullptr;
    param->rc.bEnableSlowFirstPass = 1;
    param->rc.bStrictCbr = 0;
    param->rc.bEnableGrain = 0;
    param->rc.qpMin = 0;
    param->rc.qpMax = QP_MAX_MAX;
    param->rc.bEnableConstVbv = 0;
    param->bResetZoneConfig = 1;
    param->reconfigWindowSize = 0;
    param->decoderVbvMaxRate = 0;
    param->bliveVBV2pass = 0;

    /* Video Usability Information (VUI) */
    param->vui.aspectRatioIdc = 0;
    param->vui.sarWidth = 0;
    param->vui.sarHeight = 0;
    param->vui.bEnableOverscanAppropriateFlag = 0;
    param->vui.bEnableVideoSignalTypePresentFlag = 0;
    param->vui.videoFormat = 5;
    param->vui.bEnableVideoFullRangeFlag = 0;
    param->vui.bEnableColorDescriptionPresentFlag = 0;
    param->vui.colorPrimaries = 2;
    param->vui.transferCharacteristics = 2;
    param->vui.matrixCoeffs = 2;
    param->vui.bEnableChromaLocInfoPresentFlag = 0;
    param->vui.chromaSampleLocTypeTopField = 0;
    param->vui.chromaSampleLocTypeBottomField = 0;
    param->vui.bEnableDefaultDisplayWindowFlag = 0;
    param->vui.defDispWinLeftOffset = 0;
    param->vui.defDispWinRightOffset = 0;
    param->vui.defDispWinTopOffset = 0;
    param->vui.defDispWinBottomOffset = 0;
    param->maxCLL = 0;
    param->maxFALL = 0;
    param->minLuma = 0;
    param->maxLuma = PIXEL_MAX;
    param->log2MaxPocLsb = 8;
    param->maxSlices = 1;
    param->videoSignalTypePreset[0] = 0;

    /*Conformance window*/
    param->confWinRightOffset = 0;
    param->confWinBottomOffset = 0;

    param->bEmitVUITimingInfo   = 1;
    param->bEmitVUIHRDInfo      = 1;
    param->bOptQpPPS            = 0;
    param->bOptRefListLengthPPS = 0;
    param->bOptCUDeltaQP        = 0;
    param->bAQMotion = 0;
    param->bHDR10Opt = 0;
    param->analysisSaveReuseLevel = 0;
    param->analysisLoadReuseLevel = 0;
    param->toneMapFile[0] = 0;
    param->bDhdr10opt = 0;
    param->dolbyProfile = 0;
    param->bCTUInfo = 0;
    param->bUseRcStats = 0;
    param->scaleFactor = 0;
    param->intraRefine = 0;
    param->interRefine = 0;
    param->bDynamicRefine = 0;
    param->mvRefine = 1;
    param->ctuDistortionRefine = 0;
    param->bUseAnalysisFile = 1;
    param->csvfpt = nullptr;
    param->bStylish = 0;
    param->forceFlush = 0;
    param->bDisableLookahead = 0;
    param->bCopyPicToFrame = 1;
    param->maxAUSizeFactor = 1;
    param->naluFile[0] = 0;

    /* DCT Approximations */
    param->bLowPassDct = 0;
    param->bAnalysisType = 0;
    param->bSingleSeiNal = 0;

    /* SEI messages */
    param->preferredTransferCharacteristics = -1;
    param->pictureStructure = -1;
    param->bEmitCLL = 1;

    param->bEnableFrameDuplication = 0;
    param->dupThreshold = 70;

    /* SVT Hevc Encoder specific params */
    param->bEnableSvtHevc = 0;
#ifdef SVT_HEVC
    param->svtHevcParam = svtParam;
    if (svtParam)
        svt_param_default(param);
#endif

    /* MCSTF */
    param->bEnableTemporalFilter = 0;
    param->temporalFilterStrength = 0.95;
    param->searchRangeForLayer0 = 3;
    param->searchRangeForLayer1 = 3;
    param->searchRangeForLayer2 = 3;

    /* Threaded ME */
    param->tmeTaskBlockSize = 1;
    param->tmeNumBufferRows = 10;

    /*Alpha Channel Encoding*/
    param->bEnableAlpha = 0;
    param->numScalableLayers = 1;

    /* Film grain characteristics model filename */
    param->filmGrain = nullptr;
    param->aomFilmGrain = nullptr;
    param->bEnableSBRC = 0;

    /* Multi-View Encoding*/
    param->numViews = 1;
    param->format = 0;

    param->numLayers = 1;

    /* SCC */
    param->bEnableSCC = 0;

    param->bConfigRCFrame = 0;
}

int x265_param_default_preset(x265_param* param, const char* preset, const char* tune)
{
    if (!param)
    {
        x265_log(nullptr, X265_LOG_ERROR, "x265_param_default_preset requires a non-null parameter struct\n");
        return -1;
    }

#if EXPORT_C_API
    ::x265_param_default(param);
#else
    X265_NS::x265_param_default(param);
#endif

    if (preset)
    {
        preset = parsePresetIndexName(preset);

        if (!strcmp(preset, "ultrafast"))
        {
            param->mcstfFrameRange = 1;
            param->maxNumMergeCand = 2;
            param->bIntraInBFrames = 0;
            param->lookaheadDepth = 5;
            param->scenecutThreshold = 0; // disable lookahead
            param->maxCUSize = 32;
            param->minCUSize = 16;
            param->bframes = 3;
            param->bFrameAdaptive = 0;
            param->subpelRefine = 0;
            param->searchMethod = X265_DIA_SEARCH;
            param->bEnableSAO = 0;
            param->bEnableSignHiding = 0;
            param->bEnableWeightedPred = 0;
            param->rdLevel = 2;
            param->maxNumReferences = 1;
            param->limitReferences = 0;
            param->rc.aqStrength = 0.0;
            param->rc.aqMode = X265_AQ_NONE;
            param->rc.hevcAq = 0;
            param->rc.qgSize = 32;
            param->bEnableFastIntra = 1;
        }
        else if (!strcmp(preset, "superfast"))
        {
            param->mcstfFrameRange = 1;
            param->maxNumMergeCand = 2;
            param->bIntraInBFrames = 0;
            param->lookaheadDepth = 10;
            param->maxCUSize = 32;
            param->bframes = 3;
            param->bFrameAdaptive = 0;
            param->subpelRefine = 1;
            param->bEnableWeightedPred = 0;
            param->rdLevel = 2;
            param->maxNumReferences = 1;
            param->limitReferences = 0;
            param->rc.aqStrength = 0.0;
            param->rc.aqMode = X265_AQ_NONE;
            param->rc.hevcAq = 0;
            param->rc.qgSize = 32;
            param->bEnableSAO = 0;
            param->bEnableFastIntra = 1;
        }
        else if (!strcmp(preset, "veryfast"))
        {
            param->mcstfFrameRange = 1;
            param->maxNumMergeCand = 2;
            param->limitReferences = 3;
            param->bIntraInBFrames = 0;
            param->lookaheadDepth = 15;
            param->bFrameAdaptive = 0;
            param->subpelRefine = 1;
            param->rdLevel = 2;
            param->maxNumReferences = 2;
            param->rc.qgSize = 32;
            param->bEnableFastIntra = 1;
        }
        else if (!strcmp(preset, "faster"))
        {
            param->mcstfFrameRange = 1;
            param->maxNumMergeCand = 2;
            param->limitReferences = 3;
            param->bIntraInBFrames = 0;
            param->lookaheadDepth = 15;
            param->bFrameAdaptive = 0;
            param->rdLevel = 2;
            param->maxNumReferences = 2;
            param->bEnableFastIntra = 1;
        }
        else if (!strcmp(preset, "fast"))
        {
            param->mcstfFrameRange = 1;
            param->maxNumMergeCand = 2;
            param->limitReferences = 3;
            param->bEnableEarlySkip = 0;
            param->bIntraInBFrames = 0;
            param->lookaheadDepth = 15;
            param->bFrameAdaptive = 0;
            param->rdLevel = 2;
            param->maxNumReferences = 3;
            param->bEnableFastIntra = 1;
        }
        else if (!strcmp(preset, "medium"))
        {
            param->mcstfFrameRange = 1;
            /* defaults */
        }
        else if (!strcmp(preset, "slow"))
        {
            param->limitReferences = 3;
            param->bEnableEarlySkip = 0;
            param->bIntraInBFrames = 0;
            param->bEnableRectInter = 1;
            param->lookaheadDepth = 25;
            param->rdLevel = 4;
            param->rdoqLevel = 2;
            param->psyRdoq = 1.0;
            param->subpelRefine = 3;
            param->searchMethod = X265_STAR_SEARCH;
            param->maxNumReferences = 4;
            param->limitModes = 1;
            param->lookaheadSlices = 4; // limit parallelism as already enough work exists
        }
        else if (!strcmp(preset, "slower"))
        {
            param->bEnableEarlySkip = 0;
            param->bEnableWeightedBiPred = 1;
            param->bEnableAMP = 1;
            param->bEnableRectInter = 1;
            param->lookaheadDepth = 40;
            param->bframes = 8;
            param->tuQTMaxInterDepth = 3;
            param->tuQTMaxIntraDepth = 3;
            param->rdLevel = 6;
            param->rdoqLevel = 2;
            param->psyRdoq = 1.0;
            param->subpelRefine = 4;
            param->maxNumMergeCand = 4;
            param->searchMethod = X265_STAR_SEARCH;
            param->maxNumReferences = 5;
            param->limitModes = 1;
            param->lookaheadSlices = 0; // disabled for best quality
            param->limitTU = 4;
        }
        else if (!strcmp(preset, "veryslow"))
        {
            param->bEnableEarlySkip = 0;
            param->bEnableWeightedBiPred = 1;
            param->bEnableAMP = 1;
            param->bEnableRectInter = 1;
            param->lookaheadDepth = 40;
            param->bframes = 8;
            param->tuQTMaxInterDepth = 3;
            param->tuQTMaxIntraDepth = 3;
            param->rdLevel = 6;
            param->rdoqLevel = 2;
            param->psyRdoq = 1.0;
            param->subpelRefine = 4;
            param->maxNumMergeCand = 5;
            param->searchMethod = X265_STAR_SEARCH;
            param->maxNumReferences = 5;
            param->limitReferences = 0;
            param->limitModes = 0;
            param->lookaheadSlices = 0; // disabled for best quality
            param->limitTU = 0;
        }
        else if (!strcmp(preset, "placebo"))
        {
            param->bEnableEarlySkip = 0;
            param->bEnableWeightedBiPred = 1;
            param->bEnableAMP = 1;
            param->bEnableRectInter = 1;
            param->lookaheadDepth = 60;
            param->searchRange = 92;
            param->bframes = 8;
            param->tuQTMaxInterDepth = 4;
            param->tuQTMaxIntraDepth = 4;
            param->rdLevel = 6;
            param->rdoqLevel = 2;
            param->psyRdoq = 1.0;
            param->subpelRefine = 5;
            param->maxNumMergeCand = 5;
            param->searchMethod = X265_STAR_SEARCH;
            param->bEnableTransformSkip = 1;
            param->recursionSkipMode = 0;
            param->maxNumReferences = 5;
            param->limitReferences = 0;
            param->lookaheadSlices = 0; // disabled for best quality
            // TODO: optimized esa
        }
        else
            return -1;
    }
    if (tune)
    {
        param->tune = tune;
        if (!strcmp(tune, "psnr"))
        {
            param->rc.aqStrength = 0.0;
            param->psyRd = 0.0;
            param->psyRdoq = 0.0;
        }
        else if (!strcmp(tune, "ssim"))
        {
            param->rc.aqMode = X265_AQ_AUTO_VARIANCE;
            param->psyRd = 0.0;
            param->psyRdoq = 0.0;
        }
        else if (!strcmp(tune, "fastdecode") ||
                 !strcmp(tune, "fast-decode"))
        {
            param->bEnableLoopFilter = 0;
            param->bEnableSAO = 0;
            param->bEnableWeightedPred = 0;
            param->bEnableWeightedBiPred = 0;
            param->bIntraInBFrames = 0;
        }
        else if (!strcmp(tune, "zerolatency") ||
                 !strcmp(tune, "zero-latency"))
        {
            param->bFrameAdaptive = 0;
            param->bframes = 0;
            param->lookaheadDepth = 0;
            param->scenecutThreshold = 0;
            param->bHistBasedSceneCut = 0;
            param->rc.cuTree = 0;
            param->frameNumThreads = 1;
        }
        else if (!strcmp(tune, "grain"))
        {
            param->rc.ipFactor = 1.1;
            param->rc.pbFactor = 1.0;
            param->rc.cuTree = 0;
            param->rc.aqMode = 0;
            param->rc.hevcAq = 0;
            param->rc.qpStep = 1;
            param->rc.bEnableGrain = 1;
            param->recursionSkipMode = 0;
            param->psyRd = 4.0;
            param->psyRdoq = 10.0;
            param->bEnableSAO = 0;
            param->rc.bEnableConstVbv = 1;
        }
        else if (!strcmp(tune, "animation"))
        {
            if (param->bframes + 1 < param->lookaheadDepth) param->bframes++;
            if (param->bframes + 1 < param->lookaheadDepth) param->bframes++;
            param->psyRd = 0.4;
            param->rc.aqStrength = 0.4;
            param->deblockingFilterBetaOffset = 1;
            param->deblockingFilterTCOffset = 1;
        }
        else if (!strncmp(tune, "littlepox", 9) || !strncmp(tune, "lp", 2) ||
                 !strncmp(tune, "vcb-s", 5) || !strncmp(tune, "vcbs", 4))
        {
            param->searchRange = 25;
            param->bEnableAMP = 0;
            param->bEnableRectInter = 0;
            param->rc.aqStrength = 0.8;
            if (param->rdLevel < 4) param->rdLevel = 4;
            param->rdoqLevel = 2;
            param->bEnableSAO = 0;
            param->bEnableStrongIntraSmoothing = 0;
            if (param->bframes + 1 < param->lookaheadDepth) param->bframes++;
            if (param->bframes + 1 < param->lookaheadDepth) param->bframes++;
            if (param->tuQTMaxInterDepth > 3) param->tuQTMaxInterDepth--;
            if (param->tuQTMaxIntraDepth > 3) param->tuQTMaxIntraDepth--;
            if (param->maxNumMergeCand > 3) param->maxNumMergeCand--;
            if (param->subpelRefine < 3) param->subpelRefine = 3;
            param->keyframeMin = 1;
            param->keyframeMax = 360;
            param->bOpenGOP = 0;
            param->deblockingFilterBetaOffset = -1;
            param->deblockingFilterTCOffset = -1;
            param->maxCUSize = 32;
            param->maxTUSize = 32;
            param->rc.qgSize = 8;
            param->cbQpOffset = -2;
            param->crQpOffset = -2;
            param->rc.pbFactor = 1.2;
            param->bEnableWeightedBiPred = 1;
            if (tune[0] == 'l')
            {
                param->rc.rfConstant = 20;
                param->psyRd = 1.5;
                param->psyRdoq = 0.8;

                if (strstr(tune, "++"))
                {
                    if (param->maxNumReferences < 2) param->maxNumReferences = 2;
                    if (param->subpelRefine < 3) param->subpelRefine = 3;
                    if (param->lookaheadDepth < 60) param->lookaheadDepth = 60;
                    param->searchRange = 38;
                }
            }
            else
            {
                param->rc.rfConstant = 18;
                param->psyRd = 1.8;
                param->psyRdoq = 1.0;

                if (strstr(tune, "++"))
                {
                    if (param->maxNumReferences < 3) param->maxNumReferences = 3;
                    if (param->subpelRefine < 3) param->subpelRefine = 3;
                    param->bIntraInBFrames = 1;
                    param->bEnableRectInter = 1;
                    param->limitTU = 4;
                    if (param->lookaheadDepth < 60) param->lookaheadDepth = 60;
                    param->searchRange = 38;
                }
            }
        }
        else if (!strcmp(tune, "vmaf"))  /*Adding vmaf for x265 + SVT-HEVC integration support*/
        {
            /*vmaf is under development, currently x265 won't support vmaf*/
        }
        else
            return -1;
    }

#ifdef SVT_HEVC
    if (preset && svt_set_preset(param, preset))
        return -1;
#endif

    return 0;
}

static int x265_atobool(const char* str, bool& bError)
{
    if (!strcmp(str, "1") ||
        !strcmp(str, "true") ||
        !strcmp(str, "yes"))
        return 1;
    if (!strcmp(str, "0") ||
        !strcmp(str, "false") ||
        !strcmp(str, "no"))
        return 0;
    bError = true;
    return 0;
}

static const char* invertBooleanAliasValue(const char* value, bool& bError)
{
    if (!value)
        return "false";

    bool bLocalError = false;
    int boolValue = x265_atobool(value, bLocalError);
    if (bLocalError)
    {
        bError = true;
        return value;
    }

    return boolValue ? "false" : "true";
}

static int parseOptionIntToken(const char* token, size_t length, bool& bError);

static int parseName(const char* arg, const char* const* names, bool& bError)
{
    for (int i = 0; names[i]; i++)
        if (!strcmp(arg, names[i]))
            return i;

    if (!arg)
    {
        bError = true;
        return 0;
    }

    return parseOptionIntToken(arg, std::strlen(arg), bError);
}

static int splitCommaOption(const char* value, const char* parts[], size_t lengths[], int maxParts)
{
    if (!value || !parts || !lengths || maxParts <= 0)
        return -1;

    int count = 0;
    const char* token = value;
    while (token)
    {
        if (count >= maxParts)
            return -1;

        const char* comma = std::strchr(token, ',');
        size_t length = comma ? (size_t)(comma - token) : std::strlen(token);
        if (!length)
            return -1;

        parts[count] = token;
        lengths[count] = length;
        count++;

        token = comma ? comma + 1 : nullptr;
    }

    return count;
}

static const char* findTokenChar(const char* token, size_t length, char target)
{
    if (!token)
        return nullptr;

    for (size_t i = 0; i < length; i++)
    {
        if (token[i] == target)
            return token + i;
    }

    return nullptr;
}

static int parseHmeSearchMethodToken(const char* token, size_t length, bool& bError)
{
    if (!token || !length || length >= 5)
    {
        bError = true;
        return 0;
    }

    char name[5];
    std::memcpy(name, token, length);
    name[length] = '\0';
    return parseName(name, x265_motion_est_names, bError);
}

static int parseOptionIntToken(const char* token, size_t length, bool& bError)
{
    if (!token || !length)
    {
        bError = true;
        return 0;
    }

    if (length >= 16)
    {
        bError = true;
        return 0;
    }

    const char* begin = token;
    const char* end = token + length;
    while (begin != end && std::isspace(static_cast<unsigned char>(*begin)))
        begin++;
    if (begin == end)
    {
        bError = true;
        return 0;
    }

    bool negative = false;
    if (*begin == '+' || *begin == '-')
    {
        negative = (*begin == '-');
        begin++;
        if (begin == end)
        {
            bError = true;
            return 0;
        }
    }

    int base = 10;
    const char* digitsBegin = begin;
    if (*digitsBegin == '0' && digitsBegin + 1 < end)
    {
        if (digitsBegin[1] == 'x' || digitsBegin[1] == 'X')
        {
            base = 16;
            digitsBegin += 2;
            if (digitsBegin == end)
            {
                bError = true;
                return 0;
            }
        }
        else
            base = 8;
    }

    unsigned long long magnitude = 0;
    std::from_chars_result parsed = std::from_chars(digitsBegin, end, magnitude, base);
    if (parsed.ec != std::errc() || parsed.ptr != end)
    {
        bError = true;
        return 0;
    }

    if (negative)
    {
        if (magnitude > (unsigned long long)INT_MAX + 1ULL)
        {
            bError = true;
            return 0;
        }

        return magnitude == (unsigned long long)INT_MAX + 1ULL ? INT_MIN : -(int)magnitude;
    }

    if (magnitude > INT_MAX)
    {
        bError = true;
        return 0;
    }

    return (int)magnitude;
}

static const char* parsePresetIndexName(const char* preset)
{
    if (!preset)
        return nullptr;

    bool bPresetIndexError = false;
    int index = parseOptionIntToken(preset, std::strlen(preset), bPresetIndexError);
    if (!bPresetIndexError && index >= 0 && index < (int)(sizeof(x265_preset_names) / sizeof(*x265_preset_names) - 1))
        return x265_preset_names[index];

    return preset;
}

static bool parseOptionNonNegativeIntToken(const char* token, size_t length, int maxValue, int& value)
{
    bool bLocalError = false;
    int parsedValue = parseOptionIntToken(token, length, bLocalError);
    if (bLocalError || parsedValue < 0 || parsedValue > maxValue)
        return false;

    value = parsedValue;
    return true;
}

static uint16_t parseOptionUint16Token(const char* token, size_t length, bool& bError)
{
    int value = 0;
    if (!parseOptionNonNegativeIntToken(token, length, UINT16_MAX, value))
    {
        bError = true;
        return 0;
    }

    return (uint16_t)value;
}

static bool splitOptionPair(const char* value, char separatorChar,
                            const char*& firstToken, size_t& firstLength,
                            const char*& secondToken, size_t& secondLength)
{
    if (!value)
        return false;

    const char* separator = std::strchr(value, separatorChar);
    if (!separator)
        return false;

    firstToken = value;
    firstLength = (size_t)(separator - value);
    secondToken = separator + 1;
    secondLength = std::strlen(secondToken);
    return firstLength && secondLength;
}

static uint32_t parseOptionUint32Token(const char* token, size_t length, bool& bError)
{
    int value = 0;
    if (!parseOptionNonNegativeIntToken(token, length, INT_MAX, value))
    {
        bError = true;
        return 0;
    }

    return (uint32_t)value;
}

static int parseOptionIntValue(const char* value, bool& bError)
{
    if (!value)
    {
        bError = true;
        return 0;
    }

    return parseOptionIntToken(value, std::strlen(value), bError);
}

#ifdef SVT_HEVC
static uint8_t parseOptionUint8Token(const char* token, size_t length, bool& bError)
{
    int value = 0;
    if (!parseOptionNonNegativeIntToken(token, length, UINT8_MAX, value))
    {
        bError = true;
        return 0;
    }

    return (uint8_t)value;
}

static uint8_t parseOptionUint8Value(const char* value, bool& bError)
{
    if (!value)
    {
        bError = true;
        return 0;
    }

    return parseOptionUint8Token(value, std::strlen(value), bError);
}
#endif

static void assignParsedOptionLevels(const int parsed[3], int count, int target[3])
{
    if (count == 1)
        target[0] = target[1] = target[2] = parsed[0];
    else
        for (int level = 0; level < 3; level++)
            target[level] = parsed[level];
}

static bool parseOptionIntPair(const char* value, char separatorChar, int& first, int& second)
{
    const char* firstToken = nullptr;
    size_t firstLength = 0;
    const char* secondToken = nullptr;
    size_t secondLength = 0;
    if (!splitOptionPair(value, separatorChar, firstToken, firstLength, secondToken, secondLength))
        return false;

    bool bLocalError = false;
    int parsedFirst = parseOptionIntToken(firstToken, firstLength, bLocalError);
    int parsedSecond = parseOptionIntToken(secondToken, secondLength, bLocalError);
    if (bLocalError)
        return false;

    first = parsedFirst;
    second = parsedSecond;
    return true;
}

static bool parseOptionUintPair(const char* value, char separatorChar, uint32_t& first, uint32_t& second)
{
    int parsedFirst = 0;
    int parsedSecond = 0;
    if (!parseOptionIntPair(value, separatorChar, parsedFirst, parsedSecond) || parsedFirst < 0 || parsedSecond < 0)
        return false;

    first = (uint32_t)parsedFirst;
    second = (uint32_t)parsedSecond;
    return true;
}

static bool parseOptionUint16Pair(const char* value, char separatorChar, uint16_t& first, uint16_t& second)
{
    const char* firstToken = nullptr;
    size_t firstLength = 0;
    const char* secondToken = nullptr;
    size_t secondLength = 0;
    if (!splitOptionPair(value, separatorChar, firstToken, firstLength, secondToken, secondLength))
        return false;

    bool bLocalError = false;
    uint16_t parsedFirst = parseOptionUint16Token(firstToken, firstLength, bLocalError);
    uint16_t parsedSecond = parseOptionUint16Token(secondToken, secondLength, bLocalError);
    if (bLocalError)
        return false;

    first = parsedFirst;
    second = parsedSecond;
    return true;
}

static bool parseOptionIntQuad(const char* value, int& first, int& second, int& third, int& fourth)
{
    const char* parts[4];
    size_t lengths[4];
    if (splitCommaOption(value, parts, lengths, 4) != 4)
        return false;

    bool bLocalError = false;
    int parsedFirst = parseOptionIntToken(parts[0], lengths[0], bLocalError);
    int parsedSecond = parseOptionIntToken(parts[1], lengths[1], bLocalError);
    int parsedThird = parseOptionIntToken(parts[2], lengths[2], bLocalError);
    int parsedFourth = parseOptionIntToken(parts[3], lengths[3], bLocalError);
    if (bLocalError)
        return false;

    first = parsedFirst;
    second = parsedSecond;
    third = parsedThird;
    fourth = parsedFourth;
    return true;
}

static bool parseOptionDoubleToken(const char* token, size_t length, double& value)
{
    if (!token || !length)
        return false;

    if (length >= 32)
        return false;

    double doubleValue = 0.0;
    std::from_chars_result parsed = std::from_chars(token, token + length, doubleValue);
    if (parsed.ec == std::errc() && parsed.ptr == token + length && std::isfinite(doubleValue))
    {
        value = doubleValue;
        return true;
    }

    return false;
}

static bool parseZoneOptionEntry(char* entry, char* entryEnd, x265_zone& zone)
{
    if (!entry || !entryEnd || entry >= entryEnd)
        return false;

    const char* parts[3];
    size_t lengths[3];
    char savedEnd = *entryEnd;
    *entryEnd = '\0';

    bool parsed = false;
    do
    {
        if (splitCommaOption(entry, parts, lengths, 3) != 3)
            break;

        bool bLocalError = false;
        int startFrame = parseOptionIntToken(parts[0], lengths[0], bLocalError);
        int endFrame = parseOptionIntToken(parts[1], lengths[1], bLocalError);
        if (bLocalError || startFrame < 0 || endFrame <= startFrame)
            break;

        const char* equals = findTokenChar(parts[2], lengths[2], '=');
        if (!equals || equals == parts[2] || equals + 1 >= parts[2] + lengths[2] || (size_t)(equals - parts[2]) != 1)
            break;

        size_t modeValueLength = (size_t)((parts[2] + lengths[2]) - (equals + 1));
        if (parts[2][0] == 'q')
        {
            int qp = parseOptionIntToken(equals + 1, modeValueLength, bLocalError);
            if (bLocalError || qp < -6 * (X265_DEPTH - 8) || qp > QP_MAX_MAX)
                break;

            zone.qp = qp;
            zone.bForceQp = 1;
        }
        else if (parts[2][0] == 'b')
        {
            double bitrateFactor = 0.0;
            if (!parseOptionDoubleToken(equals + 1, modeValueLength, bitrateFactor) || bitrateFactor <= 0.0)
                break;

            zone.bitrateFactor = bitrateFactor;
            zone.bForceQp = 0;
        }
        else
            break;

        zone.startFrame = startFrame;
        zone.endFrame = endFrame;
        parsed = true;
    }
    while (false);

    *entryEnd = savedEnd;
    return parsed;
}

static bool parseTenthsOrIntegerLevel(const char* value, int& parsedLevel)
{
    double decimalLevel = 0.0;
    if (!value || !parseOptionDoubleToken(value, std::strlen(value), decimalLevel) || decimalLevel < 0)
        return false;

    if (decimalLevel < 10)
    {
        if (decimalLevel > INT_MAX / 10.0)
            return false;

        double scaledLevel = 10 * decimalLevel;
        int roundedLevel = (int)(scaledLevel + .5);
        if (std::fabs(scaledLevel - roundedLevel) > 1e-6)
            return false;

        parsedLevel = roundedLevel;
        return true;
    }

    bool bLocalError = false;
    int integerLevel = parseOptionIntValue(value, bLocalError);
    if (bLocalError || integerLevel >= 100)
        return false;

    parsedLevel = integerLevel;
    return true;
}

#ifdef SVT_HEVC
static bool parseTenthsOrIntegerLevel(const char* value, uint32_t& parsedLevel)
{
    int signedLevel = 0;
    if (!parseTenthsOrIntegerLevel(value, signedLevel) || signedLevel < 0)
        return false;

    parsedLevel = (uint32_t)signedLevel;
    return true;
}
#endif

static bool parseFpsValue(const char* value, uint32_t& numerator, uint32_t& denominator)
{
    uint32_t parsedNumerator = 0;
    uint32_t parsedDenominator = 0;
    if (parseOptionUintPair(value, '/', parsedNumerator, parsedDenominator) && parsedNumerator > 0 && parsedDenominator > 0)
    {
        numerator = parsedNumerator;
        denominator = parsedDenominator;
        return true;
    }

    double fps = 0.0;
    if (!value || !parseOptionDoubleToken(value, std::strlen(value), fps) || fps <= 0 || fps > INT_MAX)
        return false;

    if (fps <= INT_MAX / 1000.0)
    {
        numerator = (uint32_t)(fps * 1000 + .5);
        denominator = 1000;
        return true;
    }

    bool bLocalError = false;
    int integerFps = parseOptionIntValue(value, bLocalError);
    if (bLocalError || integerFps <= 0)
        return false;

    numerator = (uint32_t)integerFps;
    denominator = 1;
    return true;
}

#ifdef SVT_HEVC
static bool parseFpsValue(const char* value, int32_t& numerator, int32_t& denominator)
{
    uint32_t parsedNumerator = 0;
    uint32_t parsedDenominator = 0;
    if (!parseFpsValue(value, parsedNumerator, parsedDenominator) ||
        parsedNumerator > INT32_MAX || parsedDenominator > INT32_MAX)
        return false;

    numerator = (int32_t)parsedNumerator;
    denominator = (int32_t)parsedDenominator;
    return true;
}
#endif

static bool parseIndexedNameOrNumber(const char* value, const char* const* names, int indexOffset, int& parsedValue)
{
    int maxIndexedValue = indexOffset;
    for (const char* const* name = names; name && *name; name++, maxIndexedValue++) {}

    bool bLocalError = false;
    int indexedValue = parseOptionIntValue(value, bLocalError);
    if (!bLocalError && indexedValue >= indexOffset && indexedValue <= maxIndexedValue)
    {
        parsedValue = indexedValue;
        return true;
    }

    bLocalError = false;
    int namedValue = parseName(value, names, bLocalError);
    if (bLocalError)
        return false;

    parsedValue = namedValue + indexOffset;
    return true;
}

static bool parseBoolOrIntValue(const char* value, int& parsedValue)
{
    bool bLocalError = false;
    int boolValue = x265_atobool(value, bLocalError);
    if (!bLocalError)
    {
        parsedValue = boolValue;
        return true;
    }

    bLocalError = false;
    int intValue = parseOptionIntValue(value, bLocalError);
    if (!bLocalError)
        parsedValue = intValue;
    return !bLocalError;
}

static bool parseBoolOrNamedValue(const char* value, const char* const* names, int& parsedValue)
{
    bool bLocalError = false;
    int boolValue = x265_atobool(value, bLocalError);
    if (!bLocalError)
    {
        parsedValue = boolValue;
        return true;
    }

    bLocalError = false;
    int namedValue = parseName(value, names, bLocalError);
    if (!bLocalError)
        parsedValue = namedValue;
    return !bLocalError;
}

static bool parseBoolOrNumericInt(const char* value, int falseValue, int& parsedValue)
{
    bool bLocalError = false;
    int boolValue = x265_atobool(value, bLocalError);
    if (!bLocalError && !boolValue)
    {
        parsedValue = falseValue;
        return true;
    }

    bLocalError = false;
    int intValue = parseOptionIntValue(value, bLocalError);
    if (!bLocalError)
        parsedValue = intValue;
    return !bLocalError;
}

static bool parseBoolOrNumericDouble(const char* value, double falseValue, double& parsedValue)
{
    bool bLocalError = false;
    int boolValue = x265_atobool(value, bLocalError);
    if (!bLocalError && !boolValue)
    {
        parsedValue = falseValue;
        return true;
    }

    bLocalError = false;
    double doubleValue = x265_atof(value, bLocalError);
    if (!bLocalError && std::isfinite(doubleValue))
    {
        parsedValue = doubleValue;
        return true;
    }

    return false;
}

static bool parseMaskingStrengthTriples(const char* value, int expectedTriples, int window[], double refQpDelta[], double nonRefQpDelta[])
{
    const char* parts[36];
    size_t lengths[36];
    int parsedWindow[12];
    double parsedRefQpDelta[12];
    double parsedNonRefQpDelta[12];
    const int expectedValues = expectedTriples * 3;
    if (expectedTriples <= 0 || expectedTriples > 12)
        return false;
    if (splitCommaOption(value, parts, lengths, expectedValues) != expectedValues)
        return false;

    for (int i = 0; i < expectedTriples; i++)
    {
        bool bWindowError = false;
        parsedWindow[i] = parseOptionIntToken(parts[i * 3], lengths[i * 3], bWindowError);
        if (bWindowError ||
            !parseOptionDoubleToken(parts[i * 3 + 1], lengths[i * 3 + 1], parsedRefQpDelta[i]) ||
            !parseOptionDoubleToken(parts[i * 3 + 2], lengths[i * 3 + 2], parsedNonRefQpDelta[i]))
            return false;
    }

    for (int i = 0; i < expectedTriples; i++)
    {
        window[i] = parsedWindow[i];
        refQpDelta[i] = parsedRefQpDelta[i];
        nonRefQpDelta[i] = parsedNonRefQpDelta[i];
    }

    return true;
}

static void applyCompactMaskingStrength(int parsedWindow, double parsedRefQpDelta, double parsedNonRefQpDelta,
                                        int& maxScenecutWindow, int scenecutWindow[],
                                        double refQpDelta[], double nonRefQpDelta[])
{
    if (parsedWindow > 0)
        maxScenecutWindow = parsedWindow;
    if (parsedRefQpDelta > 0)
        refQpDelta[0] = parsedRefQpDelta;
    if (parsedNonRefQpDelta > 0)
        nonRefQpDelta[0] = parsedNonRefQpDelta;

    scenecutWindow[0] = maxScenecutWindow / 6;
    for (int i = 1; i < 6; i++)
    {
        scenecutWindow[i] = maxScenecutWindow / 6;
        refQpDelta[i] = refQpDelta[i - 1] - (0.15 * refQpDelta[i - 1]);
        nonRefQpDelta[i] = nonRefQpDelta[i - 1] - (0.15 * nonRefQpDelta[i - 1]);
    }
}

static void applyExpandedMaskingStrength(const int parsedWindow[], const double parsedRefQpDelta[],
                                         const double parsedNonRefQpDelta[], int& maxScenecutWindow,
                                         int scenecutWindow[], double refQpDelta[], double nonRefQpDelta[])
{
    maxScenecutWindow = 0;
    for (int i = 0; i < 6; i++)
    {
        scenecutWindow[i] = parsedWindow[i];
        refQpDelta[i] = parsedRefQpDelta[i];
        nonRefQpDelta[i] = parsedNonRefQpDelta[i];
        maxScenecutWindow += scenecutWindow[i];
    }
}
int x265_scenecut_aware_qp_param_parse(x265_param* p, const char* name, const char* value)
{
    bool bError = false;
    char nameBuf[64];
    if (!name)
        return X265_PARAM_BAD_NAME;
    if (!p)
        return X265_PARAM_BAD_VALUE;
    // skip -- prefix if provided
    if (name[0] == '-' && name[1] == '-')
        name += 2;
    // s/_/-/g
    if (std::strlen(name) + 1 < sizeof(nameBuf) && std::strchr(name, '_'))
    {
        char *c;
        std::memcpy(nameBuf, name, std::strlen(name) + 1);
        while ((c = std::strchr(nameBuf, '_')) != 0)
            *c = '-';
        name = nameBuf;
    }
    if (!value)
        value = "true";
    else if (value[0] == '=')
        value++;
#define OPT(STR) else if (!strcmp(name, STR))
    if (0);
    OPT("scenecut-aware-qp")
    {
        bool bSceneCutAwareQpError = false;
        int sceneCutAwareQp = parseOptionIntValue(value, bSceneCutAwareQpError);
        bError |= bSceneCutAwareQpError;
        if (!bSceneCutAwareQpError)
            p->bEnableSceneCutAwareQp = sceneCutAwareQp;
    }
    OPT("bitrate")
    {
        bool bBitrateValueError = false;
        int bitrate = parseOptionIntValue(value, bBitrateValueError);
        bError |= bBitrateValueError;
        if (!bBitrateValueError)
        {
            p->rc.bitrate = bitrate;
            p->rc.rateControlMode = X265_RC_ABR;
        }
    }
    OPT("masking-strength") bError = parseMaskingStrength(p, value);
    else
        return X265_PARAM_BAD_NAME;
#undef OPT
    return bError ? X265_PARAM_BAD_VALUE : 0;
}


int x265_zone_param_parse(x265_param* p, const char* name, const char* value)
{
    bool bError = false;
    char nameBuf[64];

    if (!name)
        return X265_PARAM_BAD_NAME;
    if (!p)
        return X265_PARAM_BAD_VALUE;

    // skip -- prefix if provided
    if (name[0] == '-' && name[1] == '-')
        name += 2;

    // s/_/-/g
    if (strlen(name) + 1 < sizeof(nameBuf) && strchr(name, '_'))
    {
        char *c;
        std::memcpy(nameBuf, name, strlen(name) + 1);
        while ((c = strchr(nameBuf, '_')) != 0)
            *c = '-';

        name = nameBuf;
    }

    if (!strncmp(name, "no-", 3))
    {
        name += 3;
        value = invertBooleanAliasValue(value, bError);
    }
    else if (!strncmp(name, "no", 2))
    {
        name += 2;
        value = invertBooleanAliasValue(value, bError);
    }
    else if (!value)
        value = "true";
    else if (value[0] == '=')
        value++;

    if (bError)
        return X265_PARAM_BAD_VALUE;

#define OPT(STR) else if (!strcmp(name, STR))
#define OPT2(STR1, STR2) else if (!strcmp(name, STR1) || !strcmp(name, STR2))

    if (0);
    OPT("ref")
    {
        bool bMaxNumReferencesError = false;
        int maxNumReferences = parseOptionIntValue(value, bMaxNumReferencesError);
        bError |= bMaxNumReferencesError;
        if (!bMaxNumReferencesError)
            p->maxNumReferences = maxNumReferences;
    }
    OPT("fast-intra") p->bEnableFastIntra = x265_atobool(value, bError);
    OPT("early-skip") p->bEnableEarlySkip = x265_atobool(value, bError);
    OPT("rskip")
    {
        bool bRecursionSkipModeError = false;
        int recursionSkipMode = parseOptionIntValue(value, bRecursionSkipModeError);
        bError |= bRecursionSkipModeError;
        if (!bRecursionSkipModeError)
            p->recursionSkipMode = recursionSkipMode;
    }
    OPT("rskip-edge-threshold")
    {
        bool bEdgeVarThresholdError = false;
        int edgeVarThreshold = parseOptionIntValue(value, bEdgeVarThresholdError);
        bError |= bEdgeVarThresholdError;
        if (!bEdgeVarThresholdError)
            p->edgeVarThreshold = edgeVarThreshold / 100.0f;
    }
    OPT("me")
    {
        bool bSearchMethodError = false;
        int searchMethod = parseName(value, x265_motion_est_names, bSearchMethodError);
        bError |= bSearchMethodError;
        if (!bSearchMethodError)
            p->searchMethod = searchMethod;
    }
    OPT("subme")
    {
        bool bSubpelRefineError = false;
        int subpelRefine = parseOptionIntValue(value, bSubpelRefineError);
        bError |= bSubpelRefineError;
        if (!bSubpelRefineError)
            p->subpelRefine = subpelRefine;
    }
    OPT("merange")
    {
        bool bSearchRangeError = false;
        int searchRange = parseOptionIntValue(value, bSearchRangeError);
        bError |= bSearchRangeError;
        if (!bSearchRangeError)
            p->searchRange = searchRange;
    }
    OPT("rect") p->bEnableRectInter = x265_atobool(value, bError);
    OPT("amp") p->bEnableAMP = x265_atobool(value, bError);
    OPT("max-merge")
    {
        bool bMaxNumMergeCandError = false;
        uint32_t maxNumMergeCand = parseOptionUint32Token(value, std::strlen(value), bMaxNumMergeCandError);
        bError |= bMaxNumMergeCandError;
        if (!bMaxNumMergeCandError)
            p->maxNumMergeCand = maxNumMergeCand;
    }
    OPT("rd")
    {
        bool bRdLevelError = false;
        int rdLevel = parseOptionIntValue(value, bRdLevelError);
        bError |= bRdLevelError;
        if (!bRdLevelError)
            p->rdLevel = rdLevel;
    }
    OPT("radl")
    {
        bool bRadlError = false;
        int radl = parseOptionIntValue(value, bRadlError);
        bError |= bRadlError;
        if (!bRadlError)
            p->radl = radl;
    }
    OPT2("rdoq", "rdoq-level")
    {
        bool bRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));
        bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)
               || bRdoqTextualTrue
               || p->rdoqLevel < 0 || p->rdoqLevel > 2;
    }
    OPT("b-intra") p->bIntraInBFrames = x265_atobool(value, bError);
    OPT("scaling-list") snprintf(p->scalingLists, X265_MAX_STRING_SIZE, "%s", value);
    OPT("crf")
    {
        if (!parseOptionDoubleToken(value, std::strlen(value), p->rc.rfConstant))
            bError = true;
        else
            p->rc.rateControlMode = X265_RC_CRF;
    }
    OPT("qp")
    {
        bool bQpValueError = false;
        int qp = parseOptionIntValue(value, bQpValueError);
        bError |= bQpValueError;
        if (!bQpValueError)
        {
            p->rc.qp = qp;
            p->rc.rateControlMode = X265_RC_CQP;
        }
    }
    OPT("bitrate")
    {
        bool bBitrateValueError = false;
        int bitrate = parseOptionIntValue(value, bBitrateValueError);
        bError |= bBitrateValueError;
        if (!bBitrateValueError)
        {
            p->rc.bitrate = bitrate;
            p->rc.rateControlMode = X265_RC_ABR;
        }
    }
    OPT("aq-mode")
    {
        bool bAqModeError = false;
        int aqMode = parseOptionIntValue(value, bAqModeError);
        bError |= bAqModeError;
        if (!bAqModeError)
            p->rc.aqMode = aqMode;
    }
    OPT("limit-aq1") p->rc.limitAq1 = x265_atobool(value, bError);
    OPT("aq-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.aqStrength);
    OPT("aq-bias-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.aqBiasStrength);
    OPT("limit-aq1-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.limitAq1Strength);
    OPT("nr-intra")
    {
        bool bNoiseReductionIntraError = false;
        int noiseReductionIntra = parseOptionIntValue(value, bNoiseReductionIntraError);
        bError |= bNoiseReductionIntraError;
        if (!bNoiseReductionIntraError)
            p->noiseReductionIntra = noiseReductionIntra;
    }
    OPT("nr-inter")
    {
        bool bNoiseReductionInterError = false;
        int noiseReductionInter = parseOptionIntValue(value, bNoiseReductionInterError);
        bError |= bNoiseReductionInterError;
        if (!bNoiseReductionInterError)
            p->noiseReductionInter = noiseReductionInter;
    }
    OPT("limit-modes") p->limitModes = x265_atobool(value, bError);
    OPT("splitrd-skip") p->bEnableSplitRdSkip = x265_atobool(value, bError);
    OPT("cu-lossless") p->bCULossless = x265_atobool(value, bError);
    OPT("rd-refine") p->bEnableRdRefine = x265_atobool(value, bError);
    OPT("limit-tu")
    {
        bool bLimitTUError = false;
        int limitTU = parseOptionIntValue(value, bLimitTUError);
        bError |= bLimitTUError;
        if (!bLimitTUError)
            p->limitTU = limitTU;
    }
    OPT("tskip") p->bEnableTransformSkip = x265_atobool(value, bError);
    OPT("tskip-fast") p->bEnableTSkipFast = x265_atobool(value, bError);
    OPT("rdpenalty")
    {
        bool bRdPenaltyError = false;
        int rdPenalty = parseOptionIntValue(value, bRdPenaltyError);
        bError |= bRdPenaltyError;
        if (!bRdPenaltyError)
            p->rdPenalty = rdPenalty;
    }
    OPT("dynamic-rd") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->dynamicRd);
    else
        return X265_PARAM_BAD_NAME;

#undef OPT
#undef OPT2

    return bError ? X265_PARAM_BAD_VALUE : 0;
}

#undef atoi
#undef atof

/* internal versions of string-to-int with additional error checking */
#undef atoi
#undef atof
#define atobool(str) (bNameWasBool = true, x265_atobool(str, bError))

int x265_param_parse(x265_param* p, const char* name, const char* value)
{
    bool bError = false;
    bool bNameWasBool = false;
    bool bValueWasNull = !value;
    bool bExtraParams = false;
    char nameBuf[64];
#ifdef SVT_HEVC
    static int svtParseCallCount;
#endif

    if (!name)
        return X265_PARAM_BAD_NAME;
    if (!p)
        return X265_PARAM_BAD_VALUE;

#ifdef SVT_HEVC
    svtParseCallCount++;
#endif
    // skip -- prefix if provided
    if (name[0] == '-' && name[1] == '-')
        name += 2;

    // s/_/-/g
    if (strlen(name) + 1 < sizeof(nameBuf) && strchr(name, '_'))
    {
        char *c;
        std::memcpy(nameBuf, name, strlen(name) + 1);
        while ((c = strchr(nameBuf, '_')) != 0)
            *c = '-';

        name = nameBuf;
    }

    if (!strncmp(name, "no-", 3))
    {
        name += 3;
        value = invertBooleanAliasValue(value, bError);
        bValueWasNull = false;
    }
    else if (!strncmp(name, "no", 2))
    {
        name += 2;
        value = invertBooleanAliasValue(value, bError);
        bValueWasNull = false;
    }
    else if (!value)
        value = "true";
    else if (value[0] == '=')
        value++;

    if (bError)
        return X265_PARAM_BAD_VALUE;

#if defined(_MSC_VER)
#pragma warning(disable: 4127) // conditional expression is constant
#endif
#define OPT(STR) else if (!strcmp(name, STR))
#define OPT2(STR1, STR2) else if (!strcmp(name, STR1) || !strcmp(name, STR2))

#ifdef SVT_HEVC
    if (p->bEnableSvtHevc)
    {
        if(svt_param_parse(p, name, value))
        {
            x265_log(p, X265_LOG_ERROR, "Error while parsing params \n");
            bError = true;
        }
        return bError ? X265_PARAM_BAD_VALUE : 0;
    }
#endif

    if (0) ;
    OPT("asm")
    {
#if X265_ARCH_X86
        if (!strcasecmp(value, "avx512"))
        {
            p->cpuid = X265_NS::cpu_detect(true);
            if (!(p->cpuid & X265_CPU_AVX512))
                x265_log(p, X265_LOG_WARNING, "AVX512 is not supported\n");
        }
        else
        {
            if (bValueWasNull)
                p->cpuid = atobool(value);
            else
            {
                bool bCpuNameError = false;
                int cpuid = parseCpuName(value, bCpuNameError, false);
                bError |= bCpuNameError;
                if (!bCpuNameError)
                    p->cpuid = cpuid;
            }
        }
#else
        if (bValueWasNull)
            p->cpuid = atobool(value);
        else
        {
            bool bCpuNameError = false;
            int cpuid = parseCpuName(value, bCpuNameError, false);
            bError |= bCpuNameError;
            if (!bCpuNameError)
                p->cpuid = cpuid;
        }
#endif
    }
    OPT("fps")
    {
        bError |= !parseFpsValue(value, p->fpsNum, p->fpsDenom);
    }
    OPT("frame-threads")
    {
        bool bFrameNumThreadsError = false;
        int frameNumThreads = parseOptionIntValue(value, bFrameNumThreadsError);
        bError |= bFrameNumThreadsError;
        if (!bFrameNumThreadsError)
            p->frameNumThreads = frameNumThreads;
    }
    OPT("pmode")
    {
        bNameWasBool = true;
        p->bDistributeModeAnalysis = x265_atobool(value, bError);
    }
    OPT("pme")
    {
        bNameWasBool = true;
        p->bDistributeMotionEstimation = x265_atobool(value, bError);
    }
    OPT2("level-idc", "level")
    {
        /* allow "5.1" or "51", both converted to integer 51 */
        /* if level-idc specifies an obviously wrong value in either float or int, 
        throw error consistently. Stronger level checking will be done in encoder_open() */
        if (!parseTenthsOrIntegerLevel(value, p->levelIdc))
            bError = true;
    }
    OPT("high-tier")
    {
        bNameWasBool = true;
        p->bHighTier = x265_atobool(value, bError);
    }
    OPT("allow-non-conformance")
    {
        bNameWasBool = true;
        p->bAllowNonConformance = x265_atobool(value, bError);
    }
    OPT2("log-level", "log")
    {
        bError |= !parseIndexedNameOrNumber(value, logLevelNames, -1, p->logLevel);
    }
    OPT("log-file")
    {
        char* newLogFile = strdup(value);
        if (!newLogFile)
            bError = true;
        else
        {
            free(p->logfn);
            p->logfn = newLogFile;
        }
    }
    OPT("log-file-level")
    {
        bError |= !parseIndexedNameOrNumber(value, logLevelNames, -1, p->logfLevel);
    }
    OPT("total-frames")
    {
        bool bTotalFramesError = false;
        int totalFrames = parseOptionIntValue(value, bTotalFramesError);
        bError |= bTotalFramesError;
        if (!bTotalFramesError)
            p->totalFrames = totalFrames;
    }
    OPT("annexb")
    {
        bNameWasBool = true;
        p->bAnnexB = x265_atobool(value, bError);
    }
    OPT("repeat-headers")
    {
        bNameWasBool = true;
        p->bRepeatHeaders = x265_atobool(value, bError);
    }
    OPT("wpp")
    {
        bNameWasBool = true;
        p->bEnableWavefront = x265_atobool(value, bError);
    }
    OPT("ctu")
    {
        bool bMaxCUSizeError = false;
        uint32_t maxCUSize = parseOptionUint32Token(value, std::strlen(value), bMaxCUSizeError);
        bError |= bMaxCUSizeError;
        if (!bMaxCUSizeError)
            p->maxCUSize = maxCUSize;
    }
    OPT("min-cu-size")
    {
        bool bMinCUSizeError = false;
        uint32_t minCUSize = parseOptionUint32Token(value, std::strlen(value), bMinCUSizeError);
        bError |= bMinCUSizeError;
        if (!bMinCUSizeError)
            p->minCUSize = minCUSize;
    }
    OPT("tu-intra-depth")
    {
        bool bTuQTMaxIntraDepthError = false;
        uint32_t tuQTMaxIntraDepth = parseOptionUint32Token(value, std::strlen(value), bTuQTMaxIntraDepthError);
        bError |= bTuQTMaxIntraDepthError;
        if (!bTuQTMaxIntraDepthError)
            p->tuQTMaxIntraDepth = tuQTMaxIntraDepth;
    }
    OPT("tu-inter-depth")
    {
        bool bTuQTMaxInterDepthError = false;
        uint32_t tuQTMaxInterDepth = parseOptionUint32Token(value, std::strlen(value), bTuQTMaxInterDepthError);
        bError |= bTuQTMaxInterDepthError;
        if (!bTuQTMaxInterDepthError)
            p->tuQTMaxInterDepth = tuQTMaxInterDepth;
    }
    OPT("max-tu-size")
    {
        bool bMaxTUSizeError = false;
        uint32_t maxTUSize = parseOptionUint32Token(value, std::strlen(value), bMaxTUSizeError);
        bError |= bMaxTUSizeError;
        if (!bMaxTUSizeError)
            p->maxTUSize = maxTUSize;
    }
    OPT("subme")
    {
        bool bSubpelRefineError = false;
        int subpelRefine = parseOptionIntValue(value, bSubpelRefineError);
        bError |= bSubpelRefineError;
        if (!bSubpelRefineError)
            p->subpelRefine = subpelRefine;
    }
    OPT("merange")
    {
        bool bSearchRangeError = false;
        int searchRange = parseOptionIntValue(value, bSearchRangeError);
        bError |= bSearchRangeError;
        if (!bSearchRangeError)
            p->searchRange = searchRange;
    }
    OPT("rect")
    {
        bNameWasBool = true;
        p->bEnableRectInter = x265_atobool(value, bError);
    }
    OPT("amp")
    {
        bNameWasBool = true;
        p->bEnableAMP = x265_atobool(value, bError);
    }
    OPT("max-merge")
    {
        bool bMaxNumMergeCandError = false;
        uint32_t maxNumMergeCand = parseOptionUint32Token(value, std::strlen(value), bMaxNumMergeCandError);
        bError |= bMaxNumMergeCandError;
        if (!bMaxNumMergeCandError)
            p->maxNumMergeCand = maxNumMergeCand;
    }
    OPT("temporal-mvp")
    {
        bNameWasBool = true;
        p->bEnableTemporalMvp = x265_atobool(value, bError);
    }
    OPT("early-skip")
    {
        bNameWasBool = true;
        p->bEnableEarlySkip = x265_atobool(value, bError);
    }
    OPT("rskip")
    {
        bool bRecursionSkipModeError = false;
        int recursionSkipMode = parseOptionIntValue(value, bRecursionSkipModeError);
        bError |= bRecursionSkipModeError;
        if (!bRecursionSkipModeError)
            p->recursionSkipMode = recursionSkipMode;
    }
    OPT("rdpenalty")
    {
        bool bRdPenaltyError = false;
        int rdPenalty = parseOptionIntValue(value, bRdPenaltyError);
        bError |= bRdPenaltyError;
        if (!bRdPenaltyError)
            p->rdPenalty = rdPenalty;
    }
    OPT("tskip")
    {
        bNameWasBool = true;
        p->bEnableTransformSkip = x265_atobool(value, bError);
    }
    OPT("no-tskip-fast")
    {
        bNameWasBool = true;
        p->bEnableTSkipFast = x265_atobool(value, bError);
    }
    OPT("tskip-fast")
    {
        bNameWasBool = true;
        p->bEnableTSkipFast = x265_atobool(value, bError);
    }
    OPT("strong-intra-smoothing")
    {
        bNameWasBool = true;
        p->bEnableStrongIntraSmoothing = x265_atobool(value, bError);
    }
    OPT("lossless")
    {
        bNameWasBool = true;
        p->bLossless = x265_atobool(value, bError);
    }
    OPT("cu-lossless")
    {
        bNameWasBool = true;
        p->bCULossless = x265_atobool(value, bError);
    }
    OPT("constrained-intra")
    {
        bNameWasBool = true;
        p->bEnableConstrainedIntra = x265_atobool(value, bError);
    }
    OPT("fast-intra")
    {
        bNameWasBool = true;
        p->bEnableFastIntra = x265_atobool(value, bError);
    }
    OPT("open-gop")
    {
        bNameWasBool = true;
        p->bOpenGOP = x265_atobool(value, bError);
    }
    OPT("intra-refresh")
    {
        bNameWasBool = true;
        p->bIntraRefresh = x265_atobool(value, bError);
    }
    OPT("lookahead-slices")
    {
        bool bLookaheadSlicesError = false;
        int lookaheadSlices = parseOptionIntValue(value, bLookaheadSlicesError);
        bError |= bLookaheadSlicesError;
        if (!bLookaheadSlicesError)
            p->lookaheadSlices = lookaheadSlices;
    }
    OPT("scenecut")
    {
       bool bScenecutTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));
       bError |= !parseBoolOrIntValue(value, p->scenecutThreshold)
              || bScenecutTextualTrue
              || p->scenecutThreshold < 0;
    }
    OPT("temporal-layers")
    {
        bool bEnableTemporalSubLayersError = false;
        int enableTemporalSubLayers = parseOptionIntValue(value, bEnableTemporalSubLayersError);
        bError |= bEnableTemporalSubLayersError;
        if (!bEnableTemporalSubLayersError)
            p->bEnableTemporalSubLayers = enableTemporalSubLayers;
    }
    OPT("keyint")
    {
        bool bKeyframeMaxError = false;
        int keyframeMax = parseOptionIntValue(value, bKeyframeMaxError);
        bError |= bKeyframeMaxError;
        if (!bKeyframeMaxError)
            p->keyframeMax = keyframeMax;
    }
    OPT("min-keyint")
    {
        bool bKeyframeMinError = false;
        int keyframeMin = parseOptionIntValue(value, bKeyframeMinError);
        bError |= bKeyframeMinError;
        if (!bKeyframeMinError)
            p->keyframeMin = keyframeMin;
    }
    OPT("rc-lookahead")
    {
        bool bLookaheadDepthError = false;
        int lookaheadDepth = parseOptionIntValue(value, bLookaheadDepthError);
        bError |= bLookaheadDepthError;
        if (!bLookaheadDepthError)
            p->lookaheadDepth = lookaheadDepth;
    }
    OPT("bframes")
    {
        bool bBframesError = false;
        int bframes = parseOptionIntValue(value, bBframesError);
        bError |= bBframesError;
        if (!bBframesError)
            p->bframes = bframes;
    }
    OPT("bframe-bias")
    {
        bool bBFrameBiasError = false;
        int bFrameBias = parseOptionIntValue(value, bBFrameBiasError);
        bError |= bBFrameBiasError;
        if (!bBFrameBiasError)
            p->bFrameBias = bFrameBias;
    }
    OPT("b-adapt")
    {
        bool bBAdaptTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));
        bError |= !parseBoolOrIntValue(value, p->bFrameAdaptive)
               || bBAdaptTextualTrue
               || p->bFrameAdaptive < 0 || p->bFrameAdaptive > 2;
    }
    OPT("interlace")
    {
        bool bInterlaceBoolError = false;
        int interlaceBoolValue = x265_atobool(value, bInterlaceBoolError);
        bError |= !parseBoolOrNamedValue(value, x265_interlace_names, p->interlaceMode)
               || (!bInterlaceBoolError && interlaceBoolValue)
               || p->interlaceMode < 0 || p->interlaceMode > 2;
    }
    OPT("ref")
    {
        bool bMaxNumReferencesError = false;
        int maxNumReferences = parseOptionIntValue(value, bMaxNumReferencesError);
        bError |= bMaxNumReferencesError;
        if (!bMaxNumReferencesError)
            p->maxNumReferences = maxNumReferences;
    }
    OPT("limit-refs")
    {
        bool bLimitReferencesError = false;
        int limitReferences = parseOptionIntValue(value, bLimitReferencesError);
        bError |= bLimitReferencesError;
        if (!bLimitReferencesError)
            p->limitReferences = limitReferences;
    }
    OPT("limit-modes")
    {
        bNameWasBool = true;
        p->limitModes = x265_atobool(value, bError);
    }
    OPT("weightp")
    {
        bNameWasBool = true;
        p->bEnableWeightedPred = x265_atobool(value, bError);
    }
    OPT("weightb")
    {
        bNameWasBool = true;
        p->bEnableWeightedBiPred = x265_atobool(value, bError);
    }
    OPT("cbqpoffs")
    {
        bool bCbQpOffsetError = false;
        int cbQpOffset = parseOptionIntValue(value, bCbQpOffsetError);
        bError |= bCbQpOffsetError;
        if (!bCbQpOffsetError)
            p->cbQpOffset = cbQpOffset;
    }
    OPT("crqpoffs")
    {
        bool bCrQpOffsetError = false;
        int crQpOffset = parseOptionIntValue(value, bCrQpOffsetError);
        bError |= bCrQpOffsetError;
        if (!bCrQpOffsetError)
            p->crQpOffset = crQpOffset;
    }
    OPT("rd")
    {
        bool bRdLevelError = false;
        int rdLevel = parseOptionIntValue(value, bRdLevelError);
        bError |= bRdLevelError;
        if (!bRdLevelError)
            p->rdLevel = rdLevel;
    }
    OPT2("rdoq", "rdoq-level")
    {
        bool bRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));
        bError |= !parseBoolOrNumericInt(value, 0, p->rdoqLevel)
               || bRdoqTextualTrue
               || p->rdoqLevel < 0 || p->rdoqLevel > 2;
    }
    OPT("psy-rd")
    {
        bool bPsyRdTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));
        bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRd)
               || bPsyRdTextualTrue;
    }
    OPT("psy-rdoq")
    {
        bool bPsyRdoqTextualTrue = value && (!strcasecmp(value, "true") || !strcasecmp(value, "yes"));
        bError |= !parseBoolOrNumericDouble(value, 0.0, p->psyRdoq)
               || bPsyRdoqTextualTrue;
    }
    OPT("psy-bscale")
    {
        bool bPsyScaleBError = false;
        int psyScaleB = parseOptionIntValue(value, bPsyScaleBError);
        bError |= bPsyScaleBError;
        if (!bPsyScaleBError)
            p->psyScaleB = psyScaleB;
    }
    OPT("psy-pscale")
    {
        bool bPsyScalePError = false;
        int psyScaleP = parseOptionIntValue(value, bPsyScalePError);
        bError |= bPsyScalePError;
        if (!bPsyScalePError)
            p->psyScaleP = psyScaleP;
    }
    OPT("psy-iscale")
    {
        bool bPsyScaleIError = false;
        int psyScaleI = parseOptionIntValue(value, bPsyScaleIError);
        bError |= bPsyScaleIError;
        if (!bPsyScaleIError)
            p->psyScaleI = psyScaleI;
    }
    OPT("rd-refine")
    {
        bNameWasBool = true;
        p->bEnableRdRefine = x265_atobool(value, bError);
    }
    OPT("signhide")
    {
        bNameWasBool = true;
        p->bEnableSignHiding = x265_atobool(value, bError);
    }
    OPT("b-intra")
    {
        bNameWasBool = true;
        p->bIntraInBFrames = x265_atobool(value, bError);
    }
    OPT("deblock")
    {
        const char* separator = std::strchr(value, ':');
        if (!separator)
            separator = std::strchr(value, ',');

        if (separator)
        {
            int tcOffset = 0;
            int betaOffset = 0;
            bool bLocalError = !parseOptionIntPair(value, *separator, tcOffset, betaOffset);
            if (!bLocalError)
            {
                p->deblockingFilterTCOffset = tcOffset;
                p->deblockingFilterBetaOffset = betaOffset;
            }

            if (bLocalError)
                bError = true;
            else
                p->bEnableLoopFilter = true;
        }
        else
        {
            bool bLocalError = false;
            int offset = parseOptionIntToken(value, std::strlen(value), bLocalError);
            if (!bLocalError)
            {
                p->bEnableLoopFilter = 1;
                p->deblockingFilterTCOffset = offset;
                p->deblockingFilterBetaOffset = offset;
            }
            else
                p->bEnableLoopFilter = atobool(value);
        }
    }
    OPT("sao")
    {
        bNameWasBool = true;
        p->bEnableSAO = x265_atobool(value, bError);
    }
    OPT("sao-non-deblock")
    {
        bNameWasBool = true;
        p->bSaoNonDeblocked = x265_atobool(value, bError);
    }
    OPT("ssim")
    {
        bNameWasBool = true;
        p->bEnableSsim = x265_atobool(value, bError);
    }
    OPT("psnr")
    {
        bNameWasBool = true;
        p->bEnablePsnr = x265_atobool(value, bError);
    }
    OPT("hash")
    {
        bool bDecodedPictureHashSEIError = false;
        int decodedPictureHashSEI = parseOptionIntValue(value, bDecodedPictureHashSEIError);
        bError |= bDecodedPictureHashSEIError;
        if (!bDecodedPictureHashSEIError)
            p->decodedPictureHashSEI = decodedPictureHashSEI;
    }
    OPT("aud")
    {
        bNameWasBool = true;
        p->bEnableAccessUnitDelimiters = x265_atobool(value, bError);
    }
    OPT("info")
    {
        bNameWasBool = true;
        p->bEmitInfoSEI = x265_atobool(value, bError);
    }
    OPT("b-pyramid")
    {
        bNameWasBool = true;
        p->bBPyramid = x265_atobool(value, bError);
    }
    OPT("hrd")
    {
        bNameWasBool = true;
        p->bEmitHRDSEI = x265_atobool(value, bError);
    }
    OPT("ipratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.ipFactor);
    OPT("pbratio") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.pbFactor);
    OPT("hevc-aq")
    {
        bNameWasBool = true;
        p->rc.hevcAq = x265_atobool(value, bError);
    }
    OPT("qcomp")
    {
        double qCompress = 0.0;
        if (!parseOptionDoubleToken(value, std::strlen(value), qCompress))
            bError = true;
        else
        {
            p->rc.qCompress = qCompress;
            p->rc.cuTreeStrength = (p->rc.hevcAq ? 6.0 : 5.0) * (1.0 - qCompress);
        }
    }
    OPT("cutree-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.cuTreeStrength);
    OPT("cutree-minqpoffs") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.cuTreeMinQpOffset);
    OPT("cutree-maxqpoffs") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.cuTreeMaxQpOffset);
    OPT("qscale-mode")
    {
        bool bQScaleModeError = false;
        int qScaleMode = parseOptionIntValue(value, bQScaleModeError);
        bError |= bQScaleModeError;
        if (!bQScaleModeError)
            p->rc.qScaleMode = qScaleMode;
    }
    OPT("qpstep")
    {
        bool bQpStepError = false;
        int qpStep = parseOptionIntValue(value, bQpStepError);
        bError |= bQpStepError;
        if (!bQpStepError)
            p->rc.qpStep = qpStep;
    }
    OPT("cplxblur") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.complexityBlur);
    OPT("qblur") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.qblur);
    OPT("aq-mode")
    {
        bool bAqModeError = false;
        int aqMode = parseOptionIntValue(value, bAqModeError);
        bError |= bAqModeError;
        if (!bAqModeError)
            p->rc.aqMode = aqMode;
    }
    OPT("limit-aq1")
    {
        bNameWasBool = true;
        p->rc.limitAq1 = x265_atobool(value, bError);
    }
    OPT("aq-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.aqStrength);
    OPT("aq-bias-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.aqBiasStrength);
    OPT("limit-aq1-strength") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.limitAq1Strength);
    OPT("vbv-maxrate")
    {
        bool bVbvMaxBitrateError = false;
        int vbvMaxBitrate = parseOptionIntValue(value, bVbvMaxBitrateError);
        bError |= bVbvMaxBitrateError;
        if (!bVbvMaxBitrateError)
            p->rc.vbvMaxBitrate = vbvMaxBitrate;
    }
    OPT("vbv-bufsize")
    {
        bool bVbvBufferSizeError = false;
        int vbvBufferSize = parseOptionIntValue(value, bVbvBufferSizeError);
        bError |= bVbvBufferSizeError;
        if (!bVbvBufferSizeError)
            p->rc.vbvBufferSize = vbvBufferSize;
    }
    OPT("vbv-init")    bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.vbvBufferInit);
    OPT("crf-max")     bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.rfConstantMax);
    OPT("crf-min")     bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.rfConstantMin);
    OPT("qpmax")
    {
        bool bQpMaxError = false;
        int qpMax = parseOptionIntValue(value, bQpMaxError);
        bError |= bQpMaxError;
        if (!bQpMaxError)
            p->rc.qpMax = qpMax;
    }
    OPT("crf")
    {
        if (!parseOptionDoubleToken(value, std::strlen(value), p->rc.rfConstant))
            bError = true;
        else
            p->rc.rateControlMode = X265_RC_CRF;
    }
    OPT("bitrate")
    {
        bool bBitrateValueError = false;
        int bitrate = parseOptionIntValue(value, bBitrateValueError);
        bError |= bBitrateValueError;
        if (!bBitrateValueError)
        {
            p->rc.bitrate = bitrate;
            p->rc.rateControlMode = X265_RC_ABR;
        }
    }
    OPT("qp")
    {
        bool bQpValueError = false;
        int qp = parseOptionIntValue(value, bQpValueError);
        bError |= bQpValueError;
        if (!bQpValueError)
        {
            p->rc.qp = qp;
            p->rc.rateControlMode = X265_RC_CQP;
        }
    }
    OPT("rc-grain")
    {
        bNameWasBool = true;
        p->rc.bEnableGrain = x265_atobool(value, bError);
    }
    OPT("zones")
    {
        int zoneCount = 1;
        const char* c;

        for (c = value; *c; c++)
            zoneCount += (*c == '/');

        x265_zone* zones = X265_MALLOC(x265_zone, zoneCount);
        char* zoneText = nullptr;
        bool bZoneParseError = false;
        if (!zones)
            bZoneParseError = true;
        else
        {
            zoneText = strdup(value);
            if (!zoneText)
                bZoneParseError = true;
        }

        if (!bZoneParseError)
        {
            std::fill_n(zones, zoneCount, x265_zone());
            c = zoneText;
            for (int i = 0; i < zoneCount; i++)
            {
                char* zoneEnd = (i + 1 < zoneCount) ? std::strchr((char*)c, '/') : nullptr;
                char* entryEnd = zoneEnd ? zoneEnd : (char*)c + std::strlen(c);
                if (!parseZoneOptionEntry((char*)c, entryEnd, zones[i]))
                {
                    bZoneParseError = true;
                    break;
                }

                if (zoneEnd)
                    c = zoneEnd + 1;
            }
        }

        free(zoneText);
        bError |= bZoneParseError;
        if (!bZoneParseError)
        {
            x265_zone_free(p);
            p->rc.zoneCount = zoneCount;
            p->rc.zones = zones;
        }
        else
            X265_FREE(zones);
    }
    OPT("input-res")
    {
        bError |= !parseOptionIntPair(value, 'x', p->sourceWidth, p->sourceHeight);
    }
    OPT("input-csp")
    {
        bool bInternalCspError = false;
        int internalCsp = parseName(value, x265_source_csp_names, bInternalCspError);
        bError |= bInternalCspError;
        if (!bInternalCspError)
            p->internalCsp = internalCsp;
    }
    OPT("me")
    {
        bool bSearchMethodError = false;
        int searchMethod = parseName(value, x265_motion_est_names, bSearchMethodError);
        bError |= bSearchMethodError;
        if (!bSearchMethodError)
            p->searchMethod = searchMethod;
    }
    OPT("cutree")
    {
        bNameWasBool = true;
        p->rc.cuTree = x265_atobool(value, bError);
    }
    OPT("slow-firstpass")
    {
        bNameWasBool = true;
        p->rc.bEnableSlowFirstPass = x265_atobool(value, bError);
    }
    OPT("strict-cbr")
    {
        bool bStrictCbrError = false;
        int bStrictCbr = x265_atobool(value, bStrictCbrError);
        bError |= bStrictCbrError;
        if (!bStrictCbrError)
        {
            p->rc.bStrictCbr = bStrictCbr;
            p->rc.pbFactor = 1.0;
        }
    }
    OPT("sar")
    {
        bool bSarNameError = false;
        int aspectRatioIdc = parseName(value, x265_sar_names, bSarNameError);
        if (!bSarNameError)
            p->vui.aspectRatioIdc = aspectRatioIdc;
        else
        {
            int sarWidth = 0;
            int sarHeight = 0;
            bool bLocalError = !parseOptionIntPair(value, ':', sarWidth, sarHeight);
            if (!bLocalError)
            {
                p->vui.aspectRatioIdc = X265_EXTENDED_SAR;
                p->vui.sarWidth = sarWidth;
                p->vui.sarHeight = sarHeight;
            }
            bError |= bLocalError;
        }
    }
    OPT("overscan")
    {
        if (!strcmp(value, "show"))
            p->vui.bEnableOverscanInfoPresentFlag = 1;
        else if (!strcmp(value, "crop"))
        {
            p->vui.bEnableOverscanInfoPresentFlag = 1;
            p->vui.bEnableOverscanAppropriateFlag = 1;
        }
        else if (!strcmp(value, "unknown"))
            p->vui.bEnableOverscanInfoPresentFlag = 0;
        else
            bError = true;
    }
    OPT("videoformat")
    {
        bool bVideoFormatError = false;
        int videoFormat = parseName(value, x265_video_format_names, bVideoFormatError);
        bError |= bVideoFormatError;
        p->vui.bEnableVideoSignalTypePresentFlag = 1;
        if (!bVideoFormatError)
            p->vui.videoFormat = videoFormat;
    }
    OPT("range")
    {
        bool bVideoFullRangeError = false;
        int videoFullRange = parseName(value, x265_fullrange_names, bVideoFullRangeError);
        bError |= bVideoFullRangeError;
        p->vui.bEnableVideoSignalTypePresentFlag = 1;
        if (!bVideoFullRangeError)
            p->vui.bEnableVideoFullRangeFlag = videoFullRange;
    }
    OPT("colorprim")
    {
        bool bColorPrimariesError = false;
        int colorPrimaries = parseName(value, x265_colorprim_names, bColorPrimariesError);
        bError |= bColorPrimariesError;
        p->vui.bEnableVideoSignalTypePresentFlag = 1;
        p->vui.bEnableColorDescriptionPresentFlag = 1;
        if (!bColorPrimariesError)
            p->vui.colorPrimaries = colorPrimaries;
    }
    OPT("transfer")
    {
        bool bTransferCharacteristicsError = false;
        int transferCharacteristics = parseName(value, x265_transfer_names, bTransferCharacteristicsError);
        bError |= bTransferCharacteristicsError;
        p->vui.bEnableVideoSignalTypePresentFlag = 1;
        p->vui.bEnableColorDescriptionPresentFlag = 1;
        if (!bTransferCharacteristicsError)
            p->vui.transferCharacteristics = transferCharacteristics;
    }
    OPT("colormatrix")
    {
        bool bMatrixCoeffsError = false;
        int matrixCoeffs = parseName(value, x265_colmatrix_names, bMatrixCoeffsError);
        bError |= bMatrixCoeffsError;
        p->vui.bEnableVideoSignalTypePresentFlag = 1;
        p->vui.bEnableColorDescriptionPresentFlag = 1;
        if (!bMatrixCoeffsError)
            p->vui.matrixCoeffs = matrixCoeffs;
    }
    OPT("chromaloc")
    {
        bool bChromaSampleLocTypeError = false;
        int chromaSampleLocType = parseOptionIntValue(value, bChromaSampleLocTypeError);
        bError |= bChromaSampleLocTypeError;
        if (!bChromaSampleLocTypeError)
        {
            p->vui.bEnableChromaLocInfoPresentFlag = 1;
            p->vui.chromaSampleLocTypeTopField = chromaSampleLocType;
            p->vui.chromaSampleLocTypeBottomField = chromaSampleLocType;
        }
    }
    OPT("display-window")
    {
        int defDispWinLeftOffset = 0;
        int defDispWinTopOffset = 0;
        int defDispWinRightOffset = 0;
        int defDispWinBottomOffset = 0;
        bool bDisplayWindowError = !parseOptionIntQuad(value,
                                                       defDispWinLeftOffset,
                                                       defDispWinTopOffset,
                                                       defDispWinRightOffset,
                                                       defDispWinBottomOffset);
        bError |= bDisplayWindowError;
        if (!bDisplayWindowError)
        {
            p->vui.bEnableDefaultDisplayWindowFlag = 1;
            p->vui.defDispWinLeftOffset = defDispWinLeftOffset;
            p->vui.defDispWinTopOffset = defDispWinTopOffset;
            p->vui.defDispWinRightOffset = defDispWinRightOffset;
            p->vui.defDispWinBottomOffset = defDispWinBottomOffset;
        }
    }
        OPT("nr-intra")
        {
            bool bNoiseReductionIntraError = false;
            int noiseReductionIntra = parseOptionIntValue(value, bNoiseReductionIntraError);
            bError |= bNoiseReductionIntraError;
            if (!bNoiseReductionIntraError)
                p->noiseReductionIntra = noiseReductionIntra;
        }
        OPT("nr-inter")
        {
            bool bNoiseReductionInterError = false;
            int noiseReductionInter = parseOptionIntValue(value, bNoiseReductionInterError);
            bError |= bNoiseReductionInterError;
            if (!bNoiseReductionInterError)
                p->noiseReductionInter = noiseReductionInter;
        }
    OPT("pass")
    {
        bool bPassError = false;
        int parsedPass = parseOptionIntValue(value, bPassError);
        bError |= bPassError;
        if (!bPassError)
        {
            int pass = x265_clip3(0, 3, parsedPass);
            p->rc.bStatWrite = pass & 1;
            p->rc.bStatRead = pass & 2;
            p->rc.dataShareMode = X265_SHARE_MODE_FILE;
        }
    }
    OPT("stats") snprintf(p->rc.statFileName, X265_MAX_STRING_SIZE, "%s", value);
    OPT("scaling-list") snprintf(p->scalingLists, X265_MAX_STRING_SIZE, "%s", value);
    OPT2("pools", "numa-pools") snprintf(p->numaPools, X265_MAX_STRING_SIZE, "%s", value);
    OPT("lambda-file") snprintf(p->rc.lambdaFileName, X265_MAX_STRING_SIZE, "%s", value);
    OPT("analysis-reuse-file") snprintf(p->analysisReuseFileName, X265_MAX_STRING_SIZE, "%s", value);
    OPT("qg-size")
    {
        bool bQgSizeError = false;
        int qgSize = parseOptionIntValue(value, bQgSizeError);
        bError |= bQgSizeError;
        if (!bQgSizeError)
            p->rc.qgSize = qgSize;
    }
    OPT("master-display") snprintf(p->masteringDisplayColorVolume, X265_MAX_STRING_SIZE, "%s", value);
    OPT("max-cll")
    {
        uint16_t maxCLL = 0;
        uint16_t maxFALL = 0;
        bool bLocalError = !parseOptionUint16Pair(value, ',', maxCLL, maxFALL);
        if (!bLocalError)
        {
            p->maxCLL = maxCLL;
            p->maxFALL = maxFALL;
        }
        bError |= bLocalError;
    }
    OPT("min-luma")
    {
        bool bMinLumaError = false;
        uint16_t minLuma = parseOptionUint16Token(value, std::strlen(value), bMinLumaError);
        bError |= bMinLumaError;
        if (!bMinLumaError)
            p->minLuma = minLuma;
    }
    OPT("max-luma")
    {
        bool bMaxLumaError = false;
        uint16_t maxLuma = parseOptionUint16Token(value, std::strlen(value), bMaxLumaError);
        bError |= bMaxLumaError;
        if (!bMaxLumaError)
            p->maxLuma = maxLuma;
    }
    OPT("uhd-bd")
    {
        bNameWasBool = true;
        p->uhdBluray = x265_atobool(value, bError);
    }
    else
        bExtraParams = true;

    // solve "fatal error C1061: compiler limit : blocks nested too deeply"
    if (bExtraParams)
    {
        if (0) ;
        OPT("csv") snprintf(p->csvfn, X265_MAX_STRING_SIZE, "%s", value);
        OPT("progress-file")
        {
            char* newProgressFile = strdup(value);
            if (!newProgressFile)
                bError = true;
            else
            {
                free(p->pgfn);
                p->pgfn = newProgressFile;
            }
        }
        OPT("csv-log-level")
        {
            bool bCsvLogLevelError = false;
            int csvLogLevel = parseOptionIntValue(value, bCsvLogLevelError);
            bError |= bCsvLogLevelError;
            if (!bCsvLogLevelError)
                p->csvLogLevel = csvLogLevel;
        }
        OPT("qpmin")
        {
            bool bQpMinError = false;
            int qpMin = parseOptionIntValue(value, bQpMinError);
            bError |= bQpMinError;
            if (!bQpMinError)
                p->rc.qpMin = qpMin;
        }
        OPT("analyze-src-pics")
        {
            bNameWasBool = true;
            p->bSourceReferenceEstimation = x265_atobool(value, bError);
        }
        OPT("log2-max-poc-lsb")
        {
            bool bLog2MaxPocLsbError = false;
            int log2MaxPocLsb = parseOptionIntValue(value, bLog2MaxPocLsbError);
            bError |= bLog2MaxPocLsbError;
            if (!bLog2MaxPocLsbError)
                p->log2MaxPocLsb = log2MaxPocLsb;
        }
        OPT("vui-timing-info")
        {
            bNameWasBool = true;
            p->bEmitVUITimingInfo = x265_atobool(value, bError);
        }
        OPT("vui-hrd-info")
        {
            bNameWasBool = true;
            p->bEmitVUIHRDInfo = x265_atobool(value, bError);
        }
        OPT("slices")
        {
            bool bMaxSlicesError = false;
            int maxSlices = parseOptionIntValue(value, bMaxSlicesError);
            bError |= bMaxSlicesError;
            if (!bMaxSlicesError)
                p->maxSlices = maxSlices;
        }
        OPT("limit-tu")
        {
            bool bLimitTUError = false;
            int limitTU = parseOptionIntValue(value, bLimitTUError);
            bError |= bLimitTUError;
            if (!bLimitTUError)
                p->limitTU = limitTU;
        }
        OPT("opt-qp-pps") p->bOptQpPPS = atobool(value);
        OPT("opt-ref-list-length-pps") p->bOptRefListLengthPPS = atobool(value);
        OPT("multi-pass-opt-rps") p->bMultiPassOptRPS = atobool(value);
        OPT("scenecut-bias") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->scenecutBias);
        OPT("hist-scenecut") p->bHistBasedSceneCut = atobool(value);
        OPT("rskip-edge-threshold")
        {
            bool bEdgeVarThresholdError = false;
            int edgeVarThreshold = parseOptionIntValue(value, bEdgeVarThresholdError);
            bError |= bEdgeVarThresholdError;
            if (!bEdgeVarThresholdError)
                p->edgeVarThreshold = edgeVarThreshold / 100.0f;
        }
        OPT("lookahead-threads")
        {
            bool bLookaheadThreadsError = false;
            int lookaheadThreads = parseOptionIntValue(value, bLookaheadThreadsError);
            bError |= bLookaheadThreadsError;
            if (!bLookaheadThreadsError)
                p->lookaheadThreads = lookaheadThreads;
        }
        OPT("opt-cu-delta-qp") p->bOptCUDeltaQP = atobool(value);
        OPT("multi-pass-opt-analysis") p->analysisMultiPassRefine = atobool(value);
        OPT("multi-pass-opt-distortion") p->analysisMultiPassDistortion = atobool(value);
        OPT("aq-motion") p->bAQMotion = atobool(value);
        OPT("dynamic-rd") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->dynamicRd);
		OPT("cra-nal") p->craNal = atobool(value);
        OPT("analysis-save-reuse-level")
        {
            bool bAnalysisSaveReuseLevelError = false;
            int analysisSaveReuseLevel = parseOptionIntValue(value, bAnalysisSaveReuseLevelError);
            bError |= bAnalysisSaveReuseLevelError;
            if (!bAnalysisSaveReuseLevelError)
                p->analysisSaveReuseLevel = analysisSaveReuseLevel;
        }
        OPT("analysis-load-reuse-level")
        {
            bool bAnalysisLoadReuseLevelError = false;
            int analysisLoadReuseLevel = parseOptionIntValue(value, bAnalysisLoadReuseLevelError);
            bError |= bAnalysisLoadReuseLevelError;
            if (!bAnalysisLoadReuseLevelError)
                p->analysisLoadReuseLevel = analysisLoadReuseLevel;
        }
        OPT("ssim-rd")
        {
            bool bSsimRdError = false;
            int bSsimRd = x265_atobool(value, bSsimRdError);
            bError |= bSsimRdError;
            if (!bSsimRdError)
            {
                p->bSsimRd = bSsimRd;
                if (bSsimRd)
                    p->psyRd = 0.0;
            }
        }
        OPT("hdr") p->bEmitHDR10SEI = atobool(value);
        OPT("hdr10") p->bEmitHDR10SEI = atobool(value);
        OPT("hdr10-opt") p->bHDR10Opt = atobool(value);
        OPT("limit-sao") p->bLimitSAO = atobool(value);
        OPT("dhdr10-info") snprintf(p->toneMapFile, X265_MAX_STRING_SIZE, "%s", value);
        OPT("dhdr10-opt") p->bDhdr10opt = atobool(value);
        OPT("idr-recovery-sei") p->bEmitIDRRecoverySEI = atobool(value);
        OPT("const-vbv") p->rc.bEnableConstVbv = atobool(value);
        OPT("ctu-info")
        {
            bool bCTUInfoError = false;
            int ctuInfo = parseOptionIntValue(value, bCTUInfoError);
            bError |= bCTUInfoError;
            if (!bCTUInfoError)
                p->bCTUInfo = ctuInfo;
        }
        OPT("scale-factor")
        {
            bool bScaleFactorError = false;
            int scaleFactor = parseOptionIntValue(value, bScaleFactorError);
            bError |= bScaleFactorError;
            if (!bScaleFactorError)
                p->scaleFactor = scaleFactor;
        }
        OPT("refine-intra")
        {
            bool bIntraRefineError = false;
            int intraRefine = parseOptionIntValue(value, bIntraRefineError);
            bError |= bIntraRefineError;
            if (!bIntraRefineError)
                p->intraRefine = intraRefine;
        }
        OPT("refine-inter")
        {
            bool bInterRefineError = false;
            int interRefine = parseOptionIntValue(value, bInterRefineError);
            bError |= bInterRefineError;
            if (!bInterRefineError)
                p->interRefine = interRefine;
        }
        OPT("refine-mv")
        {
            bool bMvRefineError = false;
            int mvRefine = parseOptionIntValue(value, bMvRefineError);
            bError |= bMvRefineError;
            if (!bMvRefineError)
                p->mvRefine = mvRefine;
        }
        OPT("force-flush")
        {
            bool bForceFlushError = false;
            int forceFlush = parseOptionIntValue(value, bForceFlushError);
            bError |= bForceFlushError;
            if (!bForceFlushError)
                p->forceFlush = forceFlush;
        }
        OPT("splitrd-skip") p->bEnableSplitRdSkip = atobool(value);
        OPT("lowpass-dct") p->bLowPassDct = atobool(value);
        OPT("stylish") p->bStylish = atobool(value);
        OPT("vbv-end") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvBufferEnd);
        OPT("vbv-end-fr-adj") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->vbvEndFrameAdjust);
        OPT("copy-pic") p->bCopyPicToFrame = atobool(value);
        OPT("refine-analysis-type")
        {
            if (strcmp((value), "avc") == 0)
            {
                p->bAnalysisType = AVC_INFO;
            }
            else if (strcmp((value), "hevc") == 0)
            {
                p->bAnalysisType = HEVC_INFO;
            }
            else if (strcmp((value), "off") == 0)
            {
                p->bAnalysisType = DEFAULT;
            }
            else
            {
                bError = true;
            }
        }
        OPT("gop-lookahead")
        {
            bool bGopLookaheadError = false;
            int gopLookahead = parseOptionIntValue(value, bGopLookaheadError);
            bError |= bGopLookaheadError;
            if (!bGopLookaheadError)
                p->gopLookahead = gopLookahead;
        }
        OPT("analysis-save") snprintf(p->analysisSave, X265_MAX_STRING_SIZE, "%s", value);
        OPT("analysis-load") snprintf(p->analysisLoad, X265_MAX_STRING_SIZE, "%s", value);
        OPT("radl")
        {
            bool bRadlError = false;
            int radl = parseOptionIntValue(value, bRadlError);
            bError |= bRadlError;
            if (!bRadlError)
                p->radl = radl;
        }
        OPT("max-ausize-factor") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxAUSizeFactor);
        OPT("dynamic-refine") p->bDynamicRefine = atobool(value);
        OPT("single-sei") p->bSingleSeiNal = atobool(value);
        OPT("atc-sei")
        {
            bool bPreferredTransferCharacteristicsError = false;
            int preferredTransferCharacteristics = parseOptionIntValue(value, bPreferredTransferCharacteristicsError);
            const bool bPreferredTransferCharacteristicsRangeError = preferredTransferCharacteristics < -1
                                                                  || preferredTransferCharacteristics > UINT8_MAX;
            bError |= bPreferredTransferCharacteristicsError || bPreferredTransferCharacteristicsRangeError;
            if (!bPreferredTransferCharacteristicsError && !bPreferredTransferCharacteristicsRangeError)
                p->preferredTransferCharacteristics = preferredTransferCharacteristics;
        }
        OPT("pic-struct")
        {
            bool bPictureStructureError = false;
            int pictureStructure = parseOptionIntValue(value, bPictureStructureError);
            const bool bPictureStructureRangeError = pictureStructure < -1
                                                  || pictureStructure > 8;
            bError |= bPictureStructureError || bPictureStructureRangeError;
            if (!bPictureStructureError && !bPictureStructureRangeError)
                p->pictureStructure = pictureStructure;
        }
        OPT("chunk-start")
        {
            bool bChunkStartError = false;
            int chunkStart = parseOptionIntValue(value, bChunkStartError);
            const bool bChunkStartRangeError = chunkStart < 0;
            bError |= bChunkStartError || bChunkStartRangeError;
            if (!bChunkStartError && !bChunkStartRangeError)
                p->chunkStart = chunkStart;
        }
        OPT("chunk-end")
        {
            bool bChunkEndError = false;
            int chunkEnd = parseOptionIntValue(value, bChunkEndError);
            const bool bChunkEndRangeError = chunkEnd < 0;
            bError |= bChunkEndError || bChunkEndRangeError;
            if (!bChunkEndError && !bChunkEndRangeError)
                p->chunkEnd = chunkEnd;
        }
        OPT("nalu-file") snprintf(p->naluFile, X265_MAX_STRING_SIZE, "%s", value);
        OPT("dolby-vision-profile")
        {
            if (!parseTenthsOrIntegerLevel(value, p->dolbyProfile))
                bError = true;
        }
        OPT("hrd-concat") p->bEnableHRDConcatFlag = atobool(value);
        OPT("refine-ctu-distortion")
        {
            bool bCtuDistortionRefineError = false;
            int ctuDistortionRefine = parseOptionIntValue(value, bCtuDistortionRefineError);
            bError |= bCtuDistortionRefineError;
            if (!bCtuDistortionRefineError)
                p->ctuDistortionRefine = ctuDistortionRefine;
        }
        OPT("hevc-aq") p->rc.hevcAq = atobool(value);
        OPT("qp-adaptation-range") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->rc.qpAdaptationRange);
#ifdef SVT_HEVC
        OPT("svt")
        {
            p->bEnableSvtHevc = atobool(value);
            if (svtParseCallCount > 1 && p->bEnableSvtHevc)
            {
                x265_log(nullptr, X265_LOG_ERROR, "Enable SVT should be the first call to x265_parse_parse \n");
                bError = true;
            }
            if (p->bEnableSvtHevc)
            {
                EB_H265_ENC_CONFIGURATION* svtParam = ensureSvtHevcParam(p);
                if (!svtParam)
                {
                    x265_log(p, X265_LOG_ERROR, "unable to allocate SVT parameter storage\n");
                    bError = true;
                }
            }
            else
            {
                freeSvtHevcParamStorage(p);
            }
        }
        OPT("svt-hme") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("svt-search-width") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("svt-search-height") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("svt-compressed-ten-bit-format") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("svt-speed-control") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("input-depth") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("svt-preset-tuner") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("svt-hierarchical-level") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("svt-base-layer-switch-mode") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("svt-pred-struct") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
        OPT("svt-fps-in-vps") x265_log(p, X265_LOG_WARNING, "Option %s is SVT-HEVC Encoder specific; Disabling it here \n", name);
#endif
        OPT("selective-sao")
        {
            bool bSelectiveSaoError = false;
            int selectiveSao = parseOptionIntValue(value, bSelectiveSaoError);
            bError |= bSelectiveSaoError;
            if (!bSelectiveSaoError)
                p->selectiveSAO = selectiveSao;
        }
        OPT("fades") p->bEnableFades = atobool(value);
        OPT("scenecut-aware-qp")
        {
            bool bSceneCutAwareQpError = false;
            int sceneCutAwareQp = parseOptionIntValue(value, bSceneCutAwareQpError);
            bError |= bSceneCutAwareQpError;
            if (!bSceneCutAwareQpError)
                p->bEnableSceneCutAwareQp = sceneCutAwareQp;
        }
        OPT("masking-strength") bError |= parseMaskingStrength(p, value);
        OPT("field") p->bField = atobool( value );
        OPT("cll") p->bEmitCLL = atobool(value);
        OPT("frame-dup") p->bEnableFrameDuplication = atobool(value);
        OPT("dup-threshold")
        {
            bool bDupThresholdError = false;
            int dupThreshold = parseOptionIntValue(value, bDupThresholdError);
            bError |= bDupThresholdError;
            if (!bDupThresholdError)
                p->dupThreshold = dupThreshold;
        }
        OPT("hme") p->bEnableHME = atobool(value);
        OPT("hme-search")
        {
            const char* search[3];
            size_t searchLengths[3];
            int count = splitCommaOption(value, search, searchLengths, 3);
            bool bLocalError = false;
            if (count == 1 || count == 3)
            {
                bool bNumeric = true;
                for (int level = 0; level < count; level++)
                    bNumeric &= std::isdigit((unsigned char)search[level][0]) || search[level][0] == '-' || search[level][0] == '+';

                if (bNumeric)
                {
                    int parsed[3];
                    for (int level = 0; level < count; level++)
                        parsed[level] = parseOptionIntToken(search[level], searchLengths[level], bLocalError);

                    if (!bLocalError)
                        assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);
                }
                else
                {
                    int parsed[3];
                    for (int level = 0; level < count; level++)
                        parsed[level] = parseHmeSearchMethodToken(search[level], searchLengths[level], bLocalError);
                    if (!bLocalError)
                        assignParsedOptionLevels(parsed, count, p->hmeSearchMethod);
                }
            }
            else
                bLocalError = true;
            bError |= bLocalError;
            if (!bLocalError)
                p->bEnableHME = true;
        }
        OPT("hme-range")
        {
            const char* range[3];
            size_t rangeLengths[3];
            bool bLocalError = false;
            if (splitCommaOption(value, range, rangeLengths, 3) != 3)
                bLocalError = true;
            else
            {
                int parsed[3];
                for (int level = 0; level < 3; level++)
                    parsed[level] = parseOptionIntToken(range[level], rangeLengths[level], bLocalError);
                if (!bLocalError)
                    assignParsedOptionLevels(parsed, 3, p->hmeRange);
            }
            bError |= bLocalError;
            if (!bLocalError)
                p->bEnableHME = true;
        }
        OPT("vbv-live-multi-pass") p->bliveVBV2pass = atobool(value);
        OPT("min-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->minVbvFullness);
        OPT("max-vbv-fullness") bError |= !parseOptionDoubleToken(value, std::strlen(value), p->maxVbvFullness);
        OPT("video-signal-type-preset") snprintf(p->videoSignalTypePreset, X265_MAX_STRING_SIZE, "%s", value);
        OPT("eob") p->bEnableEndOfBitstream = atobool(value);
        OPT("eos") p->bEnableEndOfSequence = atobool(value);
        /* Film grain characterstics model filename */
        OPT("film-grain") p->filmGrain = (char* )value;
        OPT("aom-film-grain") p->aomFilmGrain = (char*)value;
        OPT("mcstf") p->bEnableTemporalFilter = atobool(value);
        OPT("sbrc") p->bEnableSBRC = atobool(value);
#if ENABLE_ALPHA
        OPT("alpha")
        {
            if (atobool(value))
            {
                p->bEnableAlpha = 1;
                p->numScalableLayers = 2;
                p->numLayers = 2;
            }
        }
#endif
#if ENABLE_MULTIVIEW
        OPT("format")
        {
            bool bFormatError = false;
            int format = parseOptionIntValue(value, bFormatError);
            bError |= bFormatError;
            if (!bFormatError)
                p->format = format;
        }
        OPT("num-views")
        {
            bool bNumViewsError = false;
            int numViews = parseOptionIntValue(value, bNumViewsError);
            bError |= bNumViewsError;
            if (!bNumViewsError)
                p->numViews = numViews;
        }
#endif
#if ENABLE_SCC_EXT
        OPT("scc")
        {
            bool bSccError = false;
            int bEnableSCC = parseOptionIntValue(value, bSccError);
            bError |= bSccError;
            if (!bSccError)
                p->bEnableSCC = bEnableSCC;
        }
#endif
        OPT("frame-rc") p->bConfigRCFrame = atobool(value);
        OPT("threaded-me") p->bThreadedME = atobool(value);
        else
            return X265_PARAM_BAD_NAME;
    }
#undef OPT
#undef atobool
#undef atoi
#undef atof

    bError |= bValueWasNull && !bNameWasBool;
    return bError ? X265_PARAM_BAD_VALUE : 0;
}

} /* end extern "C" or namespace */

namespace X265_NS {
// internal encoder functions

bool isAllocatedParamInstance(const x265_param* param)
{
    return ::isAllocatedParamInstance(param);
}

void finalizeZoneParamCopy(x265_param* zoneParam, const x265_param* src)
{
    ::finalizeZoneParamCopy(zoneParam, src);
}

int x265_atoi(const char* str, bool& bError)
{
    if (!str)
    {
        bError = true;
        return 0;
    }

    errno = 0;
    char *end;
    long parsed = strtol(str, &end, 0);

    if (errno == ERANGE || parsed < INT_MIN || parsed > INT_MAX || end == str || *end != '\0')
        bError = true;
    return (int)parsed;
}

double x265_atof(const char* str, bool& bError)
{
    if (!str)
    {
        bError = true;
        return 0.0;
    }

    errno = 0;
    char *end;
    double v = strtod(str, &end);

    if (errno == ERANGE || end == str || *end != '\0')
        bError = true;
    return v;
}

/* cpu name can be:
 *   auto || true - x265::cpu_detect()
 *   false || no  - disabled
 *   integer bitmap value
 *   comma separated list of SIMD names, eg: SSE4.1,XOP */
int parseCpuName(const char* value, bool& bError, bool bEnableavx512)
{
    if (!value)
    {
        bError = 1;
        return 0;
    }
    int cpu;
    if (isdigit(value[0]))
        cpu = parseOptionIntValue(value, bError);
    else
        cpu = !strcmp(value, "auto") || x265_atobool(value, bError) ? X265_NS::cpu_detect(bEnableavx512) : 0;

    if (bError)
    {
        char *buf = strdup(value);
        if (!buf)
        {
            bError = 1;
            return 0;
        }
        char *tok;
        bError = 0;
        cpu = 0;
        for (char* scan = buf; scan && *scan; )
        {
            char* separator = std::strchr(scan, ',');
            if (separator)
                *separator = '\0';
            tok = scan;
            scan = separator ? separator + 1 : nullptr;
            if (!*tok)
            {
                bError = 1;
                continue;
            }

            int i;
            for (i = 0; X265_NS::cpu_names[i].flags && strcasecmp(tok, X265_NS::cpu_names[i].name); i++)
            {
            }

            cpu |= X265_NS::cpu_names[i].flags;
            if (!X265_NS::cpu_names[i].flags)
                bError = 1;
        }

        free(buf);
#if X265_ARCH_X86
        if ((cpu & X265_CPU_SSSE3) && !(cpu & X265_CPU_SSE2_IS_SLOW))
            cpu |= X265_CPU_SSE2_IS_FAST;
#endif
    }

    return cpu;
}

static const int fixedRatios[][2] =
{
    { 1,  1 },
    { 12, 11 },
    { 10, 11 },
    { 16, 11 },
    { 40, 33 },
    { 24, 11 },
    { 20, 11 },
    { 32, 11 },
    { 80, 33 },
    { 18, 11 },
    { 15, 11 },
    { 64, 33 },
    { 160, 99 },
    { 4, 3 },
    { 3, 2 },
    { 2, 1 },
};

void setParamAspectRatio(x265_param* p, int width, int height)
{
    p->vui.aspectRatioIdc = X265_EXTENDED_SAR;
    p->vui.sarWidth = width;
    p->vui.sarHeight = height;
    for (size_t i = 0; i < sizeof(fixedRatios) / sizeof(fixedRatios[0]); i++)
    {
        if (width == fixedRatios[i][0] && height == fixedRatios[i][1])
        {
            p->vui.aspectRatioIdc = (int)i + 1;
            return;
        }
    }
}

void getParamAspectRatio(x265_param* p, int& width, int& height)
{
    if (!p->vui.aspectRatioIdc)
        width = height = 0;
    else if ((size_t)p->vui.aspectRatioIdc <= sizeof(fixedRatios) / sizeof(fixedRatios[0]))
    {
        width  = fixedRatios[p->vui.aspectRatioIdc - 1][0];
        height = fixedRatios[p->vui.aspectRatioIdc - 1][1];
    }
    else if (p->vui.aspectRatioIdc == X265_EXTENDED_SAR)
    {
        width  = p->vui.sarWidth;
        height = p->vui.sarHeight;
    }
    else
        width = height = 0;
}

static inline int _confirm(x265_param* param, bool bflag, const char* message)
{
    if (!bflag)
        return 0;

    x265_log(param, X265_LOG_ERROR, "%s\n", message);
    return 1;
}

int x265_check_params(x265_param* param)
{
    if (!param)
    {
        x265_log(nullptr, X265_LOG_ERROR, "x265_check_params requires a non-null parameter struct\n");
        return X265_PARAM_BAD_VALUE;
    }

#define CHECK(expr, msg) check_failed |= _confirm(param, expr, msg)
    int check_failed = 0; /* abort if there is a fatal configuration problem */
    CHECK((uint64_t)param->sourceWidth * param->sourceHeight > 142606336ULL && !param->bAllowNonConformance,
          "Input video resolution exceeds the maximum supported luma samples 142,606,336 (16384x8704) of Level 7.2.");
    CHECK(param->uhdBluray == 1 && (X265_DEPTH != 10 || param->internalCsp != 1 || param->interlaceMode != 0),
        "uhd-bd: bit depth, chroma subsample, source picture type must be 10, 4:2:0, progressive");
    CHECK(param->maxCUSize != 64 && param->maxCUSize != 32 && param->maxCUSize != 16,
          "max cu size must be 16, 32, or 64");
    if (check_failed == 1)
        return check_failed;

    uint32_t maxLog2CUSize = (uint32_t)g_log2Size[param->maxCUSize];
    uint32_t tuQTMaxLog2Size = X265_MIN(maxLog2CUSize, 5);
    uint32_t tuQTMinLog2Size = 2; //log2(4)

    CHECK(param->maxSlices < 1,
        "maxSlices must be 1 or greater");
    CHECK((param->maxSlices > 1) && !param->bEnableWavefront,
        "Multiple-Slices mode must be enable Wavefront Parallel Processing (--wpp)");
    CHECK(param->internalBitDepth != X265_DEPTH,
          "internalBitDepth must match compiled bit depth");
    CHECK(param->minCUSize != 32 && param->minCUSize != 16 && param->minCUSize != 8,
          "minimim CU size must be 8, 16 or 32");
    CHECK(param->minCUSize > param->maxCUSize,
          "min CU size must be less than or equal to max CU size");
    CHECK(param->rc.qp < -6 * (param->internalBitDepth - 8) || param->rc.qp > QP_MAX_SPEC,
          "QP exceeds supported range (-QpBDOffsety to 51)");
    CHECK(param->fpsNum == 0 || param->fpsDenom == 0,
          "Frame rate numerator and denominator must be specified");
    CHECK(param->interlaceMode < 0 || param->interlaceMode > 2,
          "Interlace mode must be 0 (progressive) 1 (top-field first) or 2 (bottom field first)");
    CHECK(param->searchMethod < 0 || param->searchMethod > X265_FULL_SEARCH,
          "Search method is not supported value (0:DIA 1:HEX 2:UMH 3:HM 4:SEA 5:FULL)");
    CHECK(param->searchRange < 0,
          "Search Range must be more than 0");
    CHECK(param->searchRange >= 32768,
          "Search Range must be less than 32768");
    CHECK(param->subpelRefine > X265_MAX_SUBPEL_LEVEL,
          "subme must be less than or equal to X265_MAX_SUBPEL_LEVEL (7)");
    CHECK(param->subpelRefine < 0,
          "subme must be greater than or equal to 0");
    CHECK(param->limitReferences > 3,
          "limitReferences must be 0, 1, 2 or 3");
    CHECK(param->limitModes > 1,
          "limitRectAmp must be 0, 1");
    CHECK(param->frameNumThreads < 0 || param->frameNumThreads > X265_MAX_FRAME_THREADS,
          "frameNumThreads (--frame-threads) must be [0 .. X265_MAX_FRAME_THREADS)");
    CHECK(param->cbQpOffset < -12, "Min. Chroma Cb QP Offset is -12");
    CHECK(param->cbQpOffset >  12, "Max. Chroma Cb QP Offset is  12");
    CHECK(param->crQpOffset < -12, "Min. Chroma Cr QP Offset is -12");
    CHECK(param->crQpOffset >  12, "Max. Chroma Cr QP Offset is  12");

    CHECK(tuQTMaxLog2Size > maxLog2CUSize,
          "QuadtreeTULog2MaxSize must be log2(maxCUSize) or smaller.");

    CHECK(param->tuQTMaxInterDepth < 1 || param->tuQTMaxInterDepth > 4,
          "QuadtreeTUMaxDepthInter must be greater than 0 and less than 5");
    CHECK(maxLog2CUSize < tuQTMinLog2Size + param->tuQTMaxInterDepth - 1,
          "QuadtreeTUMaxDepthInter must be less than or equal to the difference between log2(maxCUSize) and QuadtreeTULog2MinSize plus 1");
    CHECK(param->tuQTMaxIntraDepth < 1 || param->tuQTMaxIntraDepth > 4,
          "QuadtreeTUMaxDepthIntra must be greater 0 and less than 5");
    CHECK(maxLog2CUSize < tuQTMinLog2Size + param->tuQTMaxIntraDepth - 1,
          "QuadtreeTUMaxDepthInter must be less than or equal to the difference between log2(maxCUSize) and QuadtreeTULog2MinSize plus 1");
    CHECK((param->maxTUSize != 32 && param->maxTUSize != 16 && param->maxTUSize != 8 && param->maxTUSize != 4),
          "max TU size must be 4, 8, 16, or 32");
    CHECK(param->limitTU > 4, "Invalid limit-tu option, limit-TU must be between 0 and 4");
    CHECK(param->maxNumMergeCand < 1, "MaxNumMergeCand must be 1 or greater.");
    CHECK(param->maxNumMergeCand > 5, "MaxNumMergeCand must be 5 or smaller.");

    CHECK(param->maxNumReferences < 1, "maxNumReferences must be 1 or greater.");
    CHECK(param->maxNumReferences > MAX_NUM_REF, "maxNumReferences must be 16 or smaller.");

    CHECK(param->sourceWidth < (int)param->maxCUSize || param->sourceHeight < (int)param->maxCUSize,
          "Picture size must be at least one CTU");
    CHECK(param->internalCsp < X265_CSP_I400 || X265_CSP_I444 < param->internalCsp,
          "chroma subsampling must be i400 (4:0:0 monochrome), i420 (4:2:0 default), i422 (4:2:0), i444 (4:4:4)");
    CHECK(CHROMA_H_SHIFT(param->internalCsp) && (param->sourceWidth & 1),
          "Picture width must be an integer multiple of the specified chroma subsampling");
    CHECK(CHROMA_V_SHIFT(param->internalCsp) && (param->sourceHeight & 1),
          "Picture height must be an integer multiple of the specified chroma subsampling");

    CHECK(param->rc.rateControlMode > X265_RC_CRF || param->rc.rateControlMode < X265_RC_ABR,
          "Rate control mode is out of range");
    CHECK(param->rdLevel < 1 || param->rdLevel > 6,
          "RD Level is out of range");
    CHECK(param->rdoqLevel < 0 || param->rdoqLevel > 2,
          "RDOQ Level is out of range");
    CHECK(param->dynamicRd < 0 || param->dynamicRd > x265_ADAPT_RD_STRENGTH,
          "Dynamic RD strength must be between 0 and 4");
    CHECK(param->recursionSkipMode > 2 || param->recursionSkipMode < 0,
          "Invalid Recursion skip mode. Valid modes 0,1,2");
    if (param->recursionSkipMode == EDGE_BASED_RSKIP)
    {
        CHECK(param->edgeVarThreshold < 0.0f || param->edgeVarThreshold > 1.0f,
              "Minimum edge density percentage for a CU should be an integer between 0 to 100");
    }
    CHECK(param->bframes && (param->bEnableTemporalFilter ? (param->bframes > param->lookaheadDepth) : (param->bframes >= param->lookaheadDepth)) && !param->rc.bStatRead,
          "Lookahead depth must be greater than the max consecutive bframe count");
    CHECK(param->bframes < 0,
          "bframe count should be greater than zero");
    CHECK(param->bframes > X265_BFRAME_MAX,
          "max consecutive bframe count must be 16 or smaller");
    CHECK(param->lookaheadDepth > X265_LOOKAHEAD_MAX,
          "Lookahead depth must be less than 256");
    CHECK(param->lookaheadSlices > 16 || param->lookaheadSlices < 0,
          "Lookahead slices must between 0 and 16");
    CHECK(param->lookaheadThreads < 0 || param->lookaheadThreads > MAX_POOL_THREADS,
          "Lookahead threads must be between 0 and MAX_POOL_THREADS");
    CHECK(param->rc.aqMode < X265_AQ_NONE || X265_AQ_EDGE_BIASED < param->rc.aqMode,
          "Aq-Mode is out of range");
    CHECK(param->rc.aqStrength < 0 || param->rc.aqStrength > 3,
          "Aq-Strength is out of range");
    CHECK(param->rc.ipFactor <= 0,
          "ipratio must be greater than 0");
    CHECK(param->rc.pbFactor <= 0,
          "pbratio must be greater than 0");
    CHECK(param->rc.aqBiasStrength < 0 || param->rc.aqBiasStrength > 3,
          "Aq-Bias-Strength is out of range");
    CHECK(param->rc.limitAq1Strength < 0 || param->rc.limitAq1Strength > 3,
          "Limit-Aq1-Strength is out of range");
    CHECK(param->rc.qpAdaptationRange < 1.0f || param->rc.qpAdaptationRange > 6.0f,
        "qp adaptation range is out of range");
    CHECK(param->rc.qScaleMode > 4 || param->rc.qScaleMode < 0,
          "Invalid qScale mode. Valide modes 0,1,2,3,4");
    CHECK(param->rc.cuTree && (param->rc.cuTreeStrength < 0.0 || param->rc.cuTreeStrength > 3.0),
          "cuTreeStrength must be between 0.0 and 3.0");
    CHECK(param->rc.cuTreeMinQpOffset < -QP_MAX_MAX || param->rc.cuTreeMinQpOffset > QP_MIN,
          "cuTreeMinQpOffset exceeds supported range (-69 to 0)");
    CHECK(param->rc.cuTreeMaxQpOffset < QP_MIN || param->rc.cuTreeMaxQpOffset > QP_MAX_MAX,
          "cuTreeMaxQpOffset exceeds supported range ( 0 to 69)");
    CHECK(param->deblockingFilterTCOffset < -6 || param->deblockingFilterTCOffset > 6,
          "deblocking filter tC offset must be in the range of -6 to +6");
    CHECK(param->deblockingFilterBetaOffset < -6 || param->deblockingFilterBetaOffset > 6,
          "deblocking filter Beta offset must be in the range of -6 to +6");
    CHECK(param->psyRd < 0 || 5.0 < param->psyRd, "Psy-rd strength must be between 0 and 5.0");
    CHECK(param->psyRdoq < 0 || 50.0 < param->psyRdoq, "Psy-rdoq strength must be between 0 and 50.0");
    CHECK(param->psyScaleB < 0 || 300 < param->psyScaleB, "Psy-bscale must be between 0 and 300");
    CHECK(param->psyScaleP < 0 || 300 < param->psyScaleP, "Psy-pscale must be between 0 and 300");
    CHECK(param->psyScaleI < 0 || 300 < param->psyScaleI, "Psy-iscale must be between 0 and 300");
    CHECK(param->bEnableWavefront < 0, "WaveFrontSynchro cannot be negative");
    CHECK((param->vui.aspectRatioIdc < 0
           || param->vui.aspectRatioIdc > 16)
          && param->vui.aspectRatioIdc != X265_EXTENDED_SAR,
          "Sample Aspect Ratio must be 0-16 or 255");
    CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarWidth <= 0,
          "Sample Aspect Ratio width must be greater than 0");
    CHECK(param->vui.aspectRatioIdc == X265_EXTENDED_SAR && param->vui.sarHeight <= 0,
          "Sample Aspect Ratio height must be greater than 0");
    CHECK(param->vui.videoFormat < 0 || param->vui.videoFormat > 5,
          "Video Format must be component,"
          " pal, ntsc, secam, mac or unknown");
    CHECK(param->vui.colorPrimaries < 0
          || param->vui.colorPrimaries > 12
          || param->vui.colorPrimaries == 3,
          "Color Primaries must be unknown, bt709, bt470m,"
          " bt470bg, smpte170m, smpte240m, film, bt2020, smpte-st-428, smpte-rp-431 or smpte-eg-432");
    CHECK(param->vui.transferCharacteristics < 0
          || param->vui.transferCharacteristics > 18
          || param->vui.transferCharacteristics == 3,
          "Transfer Characteristics must be unknown, bt709, bt470m, bt470bg,"
          " smpte170m, smpte240m, linear, log100, log316, iec61966-2-4, bt1361e,"
          " iec61966-2-1, bt2020-10, bt2020-12, smpte-st-2084, smpte-st-428 or arib-std-b67");
    CHECK(param->vui.matrixCoeffs < 0
          || param->vui.matrixCoeffs > 15
          || param->vui.matrixCoeffs == 3,
          "Matrix Coefficients must be unknown, bt709, fcc, bt470bg, smpte170m,"
          " smpte240m, gbr, ycgco, bt2020nc, bt2020c, smpte-st-2085, chroma-nc, chroma-c, ictcp or ipt-pq-c2");
    CHECK(param->vui.chromaSampleLocTypeTopField < 0
          || param->vui.chromaSampleLocTypeTopField > 5,
          "Chroma Sample Location Type Top Field must be 0-5");
    CHECK(param->vui.chromaSampleLocTypeBottomField < 0
          || param->vui.chromaSampleLocTypeBottomField > 5,
          "Chroma Sample Location Type Bottom Field must be 0-5");
    CHECK(param->vui.defDispWinLeftOffset < 0,
          "Default Display Window Left Offset must be 0 or greater");
    CHECK(param->vui.defDispWinRightOffset < 0,
          "Default Display Window Right Offset must be 0 or greater");
    CHECK(param->vui.defDispWinTopOffset < 0,
          "Default Display Window Top Offset must be 0 or greater");
    CHECK(param->vui.defDispWinBottomOffset < 0,
          "Default Display Window Bottom Offset must be 0 or greater");
    CHECK(param->rc.rfConstant < -6 * (param->internalBitDepth - 8) || param->rc.rfConstant > 51,
          "Valid quality based range: -qpBDOffsetY to 51");
    CHECK(param->rc.rfConstantMax < -6 * (param->internalBitDepth - 8) || param->rc.rfConstantMax > 51,
          "Valid quality based range: -qpBDOffsetY to 51");
    CHECK(param->rc.rfConstantMin < -6 * (param->internalBitDepth - 8) || param->rc.rfConstantMin > 51,
          "Valid quality based range: -qpBDOffsetY to 51");
    CHECK(param->bFrameAdaptive < 0 || param->bFrameAdaptive > 2,
          "Valid adaptive b scheduling values 0 - none, 1 - fast, 2 - full");
    CHECK(param->logLevel<-1 || param->logLevel> X265_LOG_FULL,
          "Valid Logging level -1:none 0:error 1:warning 2:info 3:debug 4:full");
    CHECK(param->scenecutThreshold < 0,
          "scenecutThreshold must be greater than 0");
    CHECK(param->scenecutBias < 0 || 100 < param->scenecutBias,
            "scenecut-bias must be between 0 and 100");
    CHECK(param->radl < 0 || param->radl > param->bframes,
          "radl must be between 0 and bframes");
    CHECK(param->rdPenalty < 0 || param->rdPenalty > 2,
          "Valid penalty for 32x32 intra TU in non-I slices. 0:disabled 1:RD-penalty 2:maximum");
    CHECK(param->keyframeMax < -1,
          "Invalid max IDR period in frames. value should be greater than -1");
    CHECK(param->gopLookahead < 0,
          "GOP lookahead must be 0 or greater");
    CHECK(param->decodedPictureHashSEI < 0 || param->decodedPictureHashSEI > 3,
          "Invalid hash option. Decoded Picture Hash SEI 0: disabled, 1: MD5, 2: CRC, 3: Checksum");
    CHECK(param->rc.vbvBufferSize < 0,
          "Size of the vbv buffer can not be less than zero");
    CHECK(param->rc.vbvMaxBitrate < 0,
          "Maximum local bit rate can not be less than zero");
    CHECK(param->rc.vbvBufferInit < 0,
          "Valid initial VBV buffer occupancy must be a fraction 0 - 1, or size in kbits");
    CHECK(param->vbvBufferEnd < 0,
        "Valid final VBV buffer emptiness must be a fraction 0 - 1, or size in kbits");
    CHECK(param->vbvEndFrameAdjust < 0 || param->vbvEndFrameAdjust > 1,
        "Valid vbv-end-fr-adj must be a fraction 0 - 1");
    CHECK(param->vbvBufferEnd > 0 && param->vbvEndFrameAdjust == 0,
        "vbv-end-fr-adj must be greater than 0 when vbv-end is enabled");
    if ((param->rc.vbvBufferSize > 0 || param->rc.vbvMaxBitrate > 0) && param->bThreadedME)
    {
        param->bThreadedME = 0;
        x265_log(param, X265_LOG_WARNING, "VBV and threaded-me both enabled. Disabling threaded-me\n");
    }
    CHECK(param->minVbvFullness < 0 || param->minVbvFullness > 100,
        "min-vbv-fullness must be a fraction 0 - 100");
    CHECK(param->maxVbvFullness < 0 || param->maxVbvFullness > 100,
        "max-vbv-fullness must be a fraction 0 - 100");
    CHECK(param->rc.bitrate < 0,
          "Target bitrate can not be less than zero");
    CHECK(param->rc.qCompress < 0.5 || param->rc.qCompress > 1.0,
          "qCompress must be between 0.5 and 1.0");
    if (param->noiseReductionIntra)
        CHECK(0 > param->noiseReductionIntra || param->noiseReductionIntra > 2000, "Valid noise reduction range 0 - 2000");
    if (param->noiseReductionInter)
        CHECK(0 > param->noiseReductionInter || param->noiseReductionInter > 2000, "Valid noise reduction range 0 - 2000");
    CHECK(param->rc.rateControlMode == X265_RC_CQP && param->rc.bStatRead,
          "Constant QP is incompatible with 2pass");
    CHECK(param->rc.bStrictCbr && (param->rc.bitrate <= 0 || param->rc.vbvBufferSize <=0),
          "Strict-cbr cannot be applied without specifying both target bitrate and vbv bufsize");
    CHECK(!param->bResetZoneConfig && !param->rc.zonefileCount,
          "Zone reconfiguration without RC reset requires configured zonefile state");
    CHECK(param->rc.zonefileCount && !param->bResetZoneConfig && !param->reconfigWindowSize,
          "Zonefile reconfiguration without RC reset requires a non-zero reconfig window size");
    CHECK((size_t)param->reconfigWindowSize > SIZE_MAX / sizeof(double),
          "Zonefile reconfiguration window size exceeds supported relativeComplexity storage");
    if (param->rc.zonefileCount && param->rc.zones)
    {
        for (int i = 0; i < param->rc.zonefileCount; i++)
        {
            CHECK(param->rc.zones[i].startFrame < 0,
                "Zonefile start frames must be non-negative");
            CHECK(param->rc.zones[i].zoneParam->radl < 0 || param->rc.zones[i].zoneParam->radl > param->rc.zones[i].zoneParam->bframes,
                "Zonefile radl must be between 0 and the configured bframes");
            CHECK(param->rc.zones[i].zoneParam->rc.bitrate < 0,
                "Zonefile bitrate must be non-negative");
            CHECK(param->rc.zones[i].zoneParam->rc.vbvMaxBitrate < 0,
                "Zonefile vbv-maxrate must be non-negative");
            if (!param->bResetZoneConfig)
            {
                CHECK(param->rc.zones[i].startFrame % param->reconfigWindowSize != 0,
                    "Zonefile start frames must align with the reconfig window size");
            }
            if (i > 0)
            {
                CHECK(param->rc.zones[i - 1].startFrame >= param->rc.zones[i].startFrame,
                    "Zonefile start frames must be strictly increasing");
                if (param->bResetZoneConfig)
                {
                    int prevEffectiveStart = param->rc.zones[i - 1].startFrame;
                    prevEffectiveStart += prevEffectiveStart ? param->rc.zones[i - 1].zoneParam->radl : 0;
                    int effectiveStart = param->rc.zones[i].startFrame;
                    effectiveStart += effectiveStart ? param->rc.zones[i].zoneParam->radl : 0;
                    CHECK(prevEffectiveStart >= effectiveStart,
                        "Zonefile effective start frames must be strictly increasing");
                }
            }
        }
    }
    CHECK(strlen(param->analysisSave) && (param->analysisSaveReuseLevel < 0 || param->analysisSaveReuseLevel > 10),
        "Invalid analysis save refine level. Value must be between 1 and 10 (inclusive)");
    CHECK(strlen(param->analysisLoad) && (param->analysisLoadReuseLevel < 0 || param->analysisLoadReuseLevel > 10),
        "Invalid analysis load refine level. Value must be between 1 and 10 (inclusive)");
    CHECK(param->bAnalysisType == AVC_INFO && (strlen(param->analysisSave) || strlen(param->analysisLoad)),
        "AVC analysis refinement expects API-supplied analysis data and cannot be combined with analysis save/load files");
    CHECK(strlen(param->analysisLoad) && (param->mvRefine < 1 || param->mvRefine > 3),
        "Invalid mv refinement level. Value must be between 1 and 3 (inclusive)");
    CHECK(param->scaleFactor < 0 || param->scaleFactor > 2, "Invalid scale-factor. Supports factor between 0 and 2");
    CHECK(param->rc.qpMax < QP_MIN || param->rc.qpMax > QP_MAX_MAX,
        "qpmax exceeds supported range (0 to 69)");
    CHECK(param->rc.qpMin < QP_MIN || param->rc.qpMin > QP_MAX_MAX,
        "qpmin exceeds supported range (0 to 69)");
    CHECK(param->log2MaxPocLsb < 4 || param->log2MaxPocLsb > 16,
        "Supported range for log2MaxPocLsb is 4 to 16");
    CHECK(param->bCTUInfo < 0 || (param->bCTUInfo != 0 && param->bCTUInfo != 1 && param->bCTUInfo != 2 && param->bCTUInfo != 4 && param->bCTUInfo != 6) || param->bCTUInfo > 6,
        "Supported values for bCTUInfo are 0, 1, 2, 4, 6");
    CHECK(param->interRefine > 3 || param->interRefine < 0,
        "Invalid refine-inter value, refine-inter levels 0 to 3 supported");
    CHECK(param->intraRefine > 4 || param->intraRefine < 0,
        "Invalid refine-intra value, refine-intra levels 0 to 3 supported");
    CHECK(param->ctuDistortionRefine < 0 || param->ctuDistortionRefine > 1,
        "Invalid refine-ctu-distortion value, must be either 0 or 1");
    CHECK(param->maxAUSizeFactor < 0.5 || param->maxAUSizeFactor > 1.0,
        "Supported factor for controlling max AU size is from 0.5 to 1");
    CHECK((param->dolbyProfile != 0) && (param->dolbyProfile != 50) && (param->dolbyProfile != 81) && (param->dolbyProfile != 82) && (param->dolbyProfile != 84),
        "Unsupported Dolby Vision profile, only profile 5, profile 8.1, profile 8.2 and profile 8.4 enabled");
    CHECK(param->dupThreshold < 1 || 99 < param->dupThreshold,
        "Invalid frame-duplication threshold. Value must be between 1 and 99.");
    if (param->dolbyProfile)
    {
        CHECK((param->rc.vbvMaxBitrate <= 0 || param->rc.vbvBufferSize <= 0), "Dolby Vision requires VBV settings to enable HRD.\n");
        CHECK((param->internalBitDepth != 10), "Dolby Vision profile - 5, profile - 8.1, profile - 8.2 and profile - 8.4 are Main10 only\n");
        CHECK((param->internalCsp != X265_CSP_I420), "Dolby Vision profile - 5, profile - 8.1, profile - 8.2 and profile - 8.4 requires YCbCr 4:2:0 color space\n");
        if (param->dolbyProfile == 81)
            CHECK(param->masteringDisplayColorVolume[0] == 0, "Dolby Vision profile - 8.1 requires Mastering display color volume information\n");
    }
    if (param->bField && param->interlaceMode)
    {
        CHECK( (param->bFrameAdaptive==0), "Adaptive B-frame decision method should be closed for field feature.\n" );
        // to do
    }
    CHECK(param->selectiveSAO < 0 || param->selectiveSAO > 4,
        "Invalid SAO tune level. Value must be between 0 and 4 (inclusive)");
    if (param->bEnableSceneCutAwareQp)
    {
        if (!param->rc.bStatRead)
        {
            param->bEnableSceneCutAwareQp = 0;
            x265_log(param, X265_LOG_WARNING, "Disabling Scenecut Aware Frame Quantizer Selection since it works only in pass 2\n");
        }
        else
        {
            CHECK(param->bEnableSceneCutAwareQp < 0 || param->bEnableSceneCutAwareQp > 3,
            "Invalid masking direction. Value must be between 0 and 3(inclusive)");
            for (int i = 0; i < 6; i++)
            {
                CHECK(param->fwdScenecutWindow[i] < 0 || param->fwdScenecutWindow[i] > 1000,
                    "Invalid forward scenecut Window duration. Value must be between 0 and 1000(inclusive)");
                CHECK(param->fwdRefQpDelta[i] < 0 || param->fwdRefQpDelta[i] > 20,
                    "Invalid fwdRefQpDelta value. Value must be between 0 and 20 (inclusive)");
                CHECK(param->fwdNonRefQpDelta[i] < 0 || param->fwdNonRefQpDelta[i] > 20,
                    "Invalid fwdNonRefQpDelta value. Value must be between 0 and 20 (inclusive)");

                CHECK(param->bwdScenecutWindow[i] < 0 || param->bwdScenecutWindow[i] > 1000,
                    "Invalid backward scenecut Window duration. Value must be between 0 and 1000(inclusive)");
                CHECK(param->bwdRefQpDelta[i] < -1 || param->bwdRefQpDelta[i] > 20,
                    "Invalid bwdRefQpDelta value. Value must be between 0 and 20 (inclusive)");
                CHECK(param->bwdNonRefQpDelta[i] < -1 || param->bwdNonRefQpDelta[i] > 20,
                    "Invalid bwdNonRefQpDelta value. Value must be between 0 and 20 (inclusive)");
            }
        }
    }
    if (param->bEnableHME)
    {
        for (int level = 0; level < 3; level++)
            CHECK(param->hmeRange[level] < 0 || param->hmeRange[level] >= 32768,
                "Search Range for HME levels must be between 0 and 32768");
    }
#if !X86_64 && !X265_ARCH_ARM64 && !X265_ARCH_RISCV64
    CHECK(param->searchMethod == X265_SEA && (param->sourceWidth > 840 || param->sourceHeight > 480),
        "SEA motion search does not support resolutions greater than 480p in 32 bit build");
#endif

    if (strlen(param->masteringDisplayColorVolume) || param->maxFALL || param->maxCLL)
        param->bEmitHDR10SEI = 1;

    bool isSingleSEI = (param->bRepeatHeaders
                     || param->bEmitHRDSEI
                     || param->bEmitInfoSEI
                     || param->bEmitHDR10SEI
                     || param->bEmitIDRRecoverySEI
                   || param->interlaceMode != 0
                     || param->preferredTransferCharacteristics > 1
                     || strlen(param->toneMapFile)
                     || strlen(param->naluFile));

    if (!isSingleSEI && param->bSingleSeiNal)
    {
        param->bSingleSeiNal = 0;
        x265_log(param, X265_LOG_WARNING, "None of the SEI messages are enabled. Disabling Single SEI NAL\n");
    }
    CHECK(param->confWinRightOffset < 0, "Conformance Window Right Offset must be 0 or greater");
    CHECK(param->confWinBottomOffset < 0, "Conformance Window Bottom Offset must be 0 or greater");
    CHECK(param->decoderVbvMaxRate < 0, "Invalid Decoder Vbv Maxrate. Value can not be less than zero");
    if (param->bliveVBV2pass)
    {
        CHECK((param->rc.bStatRead == 0), "Live VBV in multi pass option requires rate control 2 pass to be enabled");
        if ((param->rc.vbvMaxBitrate <= 0 || param->rc.vbvBufferSize <= 0))
        {
            param->bliveVBV2pass = 0;
            x265_log(param, X265_LOG_WARNING, "Live VBV enabled without VBV settings.Disabling live VBV in 2 pass\n");
        }
    }
    CHECK(param->rc.dataShareMode != X265_SHARE_MODE_FILE && param->rc.dataShareMode != X265_SHARE_MODE_SHAREDMEM, "Invalid data share mode. It must be one of the X265_DATA_SHARE_MODES enum values\n" );
    const int expectedNumLayers = param->numViews > 1 ? param->numViews : (param->numScalableLayers > 1) ? param->numScalableLayers : 1;
    CHECK(param->numScalableLayers < 1, "numScalableLayers must be at least 1");
#if ENABLE_ALPHA
    CHECK(param->numScalableLayers > MAX_SCALABLE_LAYERS, "Alpha encoding currently support only 2 scalable layers");
#else
    CHECK(param->numScalableLayers > MAX_SCALABLE_LAYERS, "Alpha encoding is unsupported in this build");
#endif
    CHECK(param->numViews < 1, "numViews must be at least 1");
#if ENABLE_MULTIVIEW
    CHECK(param->numViews > MAX_VIEWS, "Multi-View Encoding currently support only 2 views");
#else
    CHECK(param->numViews > MAX_VIEWS, "Multi-View Encoding is unsupported in this build");
#endif
    CHECK(param->numViews > 1 && param->numScalableLayers > 1, "Alpha and Multi-View cannot be enabled together in this build");
#if ENABLE_ALPHA || ENABLE_MULTIVIEW
    CHECK(expectedNumLayers > MAX_LAYERS, "Derived layered encoding configuration exceeds this build");
#else
    CHECK(expectedNumLayers > MAX_LAYERS, "Layered encoding is unsupported in this build");
#endif
    param->numLayers = expectedNumLayers;
#if ENABLE_ALPHA
    if (param->bEnableAlpha)
    {
        CHECK(param->numScalableLayers != MAX_SCALABLE_LAYERS, "Alpha encoding requires exactly 2 scalable layers");
        CHECK((param->internalCsp != X265_CSP_I420), "Alpha encode supported only with i420a colorspace");
        CHECK((param->internalBitDepth > 10), "BitDepthConstraint must be 8 and 10  for Scalable main profile");
        CHECK((param->analysisMultiPassDistortion || param->analysisMultiPassRefine), "Alpha encode doesnot support multipass feature");
        CHECK((strlen(param->analysisSave) || strlen(param->analysisLoad)), "Alpha encode doesnot support analysis save and load  feature");
    }
    CHECK(param->numScalableLayers > 1 && !param->bEnableAlpha, "Multiple scalable layers require alpha encoding");
#else
    CHECK(param->bEnableAlpha, "Alpha encoding is unsupported in this build");
#endif
#if ENABLE_MULTIVIEW
    CHECK((param->numViews < 1), "Multi-View Encoding requires at least one view");
    CHECK((param->numViews > 2), "Multi-View Encoding currently support only 2 views");
    CHECK((param->format < 0 || param->format > 2), "Multi-View input format must be 0 (normal), 1 (side-by-side), or 2 (over-under)");
    CHECK(param->format && param->numViews <= 1, "Multi-View input format requires more than one view");
    if (param->numViews > 1)
    {
        CHECK(param->internalBitDepth != 8, "BitDepthConstraint must be 8 for Multiview main profile");
        CHECK(param->analysisMultiPassDistortion || param->analysisMultiPassRefine, "Multiview encode doesnot support multipass feature");
        CHECK(strlen(param->analysisSave) || strlen(param->analysisLoad), "Multiview encode doesnot support analysis save and load feature");
        CHECK(param->isAbrLadderEnable, "Multiview encode and Abr-Ladder feature can't be enabled together");
    }
#else
    CHECK(param->format, "Multi-View input format is unsupported in this build");
#endif
#if ENABLE_SCC_EXT
    bool checkValid = false;

    if (param->bEnableSCC != 0)
    {
        checkValid = param->keyframeMax <= 1 || param->totalFrames == 1;
        if (checkValid)     x265_log(param, X265_LOG_WARNING, "intra constraint flag must be 0 for SCC profiles. Disabling SCC  \n");
        checkValid = param->totalFrames == 1;
        if (checkValid)     x265_log(param, X265_LOG_WARNING, "one-picture-only constraint flag shall be 0 for SCC profiles. Disabling SCC  \n");
        const uint32_t bitDepthIdx = (param->internalBitDepth == 8 ? 0 : (param->internalBitDepth == 10 ? 1 : (param->internalBitDepth == 12 ? 2 : (param->internalBitDepth == 16 ? 3 : 4))));
        const uint32_t chromaFormatIdx = uint32_t(param->internalCsp);
        checkValid = !((bitDepthIdx > 2 || chromaFormatIdx > 3) ? false : (validSCCProfileNames[0][bitDepthIdx][chromaFormatIdx] != NONE));
        if (checkValid)     x265_log(param, X265_LOG_WARNING, "Invalid intra constraint flag, bit depth constraint flag and chroma format constraint flag combination for a RExt profile. Disabling SCC \n");
        if (checkValid)
            param->bEnableSCC = 0;
    }
    if (param->bEnableSCC != 0)
    {
        if (param->bEnableRdRefine && param->bDynamicRefine)
        {
            param->bEnableRdRefine = 0;
            x265_log(param, X265_LOG_WARNING, "Disabling rd-refine as it can not be used with scc and dynamic-refine\n");
        }
        if (param->bEnableRdRefine && param->interRefine > 0)
        {
            param->bEnableRdRefine = 0;
            x265_log(param, X265_LOG_WARNING, "Disabling rd-refine as it can not be used with scc and inter-refine\n");
        }
    }
    CHECK(param->bEnableSCC != 0 && param->rdLevel != 6, "Enabling scc extension in x265 requires rdlevel of 6 ");
#endif

    if (param->rc.hevcAq && param->rc.aqMode != X265_AQ_NONE)
    {
        x265_log(param, X265_LOG_WARNING,
            "--hevc-aq is enabled, --aq-mode %d will be ignored. hevcAq uses its own AQ method.\n",
            param->rc.aqMode);
    }

    if (param->rc.cuTree && param->rc.qScaleMode == 2)
    {
        x265_log(param, X265_LOG_WARNING,
            "--qscale-mode 2 (complexity-based) overrides --cuTree frame duration estimation.\n"
            "cuTree QP offsets will still apply, but rate control qScale calculation changes.\n");
    }

    if (param->rc.limitAq1 && param->rc.aqMode < X265_AQ_AUTO_VARIANCE)
    {
        x265_log(param, X265_LOG_WARNING,
            "--limit-aq1 has no effect with --aq-mode %d. "
            "It only applies to AQ modes 2, 3, 4, and 5.\n",
            param->rc.aqMode);
        param->rc.limitAq1 = 0;
    }

    if (param->rc.limitAq1 && param->rc.hevcAq)
    {
        x265_log(param, X265_LOG_WARNING,
            "--limit-aq1 is incompatible with --hevc-aq. Disabling limit-aq1.\n");
        param->rc.limitAq1 = 0;
    }

    double expectedCuTreeStrength = (param->rc.hevcAq ? 6.0 : 5.0) * (1.0 - param->rc.qCompress);
    if (param->rc.cuTree && (param->rc.cuTreeStrength - expectedCuTreeStrength > 0.01 ||
        expectedCuTreeStrength - param->rc.cuTreeStrength > 0.01))
    {
        x265_log(param, X265_LOG_INFO,
            "cuTreeStrength=%.2f (qcomp=%.2f suggests %.2f). "
            "This is normal if you set --cutree-strength explicitly.\n",
            param->rc.cuTreeStrength, param->rc.qCompress, expectedCuTreeStrength);
    }

    return check_failed;
}

void x265_param_apply_fastfirstpass(x265_param* param)
{
    if (!param)
    {
        x265_log(nullptr, X265_LOG_ERROR, "x265_param_apply_fastfirstpass requires a non-null parameter struct\n");
        return;
    }

    /* Set faster options in case of turbo firstpass */
    if (param->rc.bStatWrite && !param->rc.bStatRead)
    {
        param->maxNumReferences = 1;
        param->maxNumMergeCand = 1;
        param->bEnableRectInter = 0;
        param->bEnableFastIntra = 1;
        param->bEnableAMP = 0;
        param->searchMethod = X265_DIA_SEARCH;
        param->subpelRefine = X265_MIN(2, param->subpelRefine);
        param->bEnableEarlySkip = 1;
        param->rdLevel = X265_MIN(2, param->rdLevel);
    }
}

static void appendtool(x265_param* param, char* buf, size_t size, const char* toolstr)
{
    static const int overhead = (int)strlen("x265 [info]: tools: ");

    if (strlen(buf) + strlen(toolstr) + overhead >= size)
    {
        x265_log(param, X265_LOG_INFO, "tools:%s\n", buf);
        snprintf(buf, size, " %s", toolstr);
    }
    else
    {
        size_t used = strlen(buf);
        snprintf(buf + used, size - used, " %s", toolstr);
    }
}

void x265_print_params(x265_param* param)
{
    if (!param)
    {
        x265_log(nullptr, X265_LOG_ERROR, "x265_print_params requires a non-null parameter struct\n");
        return;
    }

    if (param->logLevel < X265_LOG_INFO)
        return;

    if (param->interlaceMode)
        x265_log(param, X265_LOG_INFO, "Interlaced field inputs             : %s\n", x265_interlace_names[param->interlaceMode]);

    x265_log(param, X265_LOG_INFO, "Coding QT: max CU size, min CU size : %d / %d\n", param->maxCUSize, param->minCUSize);

    if (param->bThreadedME)
        x265_log(param, X265_LOG_INFO, "ThreadedME: task block / buf rows   : %d / %d\n", param->tmeTaskBlockSize, param->tmeNumBufferRows);

    x265_log(param, X265_LOG_INFO, "Residual QT: max TU size, max depth : %d / %d inter / %d intra\n",
             param->maxTUSize, param->tuQTMaxInterDepth, param->tuQTMaxIntraDepth);

    if (param->bEnableHME)
        x265_log(param, X265_LOG_INFO, "HME L0,1,2 / range / subpel / merge : %s, %s, %s / %d / %d / %d\n",
            x265_motion_est_names[param->hmeSearchMethod[0]], x265_motion_est_names[param->hmeSearchMethod[1]], x265_motion_est_names[param->hmeSearchMethod[2]], param->searchRange, param->subpelRefine, param->maxNumMergeCand);
    else
        x265_log(param, X265_LOG_INFO, "ME / range / subpel / merge         : %s / %d / %d / %d\n",
            x265_motion_est_names[param->searchMethod], param->searchRange, param->subpelRefine, param->maxNumMergeCand);

    if (param->scenecutThreshold && param->keyframeMax != INT_MAX) 
        x265_log(param, X265_LOG_INFO, "Keyframe min / max / scenecut / bias  : %d / %d / %d / %.2lf \n",
                 param->keyframeMin, param->keyframeMax, param->scenecutThreshold, param->scenecutBias * 100);
    else if (param->bHistBasedSceneCut && param->keyframeMax != INT_MAX) 
        x265_log(param, X265_LOG_INFO, "Keyframe min / max / scenecut  : %d / %d / %d\n",
                 param->keyframeMin, param->keyframeMax, param->bHistBasedSceneCut);
    else if (param->keyframeMax == INT_MAX)
        x265_log(param, X265_LOG_INFO, "Keyframe min / max / scenecut       : disabled\n");

    if (param->cbQpOffset || param->crQpOffset)
        x265_log(param, X265_LOG_INFO, "Cb/Cr QP Offset                     : %d / %d\n", param->cbQpOffset, param->crQpOffset);

    if (param->rdPenalty)
        x265_log(param, X265_LOG_INFO, "Intra 32x32 TU penalty type         : %d\n", param->rdPenalty);

    x265_log(param, X265_LOG_INFO, "Lookahead / bframes / badapt        : %d / %d / %d\n", param->lookaheadDepth, param->bframes, param->bFrameAdaptive);
    x265_log(param, X265_LOG_INFO, "b-pyramid / weightp / weightb       : %d / %d / %d\n",
             param->bBPyramid, param->bEnableWeightedPred, param->bEnableWeightedBiPred);
    x265_log(param, X265_LOG_INFO, "References / ref-limit  cu / depth  : %d / %s / %s\n",
             param->maxNumReferences, (param->limitReferences & X265_REF_LIMIT_CU) ? "on" : "off",
             (param->limitReferences & X265_REF_LIMIT_DEPTH) ? "on" : "off");

    if (param->rc.aqMode)
        x265_log(param, X265_LOG_INFO, "AQ: mode / str / qg-size / cu-tree  : %d / %0.1f / %d / %d\n", param->rc.aqMode,
                 param->rc.aqStrength, param->rc.qgSize, param->rc.cuTree);

    if (param->bLossless)
        x265_log(param, X265_LOG_INFO, "Rate Control                        : Lossless\n");
    else switch (param->rc.rateControlMode)
    {
    case X265_RC_ABR:
        x265_log(param, X265_LOG_INFO, "Rate Control / qCompress            : ABR-%d kbps / %0.2f\n", param->rc.bitrate, param->rc.qCompress); break;
    case X265_RC_CQP:
        x265_log(param, X265_LOG_INFO, "Rate Control                        : CQP-%d\n", param->rc.qp); break;
    case X265_RC_CRF:
        x265_log(param, X265_LOG_INFO, "Rate Control / qCompress            : CRF-%0.1f / %0.2f\n", param->rc.rfConstant, param->rc.qCompress); break;
    }

    if (param->rc.vbvBufferSize)
    {
        if (param->vbvBufferEnd)
            x265_log(param, X265_LOG_INFO, "VBV/HRD buffer / max-rate / init / end / fr-adj: %d / %d / %.3f / %.3f / %.3f\n",
            param->rc.vbvBufferSize, param->rc.vbvMaxBitrate, param->rc.vbvBufferInit, param->vbvBufferEnd, param->vbvEndFrameAdjust);
        else
            x265_log(param, X265_LOG_INFO, "VBV/HRD buffer / max-rate / init    : %d / %d / %.3f\n",
            param->rc.vbvBufferSize, param->rc.vbvMaxBitrate, param->rc.vbvBufferInit);
    }
    
    char buf[80] = { 0 };
    char tmp[40];
#define TOOLOPT(FLAG, STR) if (FLAG) appendtool(param, buf, sizeof(buf), STR);
#define TOOLVAL(VAL, STR)  if (VAL) { snprintf(tmp, sizeof(tmp), STR, VAL); appendtool(param, buf, sizeof(buf), tmp); }
    TOOLOPT(param->bEnableRectInter, "rect");
    TOOLOPT(param->bEnableAMP, "amp");
    TOOLOPT(param->limitModes, "limit-modes");
    TOOLVAL(param->rdLevel, "rd=%d");
    TOOLVAL(param->dynamicRd, "dynamic-rd=%.2f");
    TOOLOPT(param->bSsimRd, "ssim-rd");
    TOOLVAL(param->psyRd, "psy-rd=%.2lf");
    TOOLVAL(param->rdoqLevel, "rdoq=%d");
    TOOLVAL(param->psyRdoq, "psy-rdoq=%.2lf");
    TOOLOPT(param->bEnableRdRefine, "rd-refine");
    TOOLOPT(param->bEnableEarlySkip, "early-skip");
    TOOLVAL(param->recursionSkipMode, "rskip mode=%d");
    if (param->recursionSkipMode == EDGE_BASED_RSKIP)
        TOOLVAL(param->edgeVarThreshold, "rskip-edge-threshold=%.2f");
    TOOLOPT(param->bEnableSplitRdSkip, "splitrd-skip");
    TOOLVAL(param->noiseReductionIntra, "nr-intra=%d");
    TOOLVAL(param->noiseReductionInter, "nr-inter=%d");
    TOOLOPT(param->bEnableTSkipFast, "tskip-fast");
    TOOLOPT(!param->bEnableTSkipFast && param->bEnableTransformSkip, "tskip");
    TOOLVAL(param->limitTU , "limit-tu=%d");
    TOOLOPT(param->bCULossless, "cu-lossless");
    TOOLOPT(param->bEnableSignHiding, "signhide");
    TOOLOPT(param->bEnableTemporalMvp, "tmvp");
    TOOLOPT(param->bEnableConstrainedIntra, "constrained-intra");
    TOOLOPT(param->bIntraInBFrames, "b-intra");
    TOOLOPT(param->bEnableFastIntra, "fast-intra");
    TOOLOPT(param->bEnableStrongIntraSmoothing, "strong-intra-smoothing");
    TOOLVAL(param->lookaheadSlices, "lslices=%d");
    TOOLVAL(param->lookaheadThreads, "lthreads=%d")
    TOOLVAL(param->bCTUInfo, "ctu-info=%d");
    if (param->bAnalysisType == AVC_INFO)
    {
        TOOLOPT(param->bAnalysisType, "refine-analysis-type=avc");
    }
    else if (param->bAnalysisType == HEVC_INFO)
        TOOLOPT(param->bAnalysisType, "refine-analysis-type=hevc");
    TOOLOPT(param->bDynamicRefine, "dynamic-refine");
    if (param->maxSlices > 1)
        TOOLVAL(param->maxSlices, "slices=%d");
    if (param->bEnableLoopFilter)
    {
        if (param->deblockingFilterBetaOffset || param->deblockingFilterTCOffset)
        {
            snprintf(tmp, sizeof(tmp), "deblock(tC=%d:B=%d)", param->deblockingFilterTCOffset, param->deblockingFilterBetaOffset);
            appendtool(param, buf, sizeof(buf), tmp);
        }
        else
            TOOLOPT(param->bEnableLoopFilter, "deblock");
    }
    TOOLOPT(param->bSaoNonDeblocked, "sao-non-deblock");
    TOOLOPT(!param->bSaoNonDeblocked && param->bEnableSAO, "sao");
    if (param->selectiveSAO && param->selectiveSAO != 4)
        TOOLOPT(param->selectiveSAO, "selective-sao");
    TOOLOPT(param->rc.bStatWrite, "stats-write");
    TOOLOPT(param->rc.bStatRead,  "stats-read");
    TOOLOPT(param->bSingleSeiNal, "single-sei");
#if ENABLE_ALPHA
    TOOLOPT(param->numScalableLayers > 1, "alpha");
#endif
#if ENABLE_MULTIVIEW
    TOOLOPT(param->numViews > 1, "multi-view");
#endif
#if ENABLE_HDR10_PLUS
    TOOLOPT(param->toneMapFile[0] != '\0', "dhdr10-info");
#endif
    if(param->bEnableTemporalFilter)
        TOOLOPT(param->bEnableTemporalFilter, "mcstf");
    x265_log(param, X265_LOG_INFO, "tools:%s\n", buf);
    fflush(stderr);
}

char *x265_param2string(x265_param* p, int padx, int pady)
{
    char *buf, *s;
    size_t bufSize = 4001 + p->rc.zoneCount * 64;
    if (strlen(p->numaPools))
        bufSize += strlen(p->numaPools);
    if (strlen(p->masteringDisplayColorVolume))
        bufSize += strlen(p->masteringDisplayColorVolume);
    if (strlen(p->videoSignalTypePreset))
        bufSize += strlen(p->videoSignalTypePreset);
    if (p->logfn)
        bufSize += strlen(p->logfn);
    if (p->pgfn)
        bufSize += strlen(p->pgfn);
    if (p->filmGrain)
        bufSize += strlen(p->filmGrain);
    if (p->aomFilmGrain)
        bufSize += strlen(p->aomFilmGrain);

    buf = s = X265_MALLOC(char, bufSize);
    if (!buf)
        return nullptr;
#define BOOL(param, cliopt) \
    s += snprintf(s, bufSize - (s - buf), " %s", (param) ? cliopt : "no-" cliopt);

    s += snprintf(s, bufSize - (s - buf), "cpuid=%d", p->cpuid);
    s += snprintf(s, bufSize - (s - buf), " frame-threads=%d", p->frameNumThreads);
    if (strlen(p->numaPools))
        s += snprintf(s, bufSize - (s - buf), " numa-pools=%s", p->numaPools);
    BOOL(p->bEnableWavefront, "wpp");
    BOOL(p->bDistributeModeAnalysis, "pmode");
    BOOL(p->bDistributeMotionEstimation, "pme");
    BOOL(p->bEnablePsnr, "psnr");
    BOOL(p->bEnableSsim, "ssim");
    s += snprintf(s, bufSize - (s - buf), " log-level=%d", p->logLevel);
    if (p->logfn)
        s += snprintf(s, bufSize - (s - buf), " log-file=%s log-file-level=%d", p->logfn, p->logfLevel);
    if (p->pgfn)
        s += snprintf(s, bufSize - (s - buf), " progress-file=%s", p->pgfn);
    if (strlen(p->csvfn))
        s += snprintf(s, bufSize - (s - buf), " csv csv-log-level=%d", p->csvLogLevel);
    s += snprintf(s, bufSize - (s - buf), " bitdepth=%d", p->internalBitDepth);
    s += snprintf(s, bufSize - (s - buf), " input-csp=%d", p->internalCsp);
    s += snprintf(s, bufSize - (s - buf), " fps=%u/%u", p->fpsNum, p->fpsDenom);
    s += snprintf(s, bufSize - (s - buf), " input-res=%dx%d", p->sourceWidth - padx, p->sourceHeight - pady);
    s += snprintf(s, bufSize - (s - buf), " interlace=%d", p->interlaceMode);
    s += snprintf(s, bufSize - (s - buf), " total-frames=%d", p->totalFrames);
    if (p->chunkStart)
        s += snprintf(s, bufSize - (s - buf), " chunk-start=%d", p->chunkStart);
    if (p->chunkEnd)
        s += snprintf(s, bufSize - (s - buf), " chunk-end=%d", p->chunkEnd);
    s += snprintf(s, bufSize - (s - buf), " level-idc=%d", p->levelIdc);
    s += snprintf(s, bufSize - (s - buf), " high-tier=%d", p->bHighTier);
    s += snprintf(s, bufSize - (s - buf), " uhd-bd=%d", p->uhdBluray);
    s += snprintf(s, bufSize - (s - buf), " ref=%d", p->maxNumReferences);
    BOOL(p->bAllowNonConformance, "allow-non-conformance");
    BOOL(p->bRepeatHeaders, "repeat-headers");
    BOOL(p->bAnnexB, "annexb");
    BOOL(p->bEnableAccessUnitDelimiters, "aud");
    BOOL(p->bEnableEndOfBitstream, "eob");
    BOOL(p->bEnableEndOfSequence, "eos");
    BOOL(p->bEmitHRDSEI, "hrd");
    BOOL(p->bEmitInfoSEI, "info");
    s += snprintf(s, bufSize - (s - buf), " hash=%d", p->decodedPictureHashSEI);
    s += snprintf(s, bufSize - (s - buf), " temporal-layers=%d", p->bEnableTemporalSubLayers);
    BOOL(p->bOpenGOP, "open-gop");
    s += snprintf(s, bufSize - (s - buf), " min-keyint=%d", p->keyframeMin);
    s += snprintf(s, bufSize - (s - buf), " keyint=%d", p->keyframeMax);
    s += snprintf(s, bufSize - (s - buf), " gop-lookahead=%d", p->gopLookahead);
    s += snprintf(s, bufSize - (s - buf), " bframes=%d", p->bframes);
    s += snprintf(s, bufSize - (s - buf), " b-adapt=%d", p->bFrameAdaptive);
    BOOL(p->bBPyramid, "b-pyramid");
    s += snprintf(s, bufSize - (s - buf), " bframe-bias=%d", p->bFrameBias);
    s += snprintf(s, bufSize - (s - buf), " rc-lookahead=%d", p->lookaheadDepth);
    s += snprintf(s, bufSize - (s - buf), " lookahead-slices=%d", p->lookaheadSlices);
    s += snprintf(s, bufSize - (s - buf), " scenecut=%d", p->scenecutThreshold);
    BOOL(p->bHistBasedSceneCut, "hist-scenecut");
    s += snprintf(s, bufSize - (s - buf), " radl=%d", p->radl);
    BOOL(p->bEnableHRDConcatFlag, "splice");
    BOOL(p->bIntraRefresh, "intra-refresh");
    s += snprintf(s, bufSize - (s - buf), " ctu=%d", p->maxCUSize);
    s += snprintf(s, bufSize - (s - buf), " min-cu-size=%d", p->minCUSize);
    BOOL(p->bEnableRectInter, "rect");
    BOOL(p->bEnableAMP, "amp");
    s += snprintf(s, bufSize - (s - buf), " max-tu-size=%d", p->maxTUSize);
    s += snprintf(s, bufSize - (s - buf), " tu-inter-depth=%d", p->tuQTMaxInterDepth);
    s += snprintf(s, bufSize - (s - buf), " tu-intra-depth=%d", p->tuQTMaxIntraDepth);
    s += snprintf(s, bufSize - (s - buf), " limit-tu=%d", p->limitTU);
    s += snprintf(s, bufSize - (s - buf), " rdoq-level=%d", p->rdoqLevel);
    s += snprintf(s, bufSize - (s - buf), " dynamic-rd=%.2f", p->dynamicRd);
    BOOL(p->bSsimRd, "ssim-rd");
    BOOL(p->bEnableSignHiding, "signhide");
    BOOL(p->bEnableTransformSkip, "tskip");
    s += snprintf(s, bufSize - (s - buf), " nr-intra=%d", p->noiseReductionIntra);
    s += snprintf(s, bufSize - (s - buf), " nr-inter=%d", p->noiseReductionInter);
    BOOL(p->bEnableConstrainedIntra, "constrained-intra");
    BOOL(p->bEnableStrongIntraSmoothing, "strong-intra-smoothing");
    s += snprintf(s, bufSize - (s - buf), " max-merge=%d", p->maxNumMergeCand);
    s += snprintf(s, bufSize - (s - buf), " limit-refs=%d", p->limitReferences);
    BOOL(p->limitModes, "limit-modes");
    s += snprintf(s, bufSize - (s - buf), " me=%d", p->searchMethod);
    s += snprintf(s, bufSize - (s - buf), " subme=%d", p->subpelRefine);
    s += snprintf(s, bufSize - (s - buf), " merange=%d", p->searchRange);
    BOOL(p->bEnableTemporalMvp, "temporal-mvp");
    BOOL(p->bEnableFrameDuplication, "frame-dup");
    if(p->bEnableFrameDuplication)
        s += snprintf(s, bufSize - (s - buf), " dup-threshold=%d", p->dupThreshold);
    BOOL(p->bEnableHME, "hme");
    if (p->bEnableHME)
    {
        s += snprintf(s, bufSize - (s - buf), " Level 0,1,2=%d,%d,%d", p->hmeSearchMethod[0], p->hmeSearchMethod[1], p->hmeSearchMethod[2]);
        s += snprintf(s, bufSize - (s - buf), " merange L0,L1,L2=%d,%d,%d", p->hmeRange[0], p->hmeRange[1], p->hmeRange[2]);
    }
    BOOL(p->bEnableWeightedPred, "weightp");
    BOOL(p->bEnableWeightedBiPred, "weightb");
    BOOL(p->bSourceReferenceEstimation, "analyze-src-pics");
    BOOL(p->bEnableLoopFilter, "deblock");
    if (p->bEnableLoopFilter)
        s += snprintf(s, bufSize - (s - buf), "=%d:%d", p->deblockingFilterTCOffset, p->deblockingFilterBetaOffset);
    BOOL(p->bEnableSAO, "sao");
    BOOL(p->bSaoNonDeblocked, "sao-non-deblock");
    s += snprintf(s, bufSize - (s - buf), " rd=%d", p->rdLevel);
    s += snprintf(s, bufSize - (s - buf), " selective-sao=%d", p->selectiveSAO);
    BOOL(p->bEnableEarlySkip, "early-skip");
    BOOL(p->recursionSkipMode, "rskip");
    if (p->recursionSkipMode == EDGE_BASED_RSKIP)
        s += snprintf(s, bufSize - (s - buf), " rskip-edge-threshold=%f", p->edgeVarThreshold);

    BOOL(p->bEnableFastIntra, "fast-intra");
    BOOL(p->bEnableTSkipFast, "tskip-fast");
    BOOL(p->bCULossless, "cu-lossless");
    BOOL(p->bIntraInBFrames, "b-intra");
    BOOL(p->bEnableSplitRdSkip, "splitrd-skip");
    s += snprintf(s, bufSize - (s - buf), " rdpenalty=%d", p->rdPenalty);
    s += snprintf(s, bufSize - (s - buf), " psy-rd=%.2f", p->psyRd);
    s += snprintf(s, bufSize - (s - buf), " psy-rdoq=%.2f", p->psyRdoq);
    s += snprintf(s, bufSize - (s - buf), " psy-bscale=%d", p->psyScaleB);
    s += snprintf(s, bufSize - (s - buf), " psy-pscale=%d", p->psyScaleP);
    s += snprintf(s, bufSize - (s - buf), " psy-iscale=%d", p->psyScaleI);
    BOOL(p->bEnableRdRefine, "rd-refine");
    BOOL(p->bLossless, "lossless");
    s += snprintf(s, bufSize - (s - buf), " cbqpoffs=%d", p->cbQpOffset);
    s += snprintf(s, bufSize - (s - buf), " crqpoffs=%d", p->crQpOffset);
    s += snprintf(s, bufSize - (s - buf), " rc=%s", p->rc.rateControlMode == X265_RC_ABR ? (
         p->rc.bitrate == p->rc.vbvMaxBitrate ? "cbr" : "abr")
         : p->rc.rateControlMode == X265_RC_CRF ? "crf" : "cqp");
    if (p->rc.rateControlMode == X265_RC_ABR || p->rc.rateControlMode == X265_RC_CRF)
    {
        if (p->rc.rateControlMode == X265_RC_CRF)
            s += snprintf(s, bufSize - (s - buf), " crf=%.1f", p->rc.rfConstant);
        else
            s += snprintf(s, bufSize - (s - buf), " bitrate=%d", p->rc.bitrate);
        s += snprintf(s, bufSize - (s - buf), " qcomp=%.2f qpstep=%d", p->rc.qCompress, p->rc.qpStep);
        s += snprintf(s, bufSize - (s - buf), " stats-write=%d", p->rc.bStatWrite);
        s += snprintf(s, bufSize - (s - buf), " stats-read=%d", p->rc.bStatRead);
        if (p->rc.bStatRead)
            s += snprintf(s, bufSize - (s - buf), " cplxblur=%.1f qblur=%.1f",
            p->rc.complexityBlur, p->rc.qblur);
        if (p->rc.bStatWrite && !p->rc.bStatRead)
            BOOL(p->rc.bEnableSlowFirstPass, "slow-firstpass");
        if (p->rc.vbvBufferSize)
        {
            s += snprintf(s, bufSize - (s - buf), " vbv-maxrate=%d vbv-bufsize=%d vbv-init=%.1f min-vbv-fullness=%.1f max-vbv-fullness=%.1f",
                p->rc.vbvMaxBitrate, p->rc.vbvBufferSize, p->rc.vbvBufferInit, p->minVbvFullness, p->maxVbvFullness);
            if (p->vbvBufferEnd)
                s += snprintf(s, bufSize - (s - buf), " vbv-end=%.1f vbv-end-fr-adj=%.1f", p->vbvBufferEnd, p->vbvEndFrameAdjust);
            if (p->rc.rateControlMode == X265_RC_CRF)
                s += snprintf(s, bufSize - (s - buf), " crf-max=%.1f crf-min=%.1f", p->rc.rfConstantMax, p->rc.rfConstantMin);
        }
    }
    else if (p->rc.rateControlMode == X265_RC_CQP)
        s += snprintf(s, bufSize - (s - buf), " qp=%d", p->rc.qp);
    s += snprintf(s, bufSize - (s - buf), " qscale-mode=%d", p->rc.qScaleMode);
    if (!(p->rc.rateControlMode == X265_RC_CQP && p->rc.qp == 0))
    {
        s += snprintf(s, bufSize - (s - buf), " ipratio=%.2f", p->rc.ipFactor);
        if (p->bframes)
            s += snprintf(s, bufSize - (s - buf), " pbratio=%.2f", p->rc.pbFactor);
    }
    s += snprintf(s, bufSize - (s - buf), " aq-mode=%d", p->rc.aqMode);
    BOOL(p->rc.limitAq1, "limit-aq1");
    s += snprintf(s, bufSize - (s - buf), " aq-strength=%.2f", p->rc.aqStrength);
    s += snprintf(s, bufSize - (s - buf), " aq-bias-strength=%.2f", p->rc.aqBiasStrength);
    s += snprintf(s, bufSize - (s - buf), " limit-aq1-strength=%.2f", p->rc.limitAq1Strength);
    BOOL(p->rc.cuTree, "cutree");
    s += snprintf(s, bufSize - (s - buf), " cutree-strength=%.2f", p->rc.cuTreeStrength);
    s += snprintf(s, bufSize - (s - buf), " cutree-minqpoffs=%.2f", p->rc.cuTreeMinQpOffset);
    s += snprintf(s, bufSize - (s - buf), " cutree-maxqpoffs=%.2f", p->rc.cuTreeMaxQpOffset);
    s += snprintf(s, bufSize - (s - buf), " zone-count=%d", p->rc.zoneCount);
    if (p->rc.zoneCount)
    {
        for (int i = 0; i < p->rc.zoneCount; ++i)
        {
            s += snprintf(s, bufSize - (s - buf), " zones: start-frame=%d end-frame=%d",
                 p->rc.zones[i].startFrame, p->rc.zones[i].endFrame);
            if (p->rc.zones[i].bForceQp)
                s += snprintf(s, bufSize - (s - buf), " qp=%d", p->rc.zones[i].qp);
            else
                s += snprintf(s, bufSize - (s - buf), " bitrate-factor=%f", p->rc.zones[i].bitrateFactor);
        }
    }
    BOOL(p->rc.bStrictCbr, "strict-cbr");
    s += snprintf(s, bufSize - (s - buf), " qg-size=%d", p->rc.qgSize);
    BOOL(p->rc.bEnableGrain, "rc-grain");
    s += snprintf(s, bufSize - (s - buf), " qpmax=%d qpmin=%d", p->rc.qpMax, p->rc.qpMin);
    BOOL(p->rc.bEnableConstVbv, "const-vbv");
    s += snprintf(s, bufSize - (s - buf), " sar=%d", p->vui.aspectRatioIdc);
    if (p->vui.aspectRatioIdc == X265_EXTENDED_SAR)
        s += snprintf(s, bufSize - (s - buf), " sar-width : sar-height=%d:%d", p->vui.sarWidth, p->vui.sarHeight);
    s += snprintf(s, bufSize - (s - buf), " overscan=%d", p->vui.bEnableOverscanInfoPresentFlag);
    if (p->vui.bEnableOverscanInfoPresentFlag)
        s += snprintf(s, bufSize - (s - buf), " overscan-crop=%d", p->vui.bEnableOverscanAppropriateFlag);
    s += snprintf(s, bufSize - (s - buf), " videoformat=%d", p->vui.videoFormat);
    s += snprintf(s, bufSize - (s - buf), " range=%d", p->vui.bEnableVideoFullRangeFlag);
    s += snprintf(s, bufSize - (s - buf), " colorprim=%d", p->vui.colorPrimaries);
    s += snprintf(s, bufSize - (s - buf), " transfer=%d", p->vui.transferCharacteristics);
    s += snprintf(s, bufSize - (s - buf), " colormatrix=%d", p->vui.matrixCoeffs);
    s += snprintf(s, bufSize - (s - buf), " chromaloc=%d", p->vui.bEnableChromaLocInfoPresentFlag);
    if (p->vui.bEnableChromaLocInfoPresentFlag)
        s += snprintf(s, bufSize - (s - buf), " chromaloc-top=%d chromaloc-bottom=%d",
        p->vui.chromaSampleLocTypeTopField, p->vui.chromaSampleLocTypeBottomField);
    s += snprintf(s, bufSize - (s - buf), " display-window=%d", p->vui.bEnableDefaultDisplayWindowFlag);
    if (p->vui.bEnableDefaultDisplayWindowFlag)
        s += snprintf(s, bufSize - (s - buf), " left=%d top=%d right=%d bottom=%d",
        p->vui.defDispWinLeftOffset, p->vui.defDispWinTopOffset,
        p->vui.defDispWinRightOffset, p->vui.defDispWinBottomOffset);
    if (strlen(p->masteringDisplayColorVolume))
        s += snprintf(s, bufSize - (s - buf), " master-display=%s", p->masteringDisplayColorVolume);
    if (p->bEmitCLL)
        s += snprintf(s, bufSize - (s - buf), " cll=%hu,%hu", p->maxCLL, p->maxFALL);
    s += snprintf(s, bufSize - (s - buf), " min-luma=%hu", p->minLuma);
    s += snprintf(s, bufSize - (s - buf), " max-luma=%hu", p->maxLuma);
    s += snprintf(s, bufSize - (s - buf), " log2-max-poc-lsb=%d", p->log2MaxPocLsb);
    BOOL(p->bEmitVUITimingInfo, "vui-timing-info");
    BOOL(p->bEmitVUIHRDInfo, "vui-hrd-info");
    s += snprintf(s, bufSize - (s - buf), " slices=%d", p->maxSlices);
    BOOL(p->bOptQpPPS, "opt-qp-pps");
    BOOL(p->bOptRefListLengthPPS, "opt-ref-list-length-pps");
    BOOL(p->bMultiPassOptRPS, "multi-pass-opt-rps");
    s += snprintf(s, bufSize - (s - buf), " scenecut-bias=%.2f", p->scenecutBias);
    BOOL(p->bOptCUDeltaQP, "opt-cu-delta-qp");
    BOOL(p->bAQMotion, "aq-motion");
    BOOL(p->bEmitHDR10SEI, "hdr10");
    BOOL(p->bHDR10Opt, "hdr10-opt");
    BOOL(p->bDhdr10opt, "dhdr10-opt");
    BOOL(p->bStylish, "stylish");
    BOOL(p->bEmitIDRRecoverySEI, "idr-recovery-sei");
    if (strlen(p->analysisSave))
        s += snprintf(s, bufSize - (s - buf), " analysis-save");
    if (strlen(p->analysisLoad))
        s += snprintf(s, bufSize - (s - buf), " analysis-load");
    s += snprintf(s, bufSize - (s - buf), " analysis-save-reuse-level=%d", p->analysisSaveReuseLevel);
    s += snprintf(s, bufSize - (s - buf), " analysis-load-reuse-level=%d", p->analysisLoadReuseLevel);
    s += snprintf(s, bufSize - (s - buf), " scale-factor=%d", p->scaleFactor);
    s += snprintf(s, bufSize - (s - buf), " refine-intra=%d", p->intraRefine);
    s += snprintf(s, bufSize - (s - buf), " refine-inter=%d", p->interRefine);
    s += snprintf(s, bufSize - (s - buf), " refine-mv=%d", p->mvRefine);
    s += snprintf(s, bufSize - (s - buf), " refine-ctu-distortion=%d", p->ctuDistortionRefine);
    BOOL(p->bLimitSAO, "limit-sao");
    s += snprintf(s, bufSize - (s - buf), " ctu-info=%d", p->bCTUInfo);
    BOOL(p->bLowPassDct, "lowpass-dct");
    s += snprintf(s, bufSize - (s - buf), " refine-analysis-type=%d", p->bAnalysisType);
    s += snprintf(s, bufSize - (s - buf), " copy-pic=%d", p->bCopyPicToFrame);
    s += snprintf(s, bufSize - (s - buf), " max-ausize-factor=%.1f", p->maxAUSizeFactor);
    BOOL(p->bDynamicRefine, "dynamic-refine");
    BOOL(p->bSingleSeiNal, "single-sei");
    BOOL(p->rc.hevcAq, "hevc-aq");
    BOOL(p->bEnableSvtHevc, "svt");
    BOOL(p->bField, "field");
    s += snprintf(s, bufSize - (s - buf), " qp-adaptation-range=%.2f", p->rc.qpAdaptationRange);
    s += snprintf(s, bufSize - (s - buf), " scenecut-aware-qp=%d", p->bEnableSceneCutAwareQp);
    if (p->bEnableSceneCutAwareQp)
        s += snprintf(s, bufSize - (s - buf), " fwd-scenecut-window=%d fwd-ref-qp-delta=%f fwd-nonref-qp-delta=%f bwd-scenecut-window=%d bwd-ref-qp-delta=%f bwd-nonref-qp-delta=%f", p->fwdMaxScenecutWindow, p->fwdRefQpDelta[0], p->fwdNonRefQpDelta[0], p->bwdMaxScenecutWindow, p->bwdRefQpDelta[0], p->bwdNonRefQpDelta[0]);
    s += snprintf(s, bufSize - (s - buf), " conformance-window-offsets right=%d bottom=%d", p->confWinRightOffset, p->confWinBottomOffset);
    s += snprintf(s, bufSize - (s - buf), " decoder-max-rate=%d", p->decoderVbvMaxRate);
    BOOL(p->bliveVBV2pass, "vbv-live-multi-pass");
    if (p->filmGrain)
        s += snprintf(s, bufSize - (s - buf), " film-grain=%s", p->filmGrain); // Film grain characteristics model filename
    if (p->aomFilmGrain)
        s += snprintf(s, bufSize - (s - buf), " aom-film-grain=%s", p->aomFilmGrain);
    BOOL(p->bEnableTemporalFilter, "mcstf");
#if ENABLE_ALPHA
    BOOL(p->bEnableAlpha, "alpha");
#endif
#if ENABLE_MULTIVIEW
    s += snprintf(s, bufSize - (s - buf), " num-views=%d", p->numViews);
    s += snprintf(s, bufSize - (s - buf), " format=%d", p->format);
#endif
#if ENABLE_SCC_EXT
    s += snprintf(s, bufSize - (s - buf), "scc=%d", p->bEnableSCC);
#endif
    BOOL(p->bEnableSBRC, "sbrc");
    BOOL(p->bConfigRCFrame, "frame-rc");
#undef BOOL
    return buf;
}

bool parseLambdaFile(x265_param* param)
{
    if (!strlen(param->rc.lambdaFileName))
        return false;

    FILE *lfn = x265_fopen(param->rc.lambdaFileName, "r");
    if (!lfn)
    {
        x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\n", param->rc.lambdaFileName);
        return true;
    }
    else if (ferror(lfn))
    {
        bool closeFailed = ferror(lfn) != 0;
        if (fclose(lfn))
            closeFailed = true;
        if (closeFailed)
            x265_log(param, X265_LOG_WARNING, "unable to close lambda file after open failure\n");
        x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\n", param->rc.lambdaFileName);
        return true;
    }

    char line[2048];
    char *tok = nullptr, *buf = nullptr;
    char *scan = nullptr;

    for (int t = 0; t < 3; t++)
    {
        double *table = t ? x265_lambda2_tab : x265_lambda_tab;

        for (int i = 0; i < QP_MAX_MAX + 1; i++)
        {
            double value;

            do
            {
                if (!tok)
                {
                    /* consume a line of text file */
                    if (!fgets(line, sizeof(line), lfn))
                    {
                        if (ferror(lfn))
                        {
                            bool closeFailed = ferror(lfn) != 0;
                            if (fclose(lfn))
                                closeFailed = true;
                            if (closeFailed)
                                x265_log(param, X265_LOG_WARNING, "unable to close lambda file after read failure\n");
                            x265_log_file(param, X265_LOG_ERROR, "unable to read lambda file <%s>\n", param->rc.lambdaFileName);
                            return true;
                        }
                        if (t < 2)
                        {
                            bool closeFailed = ferror(lfn) != 0;
                            if (fclose(lfn))
                                closeFailed = true;
                            if (closeFailed)
                                x265_log(param, X265_LOG_WARNING, "unable to close lambda file after incomplete parse\n");
                            x265_log(param, X265_LOG_ERROR, "lambda file is incomplete\n");
                            return true;
                        }
                        else
                        {
                            bool closeFailed = ferror(lfn) != 0;
                            if (fclose(lfn))
                                closeFailed = true;
                            if (closeFailed)
                                x265_log(param, X265_LOG_WARNING, "unable to close lambda file after truncated parse\n");
                            return false;
                        }
                    }

                    /* truncate at first hash */
                    char *hash = strchr(line, '#');
                    if (hash) *hash = 0;
                    buf = line;
                    scan = buf;
                }

                tok = nullptr;
                while (scan && *scan)
                {
                    while (*scan == ',' || std::isspace((unsigned char)*scan))
                        scan++;
                    if (!*scan)
                    {
                        scan = nullptr;
                        break;
                    }
                    tok = scan;
                    while (*scan && *scan != ',' && !std::isspace((unsigned char)*scan))
                        scan++;
                    if (*scan)
                        *scan++ = '\0';
                    break;
                }
                if (tok)
                {
                    bool bValueError = false;
                    value = x265_atof(tok, bValueError);
                    if (!bValueError)
                        break;
                    x265_log(param, X265_LOG_ERROR, "invalid lambda value: %s\n", tok);
                    bool closeFailed = ferror(lfn) != 0;
                    if (fclose(lfn))
                        closeFailed = true;
                    if (closeFailed)
                        x265_log(param, X265_LOG_WARNING, "unable to close lambda file after invalid value\n");
                    return true;
                }
            }
            while (1);

            if (t == 2)
            {
                x265_log(param, X265_LOG_ERROR, "lambda file contains too many values\n");
                bool closeFailed = ferror(lfn) != 0;
                if (fclose(lfn))
                    closeFailed = true;
                if (closeFailed)
                    x265_log(param, X265_LOG_WARNING, "unable to close lambda file after oversized table\n");
                return true;
            }
            else
                x265_log(param, X265_LOG_DEBUG, "lambda%c[%d] = %lf\n", t ? '2' : ' ', i, value);
            table[i] = value;
        }
    }

    bool closeFailed = ferror(lfn) != 0;
    if (fclose(lfn))
        closeFailed = true;
    if (closeFailed)
    {
        x265_log(param, X265_LOG_WARNING, "unable to finalize lambda file state\n");
        return true;
    }
    return false;
}

bool parseMaskingStrength(x265_param* p, const char* value)
{
    bool bError = false;
    int window1[6];
    double refQpDelta1[6], nonRefQpDelta1[6];
    if (p->bEnableSceneCutAwareQp == FORWARD)
    {
        if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))
            applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],
                                        p->fwdMaxScenecutWindow, p->fwdScenecutWindow,
                                        p->fwdRefQpDelta, p->fwdNonRefQpDelta);
        else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))
            applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,
                                         p->fwdMaxScenecutWindow, p->fwdScenecutWindow,
                                         p->fwdRefQpDelta, p->fwdNonRefQpDelta);
        else
        {
            x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \n");
            bError = true;
        }
    }
    else if (p->bEnableSceneCutAwareQp == BACKWARD)
    {
        if (parseMaskingStrengthTriples(value, 1, window1, refQpDelta1, nonRefQpDelta1))
            applyCompactMaskingStrength(window1[0], refQpDelta1[0], nonRefQpDelta1[0],
                                        p->bwdMaxScenecutWindow, p->bwdScenecutWindow,
                                        p->bwdRefQpDelta, p->bwdNonRefQpDelta);
        else if (parseMaskingStrengthTriples(value, 6, window1, refQpDelta1, nonRefQpDelta1))
            applyExpandedMaskingStrength(window1, refQpDelta1, nonRefQpDelta1,
                                         p->bwdMaxScenecutWindow, p->bwdScenecutWindow,
                                         p->bwdRefQpDelta, p->bwdNonRefQpDelta);
        else
        {
            x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \n");
            bError = true;
        }
    }
    else if (p->bEnableSceneCutAwareQp == BI_DIRECTIONAL)
    {
        int window2[12];
        double refQpDelta2[12], nonRefQpDelta2[12];
        if (parseMaskingStrengthTriples(value, 2, window2, refQpDelta2, nonRefQpDelta2))
        {
            applyCompactMaskingStrength(window2[0], refQpDelta2[0], nonRefQpDelta2[0],
                                        p->fwdMaxScenecutWindow, p->fwdScenecutWindow,
                                        p->fwdRefQpDelta, p->fwdNonRefQpDelta);
            applyCompactMaskingStrength(window2[1], refQpDelta2[1], nonRefQpDelta2[1],
                                        p->bwdMaxScenecutWindow, p->bwdScenecutWindow,
                                        p->bwdRefQpDelta, p->bwdNonRefQpDelta);
        }
        else if (parseMaskingStrengthTriples(value, 12, window2, refQpDelta2, nonRefQpDelta2))
        {
            p->fwdMaxScenecutWindow = 0;
            p->bwdMaxScenecutWindow = 0;
            for (int i = 0; i < 6; i++)
            {
                p->fwdScenecutWindow[i] = window2[i];
                p->fwdRefQpDelta[i] = refQpDelta2[i];
                p->fwdNonRefQpDelta[i] = nonRefQpDelta2[i];
                p->bwdScenecutWindow[i] = window2[i + 6];
                p->bwdRefQpDelta[i] = refQpDelta2[i + 6];
                p->bwdNonRefQpDelta[i] = nonRefQpDelta2[i + 6];
                p->fwdMaxScenecutWindow += p->fwdScenecutWindow[i];
                p->bwdMaxScenecutWindow += p->bwdScenecutWindow[i];
            }
        }
        else
        {
            x265_log(nullptr, X265_LOG_ERROR, "Specify all the necessary offsets for masking-strength \n");
            bError = true;
        }
    }
    return bError;
}

void x265_copy_params(x265_param* dst, x265_param* src)
{
#ifdef SVT_HEVC
    if (src->svtHevcParam && !ensureSvtHevcParam(dst))
    {
        x265_log(nullptr, X265_LOG_ERROR, "unable to allocate SVT parameter storage\n");
        return;
    }
#endif
    const bool preserveDstZones = (src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig) ||
                                  (src->rc.zoneCount && src->rc.zones);
    const bool zonefileCopy = src->rc.zonefileCount && src->rc.zones && src->bResetZoneConfig;
    if (dst->rc.zones && !preserveDstZones)
        x265_zone_free(dst);
    if (preserveDstZones && !ensureZoneCopyDestination(dst, src, zonefileCopy))
        return;

    dst->mcstfFrameRange = src->mcstfFrameRange;
    dst->cpuid = src->cpuid;
    dst->frameNumThreads = src->frameNumThreads;
    if (strlen(src->numaPools)) snprintf(dst->numaPools, X265_MAX_STRING_SIZE, "%s", src->numaPools);
    else dst->numaPools[0] = 0;

    dst->tune = src->tune;
    dst->bEnableWavefront = src->bEnableWavefront;
    dst->bDistributeModeAnalysis = src->bDistributeModeAnalysis;
    dst->bDistributeMotionEstimation = src->bDistributeMotionEstimation;
    dst->bEnablePsnr = src->bEnablePsnr;
    dst->bEnableSsim = src->bEnableSsim;
    dst->logLevel = src->logLevel;
    char* newLogfn = nullptr;
    if (src->logfn)
    {
        newLogfn = strdup(src->logfn);
        if (!newLogfn)
            x265_log(nullptr, X265_LOG_ERROR, "unable to allocate memory\n");
    }
    else if (dst->logfn)
    {
        free(dst->logfn);
        dst->logfn = nullptr;
    }
    if (newLogfn)
    {
        free(dst->logfn);
        dst->logfn = newLogfn;
    }
    dst->logfLevel = src->logfLevel;
    char* newPgfn = nullptr;
    if (src->pgfn)
    {
        newPgfn = strdup(src->pgfn);
        if (!newPgfn)
            x265_log(nullptr, X265_LOG_ERROR, "unable to allocate memory\n");
    }
    else if (dst->pgfn)
    {
        free(dst->pgfn);
        dst->pgfn = nullptr;
    }
    if (newPgfn)
    {
        free(dst->pgfn);
        dst->pgfn = newPgfn;
    }
    dst->csvLogLevel = src->csvLogLevel;
    if (strlen(src->csvfn)) snprintf(dst->csvfn, X265_MAX_STRING_SIZE, "%s", src->csvfn);
    else dst->csvfn[0] = 0;
    dst->internalBitDepth = src->internalBitDepth;
    dst->sourceBitDepth = src->sourceBitDepth;
    dst->internalCsp = src->internalCsp;
    dst->fpsNum = src->fpsNum;
    dst->fpsDenom = src->fpsDenom;
    dst->sourceHeight = src->sourceHeight;
    dst->sourceWidth = src->sourceWidth;
    dst->interlaceMode = src->interlaceMode;
    dst->totalFrames = src->totalFrames;
    dst->levelIdc = src->levelIdc;
    dst->bHighTier = src->bHighTier;
    dst->uhdBluray = src->uhdBluray;
    dst->maxNumReferences = src->maxNumReferences;
    dst->bAllowNonConformance = src->bAllowNonConformance;
    dst->bRepeatHeaders = src->bRepeatHeaders;
    dst->bAnnexB = src->bAnnexB;
    dst->bEnableAccessUnitDelimiters = src->bEnableAccessUnitDelimiters;
    dst->bEnableEndOfBitstream = src->bEnableEndOfBitstream;
    dst->bEnableEndOfSequence = src->bEnableEndOfSequence;
    dst->bEmitInfoSEI = src->bEmitInfoSEI;
    dst->decodedPictureHashSEI = src->decodedPictureHashSEI;
    dst->bEnableTemporalSubLayers = src->bEnableTemporalSubLayers;
    dst->bOpenGOP = src->bOpenGOP;
	dst->craNal = src->craNal;
    dst->keyframeMax = src->keyframeMax;
    dst->keyframeMin = src->keyframeMin;
    dst->bframes = src->bframes;
    dst->bFrameAdaptive = src->bFrameAdaptive;
    dst->bFrameBias = src->bFrameBias;
    dst->bBPyramid = src->bBPyramid;
    dst->lookaheadDepth = src->lookaheadDepth;
    dst->lookaheadSlices = src->lookaheadSlices;
    dst->lookaheadThreads = src->lookaheadThreads;
    dst->scenecutThreshold = src->scenecutThreshold;
    dst->bHistBasedSceneCut = src->bHistBasedSceneCut;
    dst->bIntraRefresh = src->bIntraRefresh;
    dst->maxCUSize = src->maxCUSize;
    dst->minCUSize = src->minCUSize;
    dst->bEnableRectInter = src->bEnableRectInter;
    dst->bEnableAMP = src->bEnableAMP;
    dst->maxTUSize = src->maxTUSize;
    dst->tuQTMaxInterDepth = src->tuQTMaxInterDepth;
    dst->tuQTMaxIntraDepth = src->tuQTMaxIntraDepth;
    dst->limitTU = src->limitTU;
    dst->rdoqLevel = src->rdoqLevel;
    dst->bEnableSignHiding = src->bEnableSignHiding;
    dst->bEnableTransformSkip = src->bEnableTransformSkip;
    dst->noiseReductionInter = src->noiseReductionInter;
    dst->noiseReductionIntra = src->noiseReductionIntra;
    if (strlen(src->scalingLists)) snprintf(dst->scalingLists, X265_MAX_STRING_SIZE, "%s", src->scalingLists);
    else dst->scalingLists[0] = 0;
    dst->bEnableStrongIntraSmoothing = src->bEnableStrongIntraSmoothing;
    dst->bEnableConstrainedIntra = src->bEnableConstrainedIntra;
    dst->maxNumMergeCand = src->maxNumMergeCand;
    dst->limitReferences = src->limitReferences;
    dst->limitModes = src->limitModes;
    dst->searchMethod = src->searchMethod;
    dst->subpelRefine = src->subpelRefine;
    dst->searchRange = src->searchRange;
    dst->bEnableTemporalMvp = src->bEnableTemporalMvp;
    dst->bEnableFrameDuplication = src->bEnableFrameDuplication;
    dst->dupThreshold = src->dupThreshold;
    dst->bEnableHME = src->bEnableHME;
    if (src->bEnableHME)
    {
        for (int level = 0; level < 3; level++)
        {
            dst->hmeSearchMethod[level] = src->hmeSearchMethod[level];
            dst->hmeRange[level] = src->hmeRange[level];
        }
    }
    dst->bEnableWeightedBiPred = src->bEnableWeightedBiPred;
    dst->bEnableWeightedPred = src->bEnableWeightedPred;
    dst->bSourceReferenceEstimation = src->bSourceReferenceEstimation;
    dst->bEnableLoopFilter = src->bEnableLoopFilter;
    dst->deblockingFilterBetaOffset = src->deblockingFilterBetaOffset;
    dst->deblockingFilterTCOffset = src->deblockingFilterTCOffset;
    dst->bEnableSAO = src->bEnableSAO;
    dst->bSaoNonDeblocked = src->bSaoNonDeblocked;
    dst->rdLevel = src->rdLevel;
    dst->bEnableEarlySkip = src->bEnableEarlySkip;
    dst->recursionSkipMode = src->recursionSkipMode;
    dst->edgeVarThreshold = src->edgeVarThreshold;
    dst->bEnableFastIntra = src->bEnableFastIntra;
    dst->bEnableTSkipFast = src->bEnableTSkipFast;
    dst->bCULossless = src->bCULossless;
    dst->bIntraInBFrames = src->bIntraInBFrames;
    dst->rdPenalty = src->rdPenalty;
    dst->psyRd = src->psyRd;
    dst->psyRdoq = src->psyRdoq;
    dst->psyScaleB = src->psyScaleB;
    dst->psyScaleP = src->psyScaleP;
    dst->psyScaleI = src->psyScaleI;
    dst->bEnableRdRefine = src->bEnableRdRefine;
    if (strlen(src->analysisReuseFileName)) snprintf(dst->analysisReuseFileName, X265_MAX_STRING_SIZE, "%s", src->analysisReuseFileName);
    else dst->analysisReuseFileName[0] = 0;
    dst->bLossless = src->bLossless;
    dst->cbQpOffset = src->cbQpOffset;
    dst->crQpOffset = src->crQpOffset;
    dst->preferredTransferCharacteristics = src->preferredTransferCharacteristics;
    dst->pictureStructure = src->pictureStructure;

    dst->rc.rateControlMode = src->rc.rateControlMode;
    dst->rc.qScaleMode = src->rc.qScaleMode;
    dst->rc.qp = src->rc.qp;
    dst->rc.bitrate = src->rc.bitrate;
    dst->rc.qCompress = src->rc.qCompress;
    dst->rc.cuTreeStrength = src->rc.cuTreeStrength;
    dst->rc.cuTreeMinQpOffset = src->rc.cuTreeMinQpOffset;
    dst->rc.cuTreeMaxQpOffset = src->rc.cuTreeMaxQpOffset;
    dst->rc.ipFactor = src->rc.ipFactor;
    dst->rc.pbFactor = src->rc.pbFactor;
    dst->rc.rfConstant = src->rc.rfConstant;
    dst->rc.qpStep = src->rc.qpStep;
    dst->rc.aqMode = src->rc.aqMode;
    dst->rc.limitAq1 = src->rc.limitAq1;
    dst->rc.aqStrength = src->rc.aqStrength;
    dst->rc.aqBiasStrength = src->rc.aqBiasStrength;
    dst->rc.limitAq1Strength = src->rc.limitAq1Strength;
    dst->rc.vbvBufferSize = src->rc.vbvBufferSize;
    dst->rc.vbvMaxBitrate = src->rc.vbvMaxBitrate;

    dst->rc.vbvBufferInit = src->rc.vbvBufferInit;
    dst->minVbvFullness = src->minVbvFullness;
    dst->maxVbvFullness = src->maxVbvFullness;
    dst->rc.cuTree = src->rc.cuTree;
    dst->rc.rfConstantMax = src->rc.rfConstantMax;
    dst->rc.rfConstantMin = src->rc.rfConstantMin;
    dst->rc.bStatWrite = src->rc.bStatWrite;
    dst->rc.bStatRead = src->rc.bStatRead;
    dst->rc.dataShareMode = src->rc.dataShareMode;
    if (strlen(src->rc.statFileName)) snprintf(dst->rc.statFileName, X265_MAX_STRING_SIZE, "%s", src->rc.statFileName);
    else dst->rc.statFileName[0] = 0;
    if (strlen(src->rc.sharedMemName)) snprintf(dst->rc.sharedMemName, X265_MAX_STRING_SIZE, "%s", src->rc.sharedMemName);
    else dst->rc.sharedMemName[0] = 0;
    dst->rc.qblur = src->rc.qblur;
    dst->rc.complexityBlur = src->rc.complexityBlur;
    dst->rc.bEnableSlowFirstPass = src->rc.bEnableSlowFirstPass;
    dst->rc.zoneCount = src->rc.zoneCount;
    dst->rc.zonefileCount = src->rc.zonefileCount;
    dst->reconfigWindowSize = src->reconfigWindowSize;
    dst->bResetZoneConfig = src->bResetZoneConfig;
    dst->bNoResetZoneConfig = src->bNoResetZoneConfig;
    dst->decoderVbvMaxRate = src->decoderVbvMaxRate;

    if (src->rc.zonefileCount)
    {
        dst->rc.zoneCount = 0;
        if (src->rc.zones && src->bResetZoneConfig)
        {
            for (int i = 0; i < src->rc.zonefileCount; i++)
            {
                if (!src->rc.zones[i].zoneParam || !dst->rc.zones[i].zoneParam)
                {
                    x265_log(nullptr, X265_LOG_ERROR, "zonefile param copy requires non-null zoneParam storage\n");
                    return;
                }
                dst->rc.zones[i].startFrame = src->rc.zones[i].startFrame;
                dst->rc.zones[0].keyframeMax = src->rc.zones[0].keyframeMax;
#ifdef SVT_HEVC
                void* dstZoneSvtHevcParam = dst->rc.zones[i].zoneParam->svtHevcParam;
                memcpy(dst->rc.zones[i].zoneParam, src->rc.zones[i].zoneParam, sizeof(x265_param));
                dst->rc.zones[i].zoneParam->svtHevcParam = dstZoneSvtHevcParam;
                finalizeZoneParamCopy(dst->rc.zones[i].zoneParam, src->rc.zones[i].zoneParam);
#else
                memcpy(dst->rc.zones[i].zoneParam, src->rc.zones[i].zoneParam, sizeof(x265_param));
                dst->rc.zones[i].zoneParam->rc.zones = nullptr;
                dst->rc.zones[i].zoneParam->rc.zoneCount = 0;
                dst->rc.zones[i].zoneParam->rc.zonefileCount = 0;
#endif
            }
        }
        else
            dst->rc.zones = nullptr;
    }
    else if (src->rc.zoneCount && src->rc.zones)
    {
        for (int i = 0; i < src->rc.zoneCount; i++)
        {
            dst->rc.zones[i].startFrame = src->rc.zones[i].startFrame;
            dst->rc.zones[i].endFrame = src->rc.zones[i].endFrame;
            dst->rc.zones[i].bForceQp = src->rc.zones[i].bForceQp;
            dst->rc.zones[i].qp = src->rc.zones[i].qp;
            dst->rc.zones[i].bitrateFactor = src->rc.zones[i].bitrateFactor;
        }
    }
    else
        dst->rc.zones = nullptr;

    if (strlen(src->rc.lambdaFileName)) snprintf(dst->rc.lambdaFileName, X265_MAX_STRING_SIZE, "%s", src->rc.lambdaFileName);
    else dst->rc.lambdaFileName[0] = 0;
    dst->rc.bStrictCbr = src->rc.bStrictCbr;
    dst->rc.qgSize = src->rc.qgSize;
    dst->rc.bEnableGrain = src->rc.bEnableGrain;
    dst->rc.qpMax = src->rc.qpMax;
    dst->rc.qpMin = src->rc.qpMin;
    dst->rc.bEnableConstVbv = src->rc.bEnableConstVbv;
    dst->rc.hevcAq = src->rc.hevcAq;
    dst->rc.qpAdaptationRange = src->rc.qpAdaptationRange;

    dst->vui.aspectRatioIdc = src->vui.aspectRatioIdc;
    dst->vui.sarWidth = src->vui.sarWidth;
    dst->vui.sarHeight = src->vui.sarHeight;
    dst->vui.bEnableOverscanAppropriateFlag = src->vui.bEnableOverscanAppropriateFlag;
    dst->vui.bEnableOverscanInfoPresentFlag = src->vui.bEnableOverscanInfoPresentFlag;
    dst->vui.bEnableVideoSignalTypePresentFlag = src->vui.bEnableVideoSignalTypePresentFlag;
    dst->vui.videoFormat = src->vui.videoFormat;
    dst->vui.bEnableVideoFullRangeFlag = src->vui.bEnableVideoFullRangeFlag;
    dst->vui.bEnableColorDescriptionPresentFlag = src->vui.bEnableColorDescriptionPresentFlag;
    dst->vui.colorPrimaries = src->vui.colorPrimaries;
    dst->vui.transferCharacteristics = src->vui.transferCharacteristics;
    dst->vui.matrixCoeffs = src->vui.matrixCoeffs;
    dst->vui.bEnableChromaLocInfoPresentFlag = src->vui.bEnableChromaLocInfoPresentFlag;
    dst->vui.chromaSampleLocTypeTopField = src->vui.chromaSampleLocTypeTopField;
    dst->vui.chromaSampleLocTypeBottomField = src->vui.chromaSampleLocTypeBottomField;
    dst->vui.bEnableDefaultDisplayWindowFlag = src->vui.bEnableDefaultDisplayWindowFlag;
    dst->vui.defDispWinBottomOffset = src->vui.defDispWinBottomOffset;
    dst->vui.defDispWinLeftOffset = src->vui.defDispWinLeftOffset;
    dst->vui.defDispWinRightOffset = src->vui.defDispWinRightOffset;
    dst->vui.defDispWinTopOffset = src->vui.defDispWinTopOffset;

    if (strlen(src->masteringDisplayColorVolume)) snprintf(dst->masteringDisplayColorVolume, X265_MAX_STRING_SIZE, "%s", src->masteringDisplayColorVolume);
    else dst->masteringDisplayColorVolume[0] = 0;
    dst->maxLuma = src->maxLuma;
    dst->minLuma = src->minLuma;
    dst->bEmitCLL = src->bEmitCLL;
    dst->maxCLL = src->maxCLL;
    dst->maxFALL = src->maxFALL;
    dst->log2MaxPocLsb = src->log2MaxPocLsb;
    dst->bEmitVUIHRDInfo = src->bEmitVUIHRDInfo;
    dst->bEmitVUITimingInfo = src->bEmitVUITimingInfo;
    dst->maxSlices = src->maxSlices;
    dst->bOptQpPPS = src->bOptQpPPS;
    dst->bOptRefListLengthPPS = src->bOptRefListLengthPPS;
    dst->bMultiPassOptRPS = src->bMultiPassOptRPS;
    dst->scenecutBias = src->scenecutBias;
    dst->gopLookahead = src->lookaheadDepth;
    dst->bOptCUDeltaQP = src->bOptCUDeltaQP;
    dst->analysisMultiPassDistortion = src->analysisMultiPassDistortion;
    dst->analysisMultiPassRefine = src->analysisMultiPassRefine;
    dst->bAQMotion = src->bAQMotion;
    dst->bSsimRd = src->bSsimRd;
    dst->dynamicRd = src->dynamicRd;
    dst->bEmitHDR10SEI = src->bEmitHDR10SEI;
    dst->bEmitHRDSEI = src->bEmitHRDSEI;
    dst->bHDR10Opt = src->bHDR10Opt;
    dst->analysisSaveReuseLevel = src->analysisSaveReuseLevel;
    dst->analysisLoadReuseLevel = src->analysisLoadReuseLevel;
    dst->bLimitSAO = src->bLimitSAO;
    if (strlen(src->toneMapFile)) snprintf(dst->toneMapFile, X265_MAX_STRING_SIZE, "%s", src->toneMapFile);
    else dst->toneMapFile[0] = 0;
    dst->bDhdr10opt = src->bDhdr10opt;
    dst->bCTUInfo = src->bCTUInfo;
    dst->bUseRcStats = src->bUseRcStats;
    dst->interRefine = src->interRefine;
    dst->intraRefine = src->intraRefine;
    dst->mvRefine = src->mvRefine;
    dst->maxLog2CUSize = src->maxLog2CUSize;
    dst->maxCUDepth = src->maxCUDepth;
    dst->unitSizeDepth = src->unitSizeDepth;
    dst->num4x4Partitions = src->num4x4Partitions;

    dst->csvfpt = src->csvfpt;
    dst->bStylish = src->bStylish;
    dst->bEnableSplitRdSkip = src->bEnableSplitRdSkip;
    dst->bUseAnalysisFile = src->bUseAnalysisFile;
    dst->forceFlush = src->forceFlush;
    dst->bDisableLookahead = src->bDisableLookahead;
    dst->bLowPassDct = src->bLowPassDct;
    dst->vbvBufferEnd = src->vbvBufferEnd;
    dst->vbvEndFrameAdjust = src->vbvEndFrameAdjust;
    dst->bAnalysisType = src->bAnalysisType;
    dst->bCopyPicToFrame = src->bCopyPicToFrame;
    if (strlen(src->analysisSave)) snprintf(dst->analysisSave, X265_MAX_STRING_SIZE, "%s", src->analysisSave);
    else dst->analysisSave[0] = 0;
    if (strlen(src->analysisLoad)) snprintf(dst->analysisLoad, X265_MAX_STRING_SIZE, "%s", src->analysisLoad);
    else dst->analysisLoad[0] = 0;
    dst->gopLookahead = src->gopLookahead;
    dst->radl = src->radl;
    dst->selectiveSAO = src->selectiveSAO;
    dst->maxAUSizeFactor = src->maxAUSizeFactor;
    dst->bEmitIDRRecoverySEI = src->bEmitIDRRecoverySEI;
    dst->bDynamicRefine = src->bDynamicRefine;
    dst->bSingleSeiNal = src->bSingleSeiNal;
    dst->chunkStart = src->chunkStart;
    dst->chunkEnd = src->chunkEnd;
    if (src->naluFile[0]) snprintf(dst->naluFile, X265_MAX_STRING_SIZE, "%s", src->naluFile);
    else dst->naluFile[0] = 0;
    dst->scaleFactor = src->scaleFactor;
    dst->ctuDistortionRefine = src->ctuDistortionRefine;
    dst->bEnableHRDConcatFlag = src->bEnableHRDConcatFlag;
    dst->dolbyProfile = src->dolbyProfile;
    dst->bEnableSvtHevc = src->bEnableSvtHevc;
    dst->bThreadedME = src->bThreadedME;
    dst->tmeTaskBlockSize = src->tmeTaskBlockSize;
    dst->tmeNumBufferRows = src->tmeNumBufferRows;
    dst->bEnableFades = src->bEnableFades;
    dst->bEnableSceneCutAwareQp = src->bEnableSceneCutAwareQp;
    dst->fwdMaxScenecutWindow = src->fwdMaxScenecutWindow;
    dst->bwdMaxScenecutWindow = src->bwdMaxScenecutWindow;
    for (int i = 0; i < 6; i++)
    {
        dst->fwdScenecutWindow[i] = src->fwdScenecutWindow[i];
        dst->fwdRefQpDelta[i] = src->fwdRefQpDelta[i];
        dst->fwdNonRefQpDelta[i] = src->fwdNonRefQpDelta[i];
        dst->bwdScenecutWindow[i] = src->bwdScenecutWindow[i];
        dst->bwdRefQpDelta[i] = src->bwdRefQpDelta[i];
        dst->bwdNonRefQpDelta[i] = src->bwdNonRefQpDelta[i];
    }
    dst->bField = src->bField;
    dst->bEnableTemporalFilter = src->bEnableTemporalFilter;
    dst->temporalFilterStrength = src->temporalFilterStrength;
    dst->searchRangeForLayer0 = src->searchRangeForLayer0;
    dst->searchRangeForLayer1 = src->searchRangeForLayer1;
    dst->searchRangeForLayer2 = src->searchRangeForLayer2;
    dst->confWinRightOffset = src->confWinRightOffset;
    dst->confWinBottomOffset = src->confWinBottomOffset;
    dst->bliveVBV2pass = src->bliveVBV2pass;
#if ENABLE_ALPHA
    dst->bEnableAlpha = src->bEnableAlpha;
    dst->numScalableLayers = src->numScalableLayers;
#endif
#if ENABLE_MULTIVIEW
    dst->numViews = src->numViews;
    dst->format = src->format;
#endif
    dst->numLayers = src->numLayers;
#if ENABLE_SCC_EXT
    dst->bEnableSCC = src->bEnableSCC;
#endif

    if (strlen(src->videoSignalTypePreset)) snprintf(dst->videoSignalTypePreset, X265_MAX_STRING_SIZE, "%s", src->videoSignalTypePreset);
    else dst->videoSignalTypePreset[0] = 0;
#ifdef SVT_HEVC
    if (!copySvtHevcParamStorage(dst, src))
        x265_log(nullptr, X265_LOG_ERROR, "unable to allocate SVT parameter storage\n");
#endif
    /* Film grain */
    dst->filmGrain = src->filmGrain;
    /* Aom Film grain*/
    dst->aomFilmGrain = src->aomFilmGrain;
    dst->bEnableSBRC = src->bEnableSBRC;
    dst->bConfigRCFrame = src->bConfigRCFrame;
    dst->isAbrLadderEnable = src->isAbrLadderEnable;
}

void x265_copy_params_writeonly(x265_param* dst, x265_param* src)
{
    if (!prepareFreshParamCopyDestination(dst, src))
        return;

    x265_copy_params(dst, src);
}

#ifdef SVT_HEVC

void svt_param_default(x265_param* param)
{
    EB_H265_ENC_CONFIGURATION* svtHevcParam = (EB_H265_ENC_CONFIGURATION*)param->svtHevcParam;

    // Channel info
    svtHevcParam->channelId = 0;
    svtHevcParam->activeChannelCount = 0;

    // GOP Structure
    svtHevcParam->intraPeriodLength = -2;
    svtHevcParam->intraRefreshType = 1;
    svtHevcParam->predStructure = 2;
    svtHevcParam->baseLayerSwitchMode = 0;
    svtHevcParam->hierarchicalLevels = 3;
    svtHevcParam->sourceWidth = 0;
    svtHevcParam->sourceHeight = 0;
    svtHevcParam->latencyMode = 0;

    //Preset & Tune
    svtHevcParam->encMode = 7;
    svtHevcParam->tune = 1;

    // Interlaced Video 
    svtHevcParam->interlacedVideo = 0;

    // Quantization
    svtHevcParam->qp = 32;
    svtHevcParam->useQpFile = 0;

    // Deblock Filter
    svtHevcParam->disableDlfFlag = 0;

    // SAO
    svtHevcParam->enableSaoFlag = 1;

    // ME Tools
    svtHevcParam->useDefaultMeHme = 1;
    svtHevcParam->enableHmeFlag = 1;

    // ME Parameters
    svtHevcParam->searchAreaWidth = 16;
    svtHevcParam->searchAreaHeight = 7;

    // MD Parameters
    svtHevcParam->constrainedIntra = 0;

    // Rate Control
    svtHevcParam->frameRate = 60;
    svtHevcParam->frameRateNumerator = 0;
    svtHevcParam->frameRateDenominator = 0;
    svtHevcParam->encoderBitDepth = 8;
    svtHevcParam->encoderColorFormat = EB_YUV420;
    svtHevcParam->compressedTenBitFormat = 0;
    svtHevcParam->rateControlMode = 0;
    svtHevcParam->sceneChangeDetection = 1;
    svtHevcParam->lookAheadDistance = (uint32_t)~0;
    svtHevcParam->framesToBeEncoded = 0;
    svtHevcParam->targetBitRate = 7000000;
    svtHevcParam->maxQpAllowed = 48;
    svtHevcParam->minQpAllowed = 10;
    svtHevcParam->bitRateReduction = 0;

    // Thresholds
    svtHevcParam->improveSharpness = 0;
    svtHevcParam->videoUsabilityInfo = 0;
    svtHevcParam->highDynamicRangeInput = 0;
    svtHevcParam->accessUnitDelimiter = 0;
    svtHevcParam->bufferingPeriodSEI = 0;
    svtHevcParam->pictureTimingSEI = 0;
    svtHevcParam->registeredUserDataSeiFlag = 0;
    svtHevcParam->unregisteredUserDataSeiFlag = 0;
    svtHevcParam->recoveryPointSeiFlag = 0;
    svtHevcParam->enableTemporalId = 1;
    svtHevcParam->profile = 1;
    svtHevcParam->tier = 0;
    svtHevcParam->level = 0;

    svtHevcParam->injectorFrameRate = 60 << 16;
    svtHevcParam->speedControlFlag = 0;

    // ASM Type
    svtHevcParam->asmType = 1;

    svtHevcParam->codeVpsSpsPps = 1;
    svtHevcParam->codeEosNal = 0;
    svtHevcParam->reconEnabled = 0;
    svtHevcParam->maxCLL = 0;
    svtHevcParam->maxFALL = 0;
    svtHevcParam->useMasteringDisplayColorVolume = 0;
    svtHevcParam->useNaluFile = 0;
    svtHevcParam->whitePointX = 0;
    svtHevcParam->whitePointY = 0;
    svtHevcParam->maxDisplayMasteringLuminance = 0;
    svtHevcParam->minDisplayMasteringLuminance = 0;
    svtHevcParam->dolbyVisionProfile = 0;
    svtHevcParam->targetSocket = -1;
    svtHevcParam->logicalProcessors = 0;
    svtHevcParam->switchThreadsToRtPriority = 1;
    svtHevcParam->fpsInVps = 0;

    svtHevcParam->tileColumnCount = 1;
    svtHevcParam->tileRowCount = 1;
    svtHevcParam->tileSliceMode = 0;
    svtHevcParam->unrestrictedMotionVector = 1;
    svtHevcParam->threadCount = 0;

    // vbv
    svtHevcParam->hrdFlag = 0;
    svtHevcParam->vbvMaxrate = 0;
    svtHevcParam->vbvBufsize = 0;
    svtHevcParam->vbvBufInit = 90;
}

int svt_set_preset(x265_param* param, const char* preset)
{
    EB_H265_ENC_CONFIGURATION* svtHevcParam = ensureSvtHevcParam(param);
    if (!svtHevcParam)
    {
        x265_log(param, X265_LOG_ERROR, "unable to allocate SVT parameter storage\n");
        return -1;
    }

    if (preset)
    {
        preset = parsePresetIndexName(preset);

        if (!strcmp(preset, "ultrafast")) svtHevcParam->encMode = 9;
        else if (!strcmp(preset, "superfast")) svtHevcParam->encMode = 9;
        else if (!strcmp(preset, "veryfast")) svtHevcParam->encMode = 9;
        else if (!strcmp(preset, "faster")) svtHevcParam->encMode = 8;
        else if (!strcmp(preset, "fast")) svtHevcParam->encMode = 7;
        else if (!strcmp(preset, "medium")) svtHevcParam->encMode = 6;
        else if (!strcmp(preset, "slow")) svtHevcParam->encMode = 5;
        else if (!strcmp(preset, "slower")) svtHevcParam->encMode =4;
        else if (!strcmp(preset, "veryslow")) svtHevcParam->encMode = 3;
        else if (!strcmp(preset, "placebo")) svtHevcParam->encMode = 2;
        else  return -1;
    }
    return 0;
}

int svt_param_parse(x265_param* param, const char* name, const char* value)
{
    bool bError = false;
#define OPT(STR) else if (!strcmp(name, STR))

    EB_H265_ENC_CONFIGURATION* svtHevcParam = ensureSvtHevcParam(param);
    if (!svtHevcParam)
    {
        x265_log(param, X265_LOG_ERROR, "unable to allocate SVT parameter storage\n");
        return X265_PARAM_BAD_VALUE;
    }
    if (0);
    OPT("input-res")
    {
        int sourceWidth = 0;
        int sourceHeight = 0;
        if (!parseOptionIntPair(value, 'x', sourceWidth, sourceHeight))
            bError = true;
        else
        {
            svtHevcParam->sourceWidth = (uint32_t)sourceWidth;
            svtHevcParam->sourceHeight = (uint32_t)sourceHeight;
        }
    }
    OPT("input-depth")
    {
        bool bEncoderBitDepthError = false;
        int encoderBitDepth = parseOptionIntValue(value, bEncoderBitDepthError);
        bError |= bEncoderBitDepthError;
        if (!bEncoderBitDepthError)
            svtHevcParam->encoderBitDepth = encoderBitDepth;
    }
    OPT("total-frames")
    {
        bool bFramesToBeEncodedError = false;
        int framesToBeEncoded = parseOptionIntValue(value, bFramesToBeEncodedError);
        bError |= bFramesToBeEncodedError;
        if (!bFramesToBeEncodedError)
            svtHevcParam->framesToBeEncoded = framesToBeEncoded;
    }
    OPT("frames")
    {
        bool bFramesToBeEncodedError = false;
        int framesToBeEncoded = parseOptionIntValue(value, bFramesToBeEncodedError);
        bError |= bFramesToBeEncodedError;
        if (!bFramesToBeEncodedError)
            svtHevcParam->framesToBeEncoded = framesToBeEncoded;
    }
    OPT("fps")
    {
        bError |= !parseFpsValue(value, svtHevcParam->frameRateNumerator, svtHevcParam->frameRateDenominator);
        if (!bError)
        {
            if (svtHevcParam->frameRateDenominator == 1 && svtHevcParam->frameRateNumerator < 1000)
                svtHevcParam->frameRate = svtHevcParam->frameRateNumerator << 16;
            else if (svtHevcParam->frameRateDenominator == 1)
                svtHevcParam->frameRate = svtHevcParam->frameRateNumerator;
        }
    }
    OPT2("level-idc", "level")
    {
        /* allow "5.1" or "51", both converted to integer 51 */
        /* if level-idc specifies an obviously wrong value in either float or int,
        throw error consistently. Stronger level checking will be done in encoder_open() */
        if (!parseTenthsOrIntegerLevel(value, svtHevcParam->level))
            bError = true;
    }
    OPT2("pools", "numa-pools")
    {
        char *pools = strdup(value);
        if (!pools)
        {
            x265_log(param, X265_LOG_ERROR, "unable to allocate memory for SVT pools option\n");
            bError = true;
        }
        else
        {
            char *temp1, *temp2;
            int count = 0;

            for (temp1 = strstr(pools, ","); temp1 != nullptr; temp1 = strstr(temp2, ","))
            {
                temp2 = ++temp1;
                count++;
            }

            if (count > 1)
                x265_log(param, X265_LOG_WARNING, "SVT-HEVC Encoder supports pools option only upto 2 sockets \n");
            else if (count == 1)
            {
                char* separator = std::strchr(pools, ',');
                if (!separator || separator == pools || !separator[1])
                {
                    x265_log(param, X265_LOG_ERROR, "Invalid pools option %s\n", value);
                    bError = true;
                }
                else
                {
                    *separator = '\0';
                    temp1 = pools;
                    temp2 = separator + 1;
                    if (!strcmp(temp1, "+"))
                    {
                        if (!strcmp(temp2, "+")) svtHevcParam->targetSocket = -1;
                        else if (!strcmp(temp2, "-")) svtHevcParam->targetSocket = 0;
                        else svtHevcParam->targetSocket = -1;
                    }
                    else if (!strcmp(temp1, "-"))
                    {
                        if (!strcmp(temp2, "+")) svtHevcParam->targetSocket = 1;
                        else if (!strcmp(temp2, "-"))
                        {
                            x265_log(param, X265_LOG_ERROR, "Shouldn't exclude both sockets for pools option %s \n", pools);
                            bError = true;
                        }
                        else if (!strcmp(temp2, "*")) svtHevcParam->targetSocket = 1;
                        else
                        {
                            bool bLogicalProcessorsError = false;
                            int logicalProcessors = parseOptionIntValue(temp2, bLogicalProcessorsError);
                            bError |= bLogicalProcessorsError;
                            if (!bLogicalProcessorsError)
                            {
                                svtHevcParam->targetSocket = 1;
                                svtHevcParam->logicalProcessors = logicalProcessors;
                            }
                        }
                    }
                    else svtHevcParam->targetSocket = -1;
                }
            }
            else
            {
                temp1 = pools;
                if (!strcmp(temp1, "*")) svtHevcParam->targetSocket = -1;
                else
                {
                    bool bLogicalProcessorsError = false;
                    int logicalProcessors = parseOptionIntValue(temp1, bLogicalProcessorsError);
                    bError |= bLogicalProcessorsError;
                    if (!bLogicalProcessorsError)
                    {
                        svtHevcParam->targetSocket = 0;
                        svtHevcParam->logicalProcessors = logicalProcessors;
                    }
                }
            }
            free(pools);
        }
    }
    OPT("high-tier")
    {
        int tier = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->tier = tier;
    }
    OPT("qpmin")
    {
        bool bMinQpAllowedError = false;
        int minQpAllowed = parseOptionIntValue(value, bMinQpAllowedError);
        bError |= bMinQpAllowedError;
        if (!bMinQpAllowedError)
            svtHevcParam->minQpAllowed = minQpAllowed;
    }
    OPT("qpmax")
    {
        bool bMaxQpAllowedError = false;
        int maxQpAllowed = parseOptionIntValue(value, bMaxQpAllowedError);
        bError |= bMaxQpAllowedError;
        if (!bMaxQpAllowedError)
            svtHevcParam->maxQpAllowed = maxQpAllowed;
    }
    OPT("rc-lookahead")
    {
        bool bLookAheadDistanceError = false;
        int lookAheadDistance = parseOptionIntValue(value, bLookAheadDistanceError);
        bError |= bLookAheadDistanceError;
        if (!bLookAheadDistanceError)
            svtHevcParam->lookAheadDistance = lookAheadDistance;
    }
    OPT("scenecut")
    {
        bool bSceneChangeDetectionError = false;
        int sceneChangeDetection = x265_atobool(value, bSceneChangeDetectionError);
        bError |= bSceneChangeDetectionError;
        if (!bSceneChangeDetectionError)
        {
            svtHevcParam->sceneChangeDetection = sceneChangeDetection;
            if (svtHevcParam->sceneChangeDetection)
                svtHevcParam->sceneChangeDetection = 1;
        }
    }
    OPT("open-gop")
    {
        int bOpenGop = x265_atobool(value, bError);
        if (!bError && bOpenGop)
            svtHevcParam->intraRefreshType = 1;
        else if (!bError)
            svtHevcParam->intraRefreshType = 2;
    }
    OPT("deblock")
    {
        bool bDeblockValueError = false;
        int deblockValue = parseOptionIntValue(value, bDeblockValueError);
        if (!bDeblockValueError)
            svtHevcParam->disableDlfFlag = deblockValue ? 0 : 1;
        else
        {
            int deblockEnabled = x265_atobool(value, bError);
            if (!bError)
                svtHevcParam->disableDlfFlag = deblockEnabled ? 0 : 1;
        }
    }
    OPT("sao")
    {
        int bEnableSao = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->enableSaoFlag = (uint8_t)bEnableSao;
    }
    OPT("keyint")
    {
        bool bIntraPeriodLengthError = false;
        int intraPeriodLength = parseOptionIntValue(value, bIntraPeriodLengthError);
        bError |= bIntraPeriodLengthError;
        if (!bIntraPeriodLengthError)
            svtHevcParam->intraPeriodLength = intraPeriodLength;
    }
    OPT("constrained-intra")
    {
        int constrainedIntra = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->constrainedIntra = (uint8_t)constrainedIntra;
    }
    OPT("vui-timing-info")
    {
        int videoUsabilityInfo = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->videoUsabilityInfo = videoUsabilityInfo;
    }
    OPT("hdr")
    {
        int highDynamicRangeInput = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->highDynamicRangeInput = highDynamicRangeInput;
    }
    OPT("aud")
    {
        int accessUnitDelimiter = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->accessUnitDelimiter = accessUnitDelimiter;
    }
    OPT("qp")
    {
        bool bQpValueError = false;
        int qp = parseOptionIntValue(value, bQpValueError);
        bError |= bQpValueError;
        if (!bQpValueError)
        {
            svtHevcParam->rateControlMode = 0;
            svtHevcParam->qp = qp;
        }
    }
    OPT("bitrate")
    {
        bool bBitrateValueError = false;
        int bitrate = parseOptionIntValue(value, bBitrateValueError);
        bError |= bBitrateValueError;
        if (!bBitrateValueError)
        {
            svtHevcParam->rateControlMode = 1;
            svtHevcParam->targetBitRate = bitrate;
        }
    }
    OPT("interlace")
    {
        bool bInterlacedVideoError = false;
        int interlacedVideo = x265_atobool(value, bInterlacedVideoError);
        bError |= bInterlacedVideoError;
        if (!bInterlacedVideoError)
        {
            svtHevcParam->interlacedVideo = (uint8_t)interlacedVideo;
            if (svtHevcParam->interlacedVideo)
                svtHevcParam->interlacedVideo = 1;
        }
    }
    OPT("svt-hme")
    {
        int bEnableHme = x265_atobool(value, bError);
        if (!bError)
        {
            svtHevcParam->enableHmeFlag = (uint8_t)bEnableHme;
            if (svtHevcParam->enableHmeFlag)
                svtHevcParam->useDefaultMeHme = 1;
        }
    }
    OPT("svt-search-width")
    {
        bool bSearchAreaWidthError = false;
        int searchAreaWidth = parseOptionIntValue(value, bSearchAreaWidthError);
        bError |= bSearchAreaWidthError;
        if (!bSearchAreaWidthError)
            svtHevcParam->searchAreaWidth = searchAreaWidth;
    }
    OPT("svt-search-height")
    {
        bool bSearchAreaHeightError = false;
        int searchAreaHeight = parseOptionIntValue(value, bSearchAreaHeightError);
        bError |= bSearchAreaHeightError;
        if (!bSearchAreaHeightError)
            svtHevcParam->searchAreaHeight = searchAreaHeight;
    }
    OPT("svt-compressed-ten-bit-format")
    {
        int compressedTenBitFormat = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->compressedTenBitFormat = compressedTenBitFormat;
    }
    OPT("svt-speed-control")
    {
        int speedControlFlag = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->speedControlFlag = speedControlFlag;
    }
    OPT("preset") bError |= svt_set_preset(param, value) < 0;
    OPT("svt-preset-tuner")
    {
        if (svtHevcParam->encMode == 2)
        {
            if (!strcmp(value, "0")) svtHevcParam->encMode = 0;
            else if (!strcmp(value, "1")) svtHevcParam->encMode = 1;
            else
            {
                x265_log(param, X265_LOG_ERROR, " Unsupported value=%s for svt-preset-tuner \n", value);
                bError = true;
            }
        }
        else
            x265_log(param, X265_LOG_WARNING, " svt-preset-tuner should be used only with ultrafast preset; Ignoring it \n");
    }
    OPT("svt-hierarchical-level")
    {
        bool bHierarchicalLevelsError = false;
        int hierarchicalLevels = parseOptionIntValue(value, bHierarchicalLevelsError);
        bError |= bHierarchicalLevelsError;
        if (!bHierarchicalLevelsError)
            svtHevcParam->hierarchicalLevels = hierarchicalLevels;
    }
    OPT("svt-base-layer-switch-mode")
    {
        bool bBaseLayerSwitchModeError = false;
        int baseLayerSwitchMode = parseOptionIntValue(value, bBaseLayerSwitchModeError);
        bError |= bBaseLayerSwitchModeError;
        if (!bBaseLayerSwitchModeError)
            svtHevcParam->baseLayerSwitchMode = baseLayerSwitchMode;
    }
    OPT("svt-pred-struct")
    {
        bool bPredStructureError = false;
        uint8_t predStructure = parseOptionUint8Value(value, bPredStructureError);
        bError |= bPredStructureError;
        if (!bPredStructureError)
            svtHevcParam->predStructure = predStructure;
    }
    OPT("svt-fps-in-vps")
    {
        int fpsInVps = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->fpsInVps = (uint8_t)fpsInVps;
    }
    OPT("master-display")
    {
        bool bMasterDisplayError = false;
        uint8_t useMasteringDisplayColorVolume = parseOptionUint8Value(value, bMasterDisplayError);
        bError |= bMasterDisplayError;
        if (!bMasterDisplayError)
            svtHevcParam->useMasteringDisplayColorVolume = useMasteringDisplayColorVolume;
    }
    OPT("max-cll")
    {
        uint16_t maxCLL = 0;
        uint16_t maxFALL = 0;
        bool bLocalError = !parseOptionUint16Pair(value, ',', maxCLL, maxFALL);
        if (!bLocalError)
        {
            svtHevcParam->maxCLL = maxCLL;
            svtHevcParam->maxFALL = maxFALL;
        }
        bError |= bLocalError;
    }
    OPT("nalu-file")
    {
        bool bNaluFileError = false;
        uint8_t useNaluFile = parseOptionUint8Value(value, bNaluFileError);
        bError |= bNaluFileError;
        if (!bNaluFileError)
            svtHevcParam->useNaluFile = useNaluFile;
    }
    OPT("dolby-vision-profile")
    {
        if (!parseTenthsOrIntegerLevel(value, svtHevcParam->dolbyVisionProfile))
            bError = true;
    }
    OPT("hrd")
    {
        int hrdFlag = x265_atobool(value, bError);
        if (!bError)
            svtHevcParam->hrdFlag = (uint32_t)hrdFlag;
    }
    OPT("vbv-maxrate")
    {
        bool bVbvMaxrateError = false;
        int vbvMaxrate = parseOptionIntValue(value, bVbvMaxrateError);
        bError |= bVbvMaxrateError;
        if (!bVbvMaxrateError)
            svtHevcParam->vbvMaxrate = (uint32_t)vbvMaxrate;
    }
    OPT("vbv-bufsize")
    {
        bool bVbvBufsizeError = false;
        int vbvBufsize = parseOptionIntValue(value, bVbvBufsizeError);
        bError |= bVbvBufsizeError;
        if (!bVbvBufsizeError)
            svtHevcParam->vbvBufsize = (uint32_t)vbvBufsize;
    }
    OPT("vbv-init")
    {
        bool bVbvBufInitError = false;
        double vbvBufInit = 0.0;
        bVbvBufInitError = !parseOptionDoubleToken(value, std::strlen(value), vbvBufInit);
        bError |= bVbvBufInitError;
        if (!bVbvBufInitError)
            svtHevcParam->vbvBufInit = (uint64_t)vbvBufInit;
    }
    OPT("frame-threads")
    {
        bool bThreadCountError = false;
        int threadCount = parseOptionIntValue(value, bThreadCountError);
        bError |= bThreadCountError;
        if (!bThreadCountError)
            svtHevcParam->threadCount = (uint32_t)threadCount;
    }
    else
        x265_log(param, X265_LOG_INFO, "SVT doesn't support %s param; Disabling it \n", name);


    return bError ? X265_PARAM_BAD_VALUE : 0;
}

#endif //ifdef SVT_HEVC

}
