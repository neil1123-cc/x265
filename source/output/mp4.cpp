/****************************************************************************
 * Copyright (C) 2026 x265 project
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *****************************************************************************/

#include "mp4.h"

#include <inttypes.h>
#include <limits.h>
#include <string.h>
#include <vector>

using namespace X265_NS;

#define NALU_LENGTH_SIZE 4
#define MP4_LOG_ERROR(...) general_log(NULL, "mp4", X265_LOG_ERROR, __VA_ARGS__)

#define MP4_FAIL_IF(cond, ...) \
if (cond) \
{ \
    MP4_LOG_ERROR(__VA_ARGS__); \
    m_fail = true; \
    return false; \
}

#define MP4_FAIL_IF_RET(cond, ret, ...) \
if (cond) \
{ \
    MP4_LOG_ERROR(__VA_ARGS__); \
    m_fail = true; \
    return ret; \
}

static uint32_t gcdU32(uint32_t a, uint32_t b)
{
    while (b)
    {
        uint32_t t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static bool checkedAddInt64(int64_t a, int64_t b, int64_t& out)
{
    if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b))
        return false;
    out = a + b;
    return true;
}

static bool checkedSubInt64(int64_t a, int64_t b, int64_t& out)
{
    if ((b > 0 && a < INT64_MIN + b) || (b < 0 && a > INT64_MAX + b))
        return false;
    out = a - b;
    return true;
}

static bool checkedMulInt64(int64_t a, int64_t b, int64_t& out)
{
    if (!a || !b)
    {
        out = 0;
        return true;
    }

    if ((a == -1 && b == INT64_MIN) || (b == -1 && a == INT64_MIN))
        return false;

    if ((a > 0 && b > 0 && a > INT64_MAX / b)
        || (a > 0 && b < 0 && b < INT64_MIN / a)
        || (a < 0 && b > 0 && a < INT64_MIN / b)
        || (a < 0 && b < 0 && a < INT64_MAX / b))
        return false;

    out = a * b;
    return true;
}

static bool checkedMulU64(uint64_t a, uint64_t b, uint64_t& out)
{
    if (!a || !b)
    {
        out = 0;
        return true;
    }

    if (a > UINT64_MAX / b)
        return false;

    out = a * b;
    return true;
}

static uint32_t getNalPayloadType(const x265_nal& nal)
{
    return (nal.payload[NALU_LENGTH_SIZE] >> 1) & 0x3f;
}

static uint8_t getNalTemporalId(const x265_nal& nal)
{
    return (nal.payload[NALU_LENGTH_SIZE + 1] & 0x07) - 1;
}

static bool isSeiNalType(uint32_t nalType)
{
    return nalType == NAL_UNIT_PREFIX_SEI || nalType == NAL_UNIT_SUFFIX_SEI;
}

static bool findHeaderParameterSetOffset(const x265_nal* nal, uint32_t nalcount, uint32_t& offset)
{
    offset = 0;
    while (offset < nalcount && nal[offset].type == NAL_UNIT_ACCESS_UNIT_DELIMITER)
        offset++;

    return nalcount - offset >= 3
        && nal[offset].type == NAL_UNIT_VPS
        && nal[offset + 1].type == NAL_UNIT_SPS
        && nal[offset + 2].type == NAL_UNIT_PPS;
}

static bool validateParameterSetTriplet(const x265_nal* paramSetNal, const uint32_t expectedTypes[3],
                                        const char* missingPayloadMessage, const char* invalidSizeMessage,
                                        const char* invalidTypeMessage)
{
    for (uint32_t i = 0; i < 3; i++)
    {
        if (!paramSetNal[i].payload)
        {
            MP4_LOG_ERROR("%s", missingPayloadMessage);
            return false;
        }
        if (paramSetNal[i].sizeBytes <= NALU_LENGTH_SIZE)
        {
            MP4_LOG_ERROR("%s", invalidSizeMessage);
            return false;
        }
        if (getNalPayloadType(paramSetNal[i]) != expectedTypes[i])
        {
            MP4_LOG_ERROR("%s", invalidTypeMessage);
            return false;
        }
    }
    return true;
}

static void freeTemporaryParameterState(uint8_t* paramSetBuffer[3], uint8_t* seiBuffer)
{
    for (uint32_t i = 0; i < 3; i++)
        delete[] paramSetBuffer[i];
    delete[] seiBuffer;
}

static bool validateHeaderSeiNal(const x265_nal& nal, const char* nonSeiMessage,
                                 const char* missingPayloadMessage, const char* invalidSizeMessage,
                                 const char* invalidTypeMessage)
{
    if (!isSeiNalType(nal.type))
    {
        MP4_LOG_ERROR("%s", nonSeiMessage);
        return false;
    }
    if (!nal.payload)
    {
        MP4_LOG_ERROR("%s", missingPayloadMessage);
        return false;
    }
    if (nal.sizeBytes <= NALU_LENGTH_SIZE)
    {
        MP4_LOG_ERROR("%s", invalidSizeMessage);
        return false;
    }
    if (getNalPayloadType(nal) != nal.type)
    {
        MP4_LOG_ERROR("%s", invalidTypeMessage);
        return false;
    }
    return true;
}

struct SamplePreparation
{
    bool hasLeadingVcl;
    bool hasRadl;
    bool hasRecoveryPoint;
    bool hasSublayerNonRef;
    uint8_t sampleTemporalId;
    bool sampleTemporalIdSet;
    bool keyframe;
    int32_t recoveryPocCnt;
    int64_t pts;
    int64_t dts;
    int sampleSize;
    uint64_t sampleDts;
    uint64_t sampleCts;
};

static size_t convertNalToRbsp(const uint8_t* payload, size_t payloadSize, std::vector<uint8_t>& rbsp)
{
    rbsp.clear();
    rbsp.reserve(payloadSize);
    int zeroCount = 0;
    for (size_t i = 0; i < payloadSize; i++)
    {
        uint8_t byte = payload[i];
        if (zeroCount == 2 && byte == 0x03)
        {
            zeroCount = 0;
            continue;
        }
        rbsp.push_back(byte);
        if (!byte)
            zeroCount++;
        else
            zeroCount = 0;
    }
    return rbsp.size();
}

class BitReader
{
public:
    BitReader(const uint8_t* data, size_t sizeBytes)
        : m_data(data), m_sizeBits(sizeBytes * 8), m_bitPos(0)
    {
    }

    bool readBits(uint32_t numBits, uint32_t& value)
    {
        if (!numBits || numBits > 32 || m_bitPos + numBits > m_sizeBits)
            return false;
        value = 0;
        for (uint32_t i = 0; i < numBits; i++)
        {
            size_t bytePos = (m_bitPos + i) >> 3;
            uint32_t bitOffset = 7 - (uint32_t)((m_bitPos + i) & 7);
            value = (value << 1) | ((m_data[bytePos] >> bitOffset) & 1);
        }
        m_bitPos += numBits;
        return true;
    }

    bool readFlag(bool& value)
    {
        uint32_t bit = 0;
        if (!readBits(1, bit))
            return false;
        value = bit != 0;
        return true;
    }

    bool readUe(uint32_t& value)
    {
        uint32_t leadingZeroBits = 0;
        while (true)
        {
            if (m_bitPos >= m_sizeBits)
                return false;
            uint32_t bit = 0;
            if (!readBits(1, bit))
                return false;
            if (bit)
                break;
            leadingZeroBits++;
            if (leadingZeroBits > 31)
                return false;
        }
        if (!leadingZeroBits)
        {
            value = 0;
            return true;
        }
        uint32_t suffix = 0;
        if (!readBits(leadingZeroBits, suffix))
            return false;
        value = ((1u << leadingZeroBits) - 1) + suffix;
        return true;
    }

    bool readSe(int32_t& value)
    {
        uint32_t codeNum = 0;
        if (!readUe(codeNum))
            return false;
        if (codeNum & 1)
            value = (int32_t)((codeNum + 1) >> 1);
        else
            value = -(int32_t)(codeNum >> 1);
        return true;
    }

private:
    const uint8_t* m_data;
    size_t m_sizeBits;
    size_t m_bitPos;
};

static bool parseRecoveryPointSeiPayload(const uint8_t* payload, size_t payloadSize, int32_t& recoveryPocCnt)
{
    std::vector<uint8_t> rbsp;
    convertNalToRbsp(payload, payloadSize, rbsp);
    if (rbsp.size() <= 2)
        return false;

    size_t offset = 2;
    while (offset < rbsp.size())
    {
        uint32_t payloadType = 0;
        while (offset < rbsp.size())
        {
            uint32_t byte = rbsp[offset++];
            payloadType += byte;
            if (byte != 0xff)
                break;
        }
        if (offset >= rbsp.size())
            return false;

        uint32_t payloadSizeValue = 0;
        while (offset < rbsp.size())
        {
            uint32_t byte = rbsp[offset++];
            payloadSizeValue += byte;
            if (byte != 0xff)
                break;
        }
        if (offset > rbsp.size() || rbsp.size() - offset < payloadSizeValue)
            return false;

        if (payloadType == RECOVERY_POINT)
        {
            BitReader reader(rbsp.data() + offset, payloadSizeValue);
            bool ignoredFlag = false;
            if (!reader.readSe(recoveryPocCnt)
                || !reader.readFlag(ignoredFlag)
                || !reader.readFlag(ignoredFlag))
                return false;
            return true;
        }

        offset += payloadSizeValue;
    }

    return false;
}

MP4Muxer::MP4Muxer()
{
    m_fail = false;
    m_root = NULL;
    m_summary = NULL;
    m_seiBuffer = NULL;
    m_brands.fill(static_cast<lsmash_brand_type>(0));
    memset(m_paramSetBuffer, 0, sizeof(m_paramSetBuffer));
    resetRuntimeState();
}

MP4Muxer::~MP4Muxer()
{
    cleanupHandle();
}

bool MP4Muxer::validateParameterState(const char* partialMessage, const char* incompleteMessage) const
{
    bool validState = true;
    if (!m_paramConfigured && ((m_track != 0) || m_movieTimescale || m_videoTimescale || m_timeInc))
    {
        MP4_LOG_ERROR("%s", partialMessage);
        validState = false;
    }
    if (incompleteMessage && (!m_paramConfigured || !(m_timeInc && m_movieTimescale && m_videoTimescale)))
    {
        MP4_LOG_ERROR("%s", incompleteMessage);
        validState = false;
    }
    return validState;
}

bool MP4Muxer::isFirstSample() const
{
    return !m_numFrames;
}

bool MP4Muxer::finalizeTimeline(int64_t largestPts, int64_t lastDelta)
{
    if (!(m_timeInc && m_movieTimescale && m_videoTimescale))
    {
        MP4_LOG_ERROR("timescale is broken.\n");
        return false;
    }

    int64_t endPts = 0;
    if (!checkedAddInt64(largestPts, lastDelta, endPts))
    {
        MP4_LOG_ERROR("timestamp overflow while deriving end PTS during finalize.\n");
        return false;
    }

    uint64_t scaledEndU = 0;
    if (!scaleTimestampWithOffset(endPts, "timestamp overflow while preparing end timestamp during finalize.\n",
                                  "timestamp overflow while scaling end timestamp during finalize.\n",
                                  "invalid scaled end timestamp during finalize.\n", scaledEndU))
        return false;
    if (scaledEndU < m_firstCts)
    {
        MP4_LOG_ERROR("edit end timestamp precedes first CTS during finalize.\n");
        return false;
    }

    uint64_t scaledLastCts = 0;
    if (!scaleTimestampWithOffset(m_lastPts, "timestamp overflow while preparing last CTS during finalize.\n",
                                  "timestamp overflow while scaling last CTS during finalize.\n",
                                  "invalid scaled last CTS during finalize.\n", scaledLastCts))
        return false;
    if (scaledEndU <= scaledLastCts)
    {
        MP4_LOG_ERROR("invalid sample delta during finalize.\n");
        return false;
    }

    uint64_t scaledLastDelta = scaledEndU - scaledLastCts;
    uint64_t mediaDuration = scaledEndU - m_firstCts;
    if (scaledLastDelta > UINT32_MAX)
    {
        MP4_LOG_ERROR("sample delta overflow during finalize.\n");
        return false;
    }

    uint32_t sampleDelta = (uint32_t)scaledLastDelta;

    if (lsmash_flush_pooled_samples(m_root, m_track, sampleDelta))
    {
        MP4_LOG_ERROR("failed to flush pooled samples.\n");
        return false;
    }

    uint64_t flushedMediaDuration = lsmash_get_media_duration(m_root, m_track);
    if (!flushedMediaDuration)
    {
        MP4_LOG_ERROR("media duration is broken after flushing MP4 samples.\n");
        return false;
    }
    if (flushedMediaDuration != mediaDuration)
    {
        MP4_LOG_ERROR("flushed media duration does not match finalized MP4 media duration.\n");
        return false;
    }

    uint64_t actualDuration = 0;
    uint64_t q = flushedMediaDuration / m_videoTimescale;
    uint64_t r = flushedMediaDuration % m_videoTimescale;
    if (q > UINT64_MAX / m_movieTimescale)
    {
        MP4_LOG_ERROR("duration overflow during finalize.\n");
        return false;
    }
    actualDuration = q * m_movieTimescale;

    uint64_t fractionalNumerator = 0;
    if (!checkedMulU64(r, m_movieTimescale, fractionalNumerator))
    {
        MP4_LOG_ERROR("duration overflow while scaling movie duration remainder.\n");
        return false;
    }
    uint64_t truncatedFraction = fractionalNumerator / m_videoTimescale;
    if (UINT64_MAX - actualDuration < truncatedFraction)
    {
        MP4_LOG_ERROR("duration overflow while adding truncated fraction.\n");
        return false;
    }
    actualDuration += truncatedFraction;
    if (flushedMediaDuration && !actualDuration)
        actualDuration = 1;

    lsmash_edit_t edit = {};
    edit.duration = actualDuration;
    edit.start_time = m_firstCts;
    edit.rate = ISOM_EDIT_MODE_NORMAL;
    if (lsmash_create_explicit_timeline_map(m_root, m_track, edit))
    {
        MP4_LOG_ERROR("failed to create explicit timeline map for video.\n");
        return false;
    }

    return true;
}

bool MP4Muxer::analyzeSampleNals(const ContainerSample& sample, bool& hasLeadingVcl, bool& hasRadl,
                                 bool& hasRecoveryPoint, bool& hasSublayerNonRef, bool& sampleTemporalIdSet,
                                 uint8_t& sampleTemporalId, bool& keyframe, int32_t& recoveryPocCnt)
{
    bool hasIRAP = false;
    bool hasVcl = false;
    hasLeadingVcl = false;
    hasRadl = false;
    hasRecoveryPoint = false;
    hasSublayerNonRef = false;
    sampleTemporalId = 0;
    sampleTemporalIdSet = false;
    recoveryPocCnt = 0;

    for (uint32_t i = 0; i < sample.nalCount; i++)
    {
        uint32_t nalType = sample.nal[i].type;
        MP4_FAIL_IF(nalType == NAL_UNIT_VPS || nalType == NAL_UNIT_SPS || nalType == NAL_UNIT_PPS,
                    "MP4 frame sample must not contain VPS/SPS/PPS NAL units.\n");
        MP4_FAIL_IF(nalType == NAL_UNIT_ACCESS_UNIT_DELIMITER,
                    "MP4 frame sample must not contain AUD NAL units.\n");
        MP4_FAIL_IF(nalType == NAL_UNIT_FILLER_DATA,
                    "MP4 hvc1 samples must not contain filler data NAL units.\n");
        MP4_FAIL_IF(nalType == NAL_UNIT_EOS || nalType == NAL_UNIT_EOB,
                    "MP4 frame sample must not contain EOS or EOB NAL units.\n");
        MP4_FAIL_IF(!sample.nal[i].payload, "missing NAL payload pointer in sample.\n");
        MP4_FAIL_IF(sample.nal[i].sizeBytes <= NALU_LENGTH_SIZE, "invalid empty NAL in sample.\n");
        MP4_FAIL_IF(getNalPayloadType(sample.nal[i]) != nalType,
                    "NAL payload type does not match MP4 sample metadata.\n");
        if (nalType <= NAL_UNIT_CODED_SLICE_CRA)
        {
            uint8_t nalTemporalId = getNalTemporalId(sample.nal[i]);
            if (!sampleTemporalIdSet)
            {
                sampleTemporalId = nalTemporalId;
                sampleTemporalIdSet = true;
            }
            else
                MP4_FAIL_IF(sampleTemporalId != nalTemporalId,
                            "inconsistent temporal id across VCL NAL units in MP4 sample.\n");
            hasVcl = true;
            hasSublayerNonRef |= (nalType <= NAL_UNIT_CODED_SLICE_RASL_R) && ((nalType & 1) == 0);
            if (nalType == NAL_UNIT_CODED_SLICE_RADL_N || nalType == NAL_UNIT_CODED_SLICE_RADL_R)
            {
                hasLeadingVcl = true;
                hasRadl = true;
            }
            else if (nalType == NAL_UNIT_CODED_SLICE_RASL_N || nalType == NAL_UNIT_CODED_SLICE_RASL_R)
                hasLeadingVcl = true;
            if (nalType >= NAL_UNIT_CODED_SLICE_BLA_W_LP)
                hasIRAP = true;
        }
        else if (nalType == NAL_UNIT_PREFIX_SEI)
        {
            int32_t parsedRecoveryPocCnt = 0;
            if (parseRecoveryPointSeiPayload(sample.nal[i].payload + NALU_LENGTH_SIZE,
                                             sample.nal[i].sizeBytes - NALU_LENGTH_SIZE,
                                             parsedRecoveryPocCnt))
            {
                hasRecoveryPoint = true;
                recoveryPocCnt = parsedRecoveryPocCnt;
            }
        }
    }

    MP4_FAIL_IF(!hasVcl, "MP4 sample is missing a VCL NAL unit.\n");
    MP4_FAIL_IF(isFirstSample() && hasLeadingVcl,
                "first MP4 sample must not contain RADL or RASL pictures.\n");

    keyframe = hasIRAP;
    MP4_FAIL_IF(isFirstSample() && !keyframe, "first MP4 sample must be an IRAP access unit.\n");
    return true;
}

bool MP4Muxer::fail()
{
    m_fail = true;
    return false;
}

int MP4Muxer::failWrite()
{
    m_fail = true;
    return -1;
}

bool MP4Muxer::scaleTimestampWithOffset(int64_t ts, const char* prepareError, const char* scaleError,
                                        const char* invalidError, uint64_t& scaledTs) const
{
    int64_t tsWithOffset = 0;
    if (!checkedAddInt64(ts, m_startOffset, tsWithOffset))
    {
        MP4_LOG_ERROR("%s", prepareError);
        return false;
    }

    int64_t scaledInput = 0;
    if (!checkedMulInt64(tsWithOffset, (int64_t)m_timeInc, scaledInput))
    {
        MP4_LOG_ERROR("%s", scaleError);
        return false;
    }

    int64_t scaledValue = getTimeScaled(scaledInput);
    if (scaledValue < 0)
    {
        MP4_LOG_ERROR("%s", invalidError);
        return false;
    }

    scaledTs = (uint64_t)scaledValue;
    return true;
}

bool MP4Muxer::scaleSampleTimestamps(int64_t pts, int64_t dts, uint64_t& sampleDts, uint64_t& sampleCts)
{
    if (isFirstSample())
    {
        if (dts == INT64_MIN)
        {
            MP4_LOG_ERROR("timestamp overflow while deriving start offset.\n");
            return false;
        }
        m_startOffset = -dts;
    }

    if (!scaleTimestampWithOffset(dts, "timestamp overflow while preparing DTS.\n",
                                  "timestamp overflow while scaling DTS.\n",
                                  "negative timestamp after scaling.\n", sampleDts))
        return false;
    if (!scaleTimestampWithOffset(pts, "timestamp overflow while preparing CTS.\n",
                                  "timestamp overflow while scaling CTS.\n",
                                  "negative timestamp after scaling.\n", sampleCts))
        return false;
    if (sampleCts < sampleDts)
    {
        MP4_LOG_ERROR("CTS precedes DTS after scaling.\n");
        return false;
    }

    return true;
}

void MP4Muxer::clearBufferedParameterSets()
{
    for (uint32_t i = 0; i < 3; i++)
    {
        delete[] m_paramSetBuffer[i];
        m_paramSetBuffer[i] = NULL;
        m_paramSetSize[i] = 0;
    }
}

void MP4Muxer::clearBufferedSeiState()
{
    delete[] m_seiBuffer;
    m_seiBuffer = NULL;
    m_seiSize = 0;
}

void MP4Muxer::resetRuntimeState()
{
    m_paramConfigured = false;
    m_timebaseNum = 0;
    m_timebaseDenom = 0;
    m_maxTemporalId = 0;
    memset(&m_fileParam, 0, sizeof(m_fileParam));
    m_fileOpen = false;
    m_brands.fill(static_cast<lsmash_brand_type>(0));
    m_movieTimescale = 0;
    m_videoTimescale = 0;
    m_track = 0;
    m_sampleEntry = 0;
    m_timeInc = 0;
    m_startOffset = 0;
    m_firstCts = 0;
    m_prevDts = 0;
    m_lastIntraCts = 0;
    m_lastPts = 0;
    m_secondLastPts = 0;
    m_seiSize = 0;
    memset(m_paramSetSize, 0, sizeof(m_paramSetSize));
    m_numFrames = 0;
    m_oldTimescale = 0;
    m_fpsNum = 0;
    m_fpsDenom = 0;
    m_fpsScale = 0;
}

void MP4Muxer::fixTimeScale(uint64_t& mediaTimescale, uint32_t fpsDenom)
{
    m_oldTimescale = 0;
    m_fpsScale = 1;

    if (fpsDenom && fpsDenom % 1001 == 0)
        m_fpsScale = fpsDenom / 1001;

    if (mediaTimescale <= UINT32_MAX)
        return;

    m_oldTimescale = mediaTimescale;
    while (mediaTimescale > UINT32_MAX)
        mediaTimescale = (mediaTimescale + 1) / 2;
}

#define MAX_OFFSET 50

int64_t MP4Muxer::getTimeScaled(int64_t ts) const
{
    if (!m_oldTimescale)
        return ts;

    int64_t scaledTs = 0;
    if (!checkedMulInt64(ts, (int64_t)m_videoTimescale, scaledTs))
    {
        MP4_LOG_ERROR("timestamp overflow while rescaling timebase.\n");
        return INT64_MIN;
    }
    const int64_t oldTimescale = (int64_t)m_oldTimescale;
    ts = scaledTs / oldTimescale;
    if ((scaledTs % oldTimescale) < 0)
        ts--;

    if (!m_fpsDenom)
    {
        MP4_LOG_ERROR("invalid fps denominator while scaling timestamp.\n");
        return INT64_MIN;
    }
    int64_t offsetBase = 0;
    if (!checkedMulInt64((int64_t)MAX_OFFSET, (int64_t)m_fpsScale, offsetBase))
    {
        MP4_LOG_ERROR("timestamp overflow while deriving offset base.\n");
        return INT64_MIN;
    }

    int64_t bias = offsetBase % m_fpsDenom;
    if (bias < 0)
        bias += m_fpsDenom;

    int64_t tsWithBias = 0;
    if (!checkedAddInt64(ts, bias, tsWithBias))
    {
        MP4_LOG_ERROR("timestamp overflow while deriving offset.\n");
        return INT64_MIN;
    }
    int64_t offset = tsWithBias % m_fpsDenom;
    if (offset < 0)
        offset += m_fpsDenom;

    int64_t biasWindow = 0;
    if (!checkedMulInt64(bias, 2, biasWindow))
    {
        MP4_LOG_ERROR("timestamp overflow while deriving offset window.\n");
        return INT64_MIN;
    }
    if (offset <= biasWindow)
    {
        int64_t adjust = 0;
        if (!checkedSubInt64(offset, bias, adjust))
        {
            MP4_LOG_ERROR("timestamp overflow while deriving offset adjustment.\n");
            return INT64_MIN;
        }
        int64_t adjustedTs = 0;
        if (!checkedSubInt64(ts, adjust, adjustedTs))
        {
            MP4_LOG_ERROR("timestamp overflow while applying offset adjustment.\n");
            return INT64_MIN;
        }
        ts = adjustedTs;
    }

    return ts;
}

void MP4Muxer::cleanupHandle()
{
    if (m_summary)
    {
        lsmash_cleanup_summary((lsmash_summary_t*)m_summary);
        m_summary = NULL;
    }
    if (m_root)
    {
        if (m_fileOpen)
        {
            lsmash_close_file(&m_fileParam);
            m_fileOpen = false;
        }
        lsmash_destroy_root(m_root);
        m_root = NULL;
    }
    clearBufferedSeiState();
    clearBufferedParameterSets();
    resetRuntimeState();
}

void MP4Muxer::cleanupOutputFile()
{
    if (!m_filename.empty())
        x265_unlink(m_filename.c_str());
}

void MP4Muxer::sign()
{
    if (!m_root)
        return;

    const char* text = "Multiplexed by L-SMASH";
    int length = (int)strlen(text);
    lsmash_box_type_t type = lsmash_form_iso_box_type(LSMASH_4CC('f', 'r', 'e', 'e'));
    lsmash_box_t* freeBox = lsmash_create_box(type, (uint8_t*)text, length, LSMASH_BOX_PRECEDENCE_N);
    if (!freeBox)
        return;

    if (lsmash_add_box_ex(lsmash_root_as_box(m_root), &freeBox) < 0)
    {
        lsmash_destroy_box(freeBox);
        return;
    }

    lsmash_write_top_level_box(freeBox);
}

bool MP4Muxer::init(const char* fname, const InputFileInfo& info)
{
    MP4_FAIL_IF(!fname || !fname[0], "invalid output filename for MP4 muxer.\n");
    m_timebaseNum = info.timebaseNum;
    m_timebaseDenom = info.timebaseDenom;

    m_filename = fname;

    FILE* fh = x265_fopen(fname, "wb");
    if (!fh)
    {
        MP4_LOG_ERROR("cannot open output file `%s'.\n", fname);
        m_fail = true;
        return false;
    }
    fclose(fh);

    m_root = lsmash_create_root();
    if (!m_root)
    {
        MP4_LOG_ERROR("failed to create root.\n");
        m_fail = true;
        cleanupOutputFile();
        return false;
    }

    if (lsmash_open_file(fname, 0, &m_fileParam) < 0)
    {
        MP4_LOG_ERROR("failed to open output file in L-SMASH.\n");
        m_fail = true;
        cleanupHandle();
        cleanupOutputFile();
        return false;
    }
    m_fileOpen = true;

    m_summary = (lsmash_video_summary_t*)lsmash_create_summary(LSMASH_SUMMARY_TYPE_VIDEO);
    if (!m_summary)
    {
        MP4_LOG_ERROR("failed to allocate summary information for video.\n");
        m_fail = true;
        cleanupHandle();
        cleanupOutputFile();
        return false;
    }
    m_summary->sample_type = ISOM_CODEC_TYPE_HVC1_VIDEO;

    return true;
}

bool MP4Muxer::setParam(const x265_param* param)
{
    if (!(m_root && m_summary))
    {
        MP4_LOG_ERROR("MP4 muxer is not initialized before setting parameters.\n");
        m_fail = true;
        return false;
    }
    if (!param)
    {
        MP4_LOG_ERROR("null encoder parameters for MP4 muxer.\n");
        m_fail = true;
        return false;
    }
    if (!validateParameterState("MP4 muxer reached parameter setup with partial parameter state.\n", NULL))
    {
        m_fail = true;
        return false;
    }
    if ((m_sampleEntry != 0))
    {
        MP4_LOG_ERROR("MP4 sample entry already exists before setting parameters.\n");
        m_fail = true;
        return false;
    }
    if (!isFirstSample())
    {
        MP4_LOG_ERROR("cannot reset MP4 parameters after samples were written.\n");
        m_fail = true;
        return false;
    }
    if (m_seiBuffer || m_seiSize)
    {
        MP4_LOG_ERROR("stale SEI header state detected before setting MP4 parameters.\n");
        m_fail = true;
        return false;
    }
    if (m_paramSetBuffer[0] || m_paramSetBuffer[1] || m_paramSetBuffer[2]
        || m_paramSetSize[0] || m_paramSetSize[1] || m_paramSetSize[2])
    {
        MP4_LOG_ERROR("stale parameter set state detected before setting MP4 parameters.\n");
        m_fail = true;
        return false;
    }

    MP4_FAIL_IF(param->rc.bStrictCbr,
                "MP4 hvc1 output does not support strict-cbr because it may require filler data NAL units.\n");

    const uint32_t fpsNum = param->fpsNum;
    const uint32_t fpsDenom = param->fpsDenom ? param->fpsDenom : 1;

    if (((m_root && m_summary) && (m_track != 0)))
    {
        MP4_FAIL_IF(!(m_timeInc && m_movieTimescale && m_videoTimescale),
                    "MP4 muxer lost timeline state before resetting parameters.\n");
        MP4_FAIL_IF((uint32_t)param->sourceWidth != m_summary->width || (uint32_t)param->sourceHeight != m_summary->height,
                    "cannot change MP4 frame dimensions after track initialization.\n");
        MP4_FAIL_IF(param->vui.sarWidth != (int)m_summary->par_h || param->vui.sarHeight != (int)m_summary->par_v,
                    "cannot change MP4 sample aspect ratio after track initialization.\n");
        MP4_FAIL_IF(param->vui.colorPrimaries != m_summary->color.primaries_index
                    || param->vui.transferCharacteristics != m_summary->color.transfer_index,
                    "cannot change MP4 color primaries or transfer characteristics after track initialization.\n");
        const int unspecifiedMatrixIndex = 2;
        int matrixIndex = param->vui.matrixCoeffs >= 0 ? param->vui.matrixCoeffs : unspecifiedMatrixIndex;
        int fullRange = param->vui.bEnableVideoFullRangeFlag >= 0 ? param->vui.bEnableVideoFullRangeFlag : 0;
        MP4_FAIL_IF(matrixIndex != m_summary->color.matrix_index || fullRange != m_summary->color.full_range,
                    "cannot change MP4 matrix coefficients or range after track initialization.\n");
        MP4_FAIL_IF(fpsNum != m_fpsNum || fpsDenom != m_fpsDenom,
                    "cannot change MP4 frame rate parameters after track initialization.\n");
        m_paramConfigured = true;
        m_maxTemporalId = (param->bEnableTemporalSubLayers > 0)
                       ? (uint8_t)(param->bEnableTemporalSubLayers - 1)
                       : 0;
        m_fpsNum = fpsNum;
        m_fpsDenom = fpsDenom;
        return true;
    }

    MP4_FAIL_IF(m_timebaseDenom <= 0, "input timebase denominator must be positive.\n");
    MP4_FAIL_IF(m_timebaseNum <= 0, "input timebase numerator must be positive.\n");
    MP4_FAIL_IF(param->sourceWidth <= 0 || param->sourceHeight <= 0,
                "source dimensions must be positive for MP4 output.\n");
    MP4_FAIL_IF(param->vui.sarWidth < 0 || param->vui.sarHeight < 0,
                "sample aspect ratio must be non-negative for MP4 output.\n");
    MP4_FAIL_IF((param->vui.sarWidth && !param->vui.sarHeight) || (!param->vui.sarWidth && param->vui.sarHeight),
                "sample aspect ratio must provide both width and height for MP4 output.\n");

    uint64_t mediaTimescale = (uint64_t)m_timebaseDenom;
    uint64_t timeInc = (uint64_t)m_timebaseNum;
    fixTimeScale(mediaTimescale, fpsDenom);
    MP4_FAIL_IF(mediaTimescale > UINT32_MAX,
                "MP4 media timescale %" PRIu64 " exceeds maximum\n", mediaTimescale);

    MP4_FAIL_IF((uint32_t)param->sourceWidth > (UINT32_MAX >> 16) || (uint32_t)param->sourceHeight > (UINT32_MAX >> 16),
                "source dimensions exceed MP4 fixed-point display range.\n");
    uint32_t displayWidth = param->sourceWidth << 16;
    uint32_t displayHeight = param->sourceHeight << 16;
    uint32_t parH = 0;
    uint32_t parV = 0;
    if (param->vui.sarWidth && param->vui.sarHeight)
    {
        uint32_t sarW = param->vui.sarWidth;
        uint32_t sarH = param->vui.sarHeight;
        if (sarW > sarH)
        {
            uint64_t scaledWidth = (uint64_t)displayWidth * sarW;
            uint64_t roundedWidth = (scaledWidth + sarH / 2) / sarH;
            MP4_FAIL_IF(roundedWidth > UINT32_MAX,
                        "display width exceeds MP4 fixed-point range after SAR scaling.\n");
            displayWidth = (uint32_t)roundedWidth;
        }
        else if (sarW < sarH)
        {
            uint64_t scaledHeight = (uint64_t)displayHeight * sarH;
            uint64_t roundedHeight = (scaledHeight + sarW / 2) / sarW;
            MP4_FAIL_IF(roundedHeight > UINT32_MAX,
                        "display height exceeds MP4 fixed-point range after SAR scaling.\n");
            displayHeight = (uint32_t)roundedHeight;
        }

        parH = sarW;
        parV = sarH;
    }

    const int unspecifiedMatrixIndex = 2;
    uint16_t primariesIndex = param->vui.colorPrimaries;
    uint16_t transferIndex = param->vui.transferCharacteristics;
    uint16_t matrixIndex = param->vui.matrixCoeffs >= 0 ? param->vui.matrixCoeffs : unspecifiedMatrixIndex;
    uint8_t fullRange = param->vui.bEnableVideoFullRangeFlag >= 0 ? param->vui.bEnableVideoFullRangeFlag : 0;

    uint32_t brandCount = 0;
    m_brands[brandCount++] = ISOM_BRAND_TYPE_MP42;
    m_brands[brandCount++] = ISOM_BRAND_TYPE_MP41;
    m_brands[brandCount++] = ISOM_BRAND_TYPE_ISOM;

    lsmash_file_parameters_t* fparam = &m_fileParam;
    fparam->major_brand = m_brands[0];
    fparam->brands = m_brands.data();
    fparam->brand_count = brandCount;
    fparam->minor_version = 0;
    MP4_FAIL_IF(!lsmash_set_file(m_root, fparam),
                "failed to add output file into root.\n");

    lsmash_movie_parameters_t movieParam;
    lsmash_initialize_movie_parameters(&movieParam);
    MP4_FAIL_IF(lsmash_set_movie_parameters(m_root, &movieParam),
                "failed to set movie parameters.\n");

    uint32_t movieTimescale = lsmash_get_movie_timescale(m_root);
    MP4_FAIL_IF(!movieTimescale, "movie timescale is broken.\n");

    uint32_t track = lsmash_create_track(m_root, ISOM_MEDIA_HANDLER_TYPE_VIDEO_TRACK);
    MP4_FAIL_IF(!track, "failed to create video track.\n");

    lsmash_track_parameters_t trackParam;
    lsmash_initialize_track_parameters(&trackParam);
    trackParam.mode = static_cast<lsmash_track_mode>(ISOM_TRACK_ENABLED | ISOM_TRACK_IN_MOVIE | ISOM_TRACK_IN_PREVIEW);
    trackParam.display_width = displayWidth;
    trackParam.display_height = displayHeight;
    MP4_FAIL_IF(lsmash_set_track_parameters(m_root, track, &trackParam),
                "failed to set track parameters for video.\n");

    lsmash_media_parameters_t mediaParam;
    lsmash_initialize_media_parameters(&mediaParam);
    mediaParam.timescale = mediaTimescale;
    mediaParam.media_handler_name = strdup("L-SMASH Video Media Handler");
    MP4_FAIL_IF(!mediaParam.media_handler_name,
                "failed to allocate media handler name for video.\n");
    MP4_FAIL_IF(lsmash_set_media_parameters(m_root, track, &mediaParam),
                "failed to set media parameters for video.\n");

    uint32_t videoTimescale = lsmash_get_media_timescale(m_root, track);
    MP4_FAIL_IF(!videoTimescale, "media timescale for video is broken.\n");

    m_paramConfigured = true;
    m_maxTemporalId = (param->bEnableTemporalSubLayers > 0)
                   ? (uint8_t)(param->bEnableTemporalSubLayers - 1)
                   : 0;
    m_numFrames = 0;
    m_track = track;
    m_movieTimescale = movieTimescale;
    m_videoTimescale = videoTimescale;
    m_timeInc = timeInc;
    m_startOffset = 0;
    m_firstCts = 0;
    m_prevDts = 0;
    m_lastIntraCts = 0;
    m_lastPts = 0;
    m_secondLastPts = 0;
    m_fpsNum = fpsNum;
    m_fpsDenom = fpsDenom;

    m_summary->width = param->sourceWidth;
    m_summary->height = param->sourceHeight;
    m_summary->par_h = parH;
    m_summary->par_v = parV;
    m_summary->color.primaries_index = primariesIndex;
    m_summary->color.transfer_index = transferIndex;
    m_summary->color.matrix_index = matrixIndex;
    m_summary->color.full_range = fullRange;

    return true;
}

bool MP4Muxer::configureParameterSets(const x265_nal* nal, uint32_t nalcount)
{
    if (!((m_root && m_summary) && (m_track != 0)))
    {
        MP4_LOG_ERROR("MP4 muxer is not initialized before configuring headers.\n");
        m_fail = true;
        return false;
    }
    if (!validateParameterState("MP4 muxer reached header configuration with partial parameter state.\n",
                                "MP4 muxer parameters are incomplete before configuring headers.\n"))
    {
        m_fail = true;
        return false;
    }
    if ((m_sampleEntry != 0))
    {
        MP4_LOG_ERROR("MP4 sample entry is already configured.\n");
        m_fail = true;
        return false;
    }
    if (!isFirstSample())
    {
        MP4_LOG_ERROR("cannot configure MP4 headers after samples were written.\n");
        m_fail = true;
        return false;
    }
    if (m_seiBuffer || m_seiSize)
    {
        MP4_LOG_ERROR("stale SEI header state detected before configuring MP4 headers.\n");
        m_fail = true;
        return false;
    }
    if (m_paramSetBuffer[0] || m_paramSetBuffer[1] || m_paramSetBuffer[2]
        || m_paramSetSize[0] || m_paramSetSize[1] || m_paramSetSize[2])
    {
        MP4_LOG_ERROR("stale parameter set state detected before configuring MP4 headers.\n");
        m_fail = true;
        return false;
    }
    uint32_t headerOffset = 0;
    if (!nal)
    {
        MP4_LOG_ERROR("null NAL array for MP4 headers.\n");
        m_fail = true;
        return false;
    }
    if (!findHeaderParameterSetOffset(nal, nalcount, headerOffset))
    {
        MP4_LOG_ERROR("MP4 headers must contain optional AUD followed by VPS/SPS/PPS NAL units.\n");
        m_fail = true;
        return false;
    }
    const x265_nal* paramSetNal = nal + headerOffset;

    static const uint32_t expectedParamSetTypes[3] = { NAL_UNIT_VPS, NAL_UNIT_SPS, NAL_UNIT_PPS };
    if (!validateParameterSetTriplet(paramSetNal, expectedParamSetTypes,
                                     "missing VPS/SPS/PPS payload pointer in headers.\n",
                                     "invalid VPS/SPS/PPS size in headers.\n",
                                     "VPS/SPS/PPS payload type does not match MP4 header metadata.\n"))
    {
        m_fail = true;
        return false;
    }

    uint8_t* vps = paramSetNal[0].payload + NALU_LENGTH_SIZE;
    uint8_t* sps = paramSetNal[1].payload + NALU_LENGTH_SIZE;
    uint8_t* pps = paramSetNal[2].payload + NALU_LENGTH_SIZE;
    uint32_t vpsSize = paramSetNal[0].sizeBytes - NALU_LENGTH_SIZE;
    uint32_t spsSize = paramSetNal[1].sizeBytes - NALU_LENGTH_SIZE;
    uint32_t ppsSize = paramSetNal[2].sizeBytes - NALU_LENGTH_SIZE;

    const uint32_t paramSetSize[3] = { vpsSize, spsSize, ppsSize };
    uint8_t* const paramSetPayload[3] = { vps, sps, pps };
    uint8_t* newParamSetBuffer[3] = { NULL, NULL, NULL };
    uint8_t* newSeiBuffer = NULL;
    uint32_t newSeiSize = 0;
    for (uint32_t i = 0; i < 3; i++)
    {
        newParamSetBuffer[i] = new uint8_t[paramSetSize[i]];
        if (!newParamSetBuffer[i])
        {
            newParamSetBuffer[i] = NULL;
            freeTemporaryParameterState(newParamSetBuffer, NULL);
            MP4_LOG_ERROR("failed to allocate parameter set state buffer.\n");
            m_fail = true;
            return false;
        }
        memcpy(newParamSetBuffer[i], paramSetPayload[i], paramSetSize[i]);
    }
    const auto failSeiAssembly = [&](const char* message) {
        freeTemporaryParameterState(newParamSetBuffer, newSeiBuffer);
        if (message)
            MP4_LOG_ERROR("%s", message);
        m_fail = true;
        return false;
    };
    const uint32_t seiOffset = headerOffset + 3;
    newSeiBuffer = NULL;
    newSeiSize = 0;
    if (nalcount > seiOffset)
    {
        uint64_t seiTotalSize = 0;
        for (uint32_t i = seiOffset; i < nalcount; i++)
        {
            if (!validateHeaderSeiNal(nal[i],
                                      "unexpected non-SEI NAL in MP4 header extras.\n",
                                      "missing SEI payload pointer in headers.\n",
                                      "invalid empty SEI in headers.\n",
                                      "SEI payload type does not match MP4 header metadata.\n"))
                return failSeiAssembly(NULL);
            if (UINT64_MAX - seiTotalSize < nal[i].sizeBytes)
                return failSeiAssembly("SEI payload overflow while assembling MP4 headers.\n");
            seiTotalSize += nal[i].sizeBytes;
        }
        if (seiTotalSize > UINT32_MAX)
            return failSeiAssembly("SEI payload too large for MP4 sample assembly.\n");

        newSeiSize = (uint32_t)seiTotalSize;
        newSeiBuffer = new uint8_t[newSeiSize];
        if (!newSeiBuffer)
            return failSeiAssembly("failed to allocate sei transition buffer.\n");

        uint8_t* dst = newSeiBuffer;
        for (uint32_t i = seiOffset; i < nalcount; i++)
        {
            memcpy(dst, nal[i].payload, nal[i].sizeBytes);
            dst += nal[i].sizeBytes;
        }
    }

    const auto failSampleEntry = [&](const char* message, lsmash_codec_specific_t* codecSpecific) {
        if (codecSpecific)
            lsmash_destroy_codec_specific_data(codecSpecific);
        freeTemporaryParameterState(newParamSetBuffer, newSeiBuffer);
        MP4_LOG_ERROR("%s", message);
        m_fail = true;
        return false;
    };
    lsmash_codec_specific_t* cs = lsmash_create_codec_specific_data(LSMASH_CODEC_SPECIFIC_DATA_TYPE_ISOM_VIDEO_HEVC,
                                                                     LSMASH_CODEC_SPECIFIC_FORMAT_STRUCTURED);
    if (!cs)
        return failSampleEntry("failed to create codec specific data.\n", cs);

    lsmash_hevc_specific_parameters_t* hevc = (lsmash_hevc_specific_parameters_t*)cs->data.structured;
    hevc->lengthSizeMinusOne = NALU_LENGTH_SIZE - 1;

    if (lsmash_append_hevc_dcr_nalu(hevc, HEVC_DCR_NALU_TYPE_VPS, vps, vpsSize)
        || lsmash_append_hevc_dcr_nalu(hevc, HEVC_DCR_NALU_TYPE_SPS, sps, spsSize)
        || lsmash_append_hevc_dcr_nalu(hevc, HEVC_DCR_NALU_TYPE_PPS, pps, ppsSize))
        return failSampleEntry("failed to append VPS/SPS/PPS to hvcC.\n", cs);

    if (lsmash_add_codec_specific_data((lsmash_summary_t*)m_summary, cs))
        return failSampleEntry("failed to add HEVC codec specific info.\n", cs);
    lsmash_destroy_codec_specific_data(cs);

    uint32_t sampleEntry = lsmash_add_sample_entry(m_root, m_track, m_summary);
    if (!sampleEntry)
        return failSampleEntry("failed to add sample entry for video.\n", NULL);

    m_sampleEntry = sampleEntry;
    for (uint32_t i = 0; i < 3; i++)
    {
        m_paramSetBuffer[i] = newParamSetBuffer[i];
        m_paramSetSize[i] = paramSetSize[i];
    }
    m_seiBuffer = newSeiBuffer;
    m_seiSize = newSeiSize;

    return true;
}

int MP4Muxer::beginStream(const x265_nal* nal, uint32_t nalcount)
{
    if (!((m_root && m_summary) && (m_track != 0)))
    {
        MP4_LOG_ERROR("MP4 muxer is not initialized before beginning stream.\n");
        m_fail = true;
        return -1;
    }
    if (!validateParameterState("MP4 muxer reached stream start with partial parameter state.\n",
                                "MP4 muxer parameters are incomplete before beginning stream.\n"))
    {
        m_fail = true;
        return -1;
    }
    if (!(m_sampleEntry != 0))
    {
        MP4_LOG_ERROR("MP4 headers must be configured before beginning stream.\n");
        m_fail = true;
        return -1;
    }
    if (!isFirstSample())
    {
        MP4_LOG_ERROR("cannot begin MP4 stream after samples were written.\n");
        m_fail = true;
        return -1;
    }
    if ((m_seiBuffer && !m_seiSize) || (!m_seiBuffer && m_seiSize))
    {
        MP4_LOG_ERROR("inconsistent SEI transition state before beginning MP4 stream.\n");
        m_fail = true;
        return -1;
    }
    if (!(m_paramSetBuffer[0] && m_paramSetBuffer[1] && m_paramSetBuffer[2]
          && m_paramSetSize[0] && m_paramSetSize[1] && m_paramSetSize[2]))
    {
        MP4_LOG_ERROR("missing configured VPS/SPS/PPS state before beginning MP4 stream.\n");
        m_fail = true;
        return -1;
    }
    if (!nal)
    {
        MP4_LOG_ERROR("null NAL array for stream headers.\n");
        m_fail = true;
        return -1;
    }
    uint32_t headerOffset = 0;
    if (!findHeaderParameterSetOffset(nal, nalcount, headerOffset))
    {
        MP4_LOG_ERROR("MP4 stream headers must contain optional AUD followed by VPS/SPS/PPS NAL units.\n");
        m_fail = true;
        return -1;
    }

    const x265_nal* paramSetNal = nal + headerOffset;
    static const uint32_t expectedParamSetTypes[3] = { NAL_UNIT_VPS, NAL_UNIT_SPS, NAL_UNIT_PPS };
    if (!validateParameterSetTriplet(paramSetNal, expectedParamSetTypes,
                                     "missing VPS/SPS/PPS payload pointer in stream headers.\n",
                                     "invalid VPS/SPS/PPS size in stream headers.\n",
                                     "NAL payload type does not match MP4 stream header metadata.\n"))
    {
        m_fail = true;
        return -1;
    }

    for (uint32_t i = 0; i < 3; i++)
    {
        uint32_t payloadSize = paramSetNal[i].sizeBytes - NALU_LENGTH_SIZE;
        if (payloadSize != m_paramSetSize[i])
        {
            MP4_LOG_ERROR("stream VPS/SPS/PPS payload size does not match configured MP4 header state.\n");
            m_fail = true;
            return -1;
        }
        if (memcmp(m_paramSetBuffer[i], paramSetNal[i].payload + NALU_LENGTH_SIZE, payloadSize))
        {
            MP4_LOG_ERROR("stream VPS/SPS/PPS payload does not match configured MP4 header state.\n");
            m_fail = true;
            return -1;
        }
    }

    const uint32_t seiOffset = headerOffset + 3;
    uint64_t totalBytes = 0;
    uint64_t seiBytes = 0;
    for (uint32_t i = 0; i < nalcount; i++)
    {
        MP4_FAIL_IF(i < headerOffset && nal[i].type != NAL_UNIT_ACCESS_UNIT_DELIMITER,
                    "unexpected non-AUD NAL before MP4 stream header parameter sets.\n");
        if (i >= seiOffset && !validateHeaderSeiNal(nal[i],
                                                    "unexpected non-SEI NAL in MP4 stream headers.\n",
                                                    "missing NAL payload pointer in stream headers.\n",
                                                    "invalid empty NAL in stream headers.\n",
                                                    "NAL payload type does not match MP4 stream header metadata.\n"))
        {
            m_fail = true;
            return -1;
        }
        MP4_FAIL_IF(nal[i].type <= NAL_UNIT_CODED_SLICE_CRA,
                    "MP4 stream headers must not contain VCL NAL units.\n");
        if (i < seiOffset)
        {
            MP4_FAIL_IF(!nal[i].payload, "missing NAL payload pointer in stream headers.\n");
            MP4_FAIL_IF(nal[i].sizeBytes <= NALU_LENGTH_SIZE, "invalid empty NAL in stream headers.\n");
            MP4_FAIL_IF(getNalPayloadType(nal[i]) != nal[i].type,
                        "NAL payload type does not match MP4 stream header metadata.\n");
        }
        MP4_FAIL_IF(UINT64_MAX - totalBytes < nal[i].sizeBytes,
                    "header payload overflow while assembling MP4 stream headers.\n");
        totalBytes += nal[i].sizeBytes;
        if (i >= seiOffset)
        {
            MP4_FAIL_IF(UINT64_MAX - seiBytes < nal[i].sizeBytes,
                        "SEI payload overflow while validating MP4 stream headers.\n");
            MP4_FAIL_IF((m_seiBuffer || m_seiSize) && (seiBytes > m_seiSize || m_seiSize - seiBytes < nal[i].sizeBytes),
                        "stream header SEI payload exceeds configured MP4 header state.\n");
            if ((m_seiBuffer || m_seiSize) && memcmp(m_seiBuffer + seiBytes, nal[i].payload, nal[i].sizeBytes))
            {
                MP4_LOG_ERROR("stream header SEI payload does not match configured MP4 header state.\n");
                m_fail = true;
                return -1;
            }
            seiBytes += nal[i].sizeBytes;
        }
    }
    MP4_FAIL_IF(seiBytes != m_seiSize,
                "stream header SEI payload does not match configured MP4 header state.\n");
    MP4_FAIL_IF(totalBytes > INT_MAX, "header payload too large for muxer buffer.\n");

    clearBufferedParameterSets();
    return (int)totalBytes;
}

int MP4Muxer::writeSample(const ContainerSample& sample)
{
    if (!((m_root && m_summary) && (m_track != 0)))
    {
        MP4_LOG_ERROR("MP4 muxer is not initialized before writing sample.\n");
        m_fail = true;
        return -1;
    }
    if (!validateParameterState("MP4 muxer reached sample write with partial parameter state.\n",
                                "MP4 muxer parameters are incomplete before writing sample.\n"))
    {
        m_fail = true;
        return -1;
    }
    if (!(m_sampleEntry != 0))
    {
        MP4_LOG_ERROR("missing MP4 sample entry before writing sample.\n");
        m_fail = true;
        return -1;
    }
    if (!sample.pic)
    {
        MP4_LOG_ERROR("null picture for MP4 sample.\n");
        m_fail = true;
        return -1;
    }
    if (sample.nalCount && !sample.nal)
    {
        MP4_LOG_ERROR("null NAL array for MP4 sample.\n");
        m_fail = true;
        return -1;
    }
    if (!sample.nalCount)
    {
        MP4_LOG_ERROR("empty NAL array for MP4 sample.\n");
        m_fail = true;
        return -1;
    }
    if ((m_paramSetBuffer[0] || m_paramSetBuffer[1] || m_paramSetBuffer[2]
        || m_paramSetSize[0] || m_paramSetSize[1] || m_paramSetSize[2]))
    {
        MP4_LOG_ERROR("stale parameter set state remained after MP4 stream start.\n");
        m_fail = true;
        return -1;
    }
    SamplePreparation prep = {};
    const bool prepared = [&]() {
        if (!analyzeSampleNals(sample, prep.hasLeadingVcl, prep.hasRadl, prep.hasRecoveryPoint,
                               prep.hasSublayerNonRef, prep.sampleTemporalIdSet, prep.sampleTemporalId,
                               prep.keyframe, prep.recoveryPocCnt))
            return false;
        prep.pts = sample.pic->pts;
        prep.dts = sample.pic->dts;
        MP4_FAIL_IF(prep.pts < prep.dts, "picture PTS precedes encoder DTS for MP4 sample.\n");
        uint64_t sampleSize64 = m_seiSize;
        for (uint32_t i = 0; i < sample.nalCount; i++)
        {
            MP4_FAIL_IF(!sample.nal[i].payload, "missing NAL payload pointer in sample.\n");
            MP4_FAIL_IF(sample.nal[i].sizeBytes <= NALU_LENGTH_SIZE, "invalid empty NAL in sample.\n");
            MP4_FAIL_IF(UINT64_MAX - sampleSize64 < sample.nal[i].sizeBytes,
                        "sample payload overflow while assembling MP4 sample.\n");
            sampleSize64 += sample.nal[i].sizeBytes;
        }
        MP4_FAIL_IF(sampleSize64 > INT_MAX, "sample payload too large for muxer buffer.\n");
        prep.sampleSize = (int)sampleSize64;
        if (!scaleSampleTimestamps(prep.pts, prep.dts, prep.sampleDts, prep.sampleCts))
        {
            m_fail = true;
            return false;
        }
        if (!isFirstSample() && prep.sampleDts <= m_prevDts)
        {
            MP4_LOG_ERROR("non-increasing DTS detected while writing MP4 sample.\n");
            m_fail = true;
            return false;
        }
        MP4_FAIL_IF((m_seiBuffer && !m_seiSize) || (!m_seiBuffer && m_seiSize),
                    "inconsistent SEI transition state before assembling MP4 sample.\n");
        return true;
    }();
    if (!prepared)
        return -1;

    general_log(NULL, "mp4", X265_LOG_DEBUG, "creating MP4 sample size=%d scaledDts=%" PRIu64 " scaledCts=%" PRIu64 "\n",
                prep.sampleSize, prep.sampleDts, prep.sampleCts);
    lsmash_sample_t* outSample = lsmash_create_sample((uint32_t)prep.sampleSize);
    if (!outSample)
    {
        MP4_LOG_ERROR("failed to create video sample data.\n");
        m_fail = true;
        return -1;
    }
    if (!outSample->data)
    {
        lsmash_delete_sample(outSample);
        MP4_LOG_ERROR("failed to allocate MP4 sample payload buffer.\n");
        m_fail = true;
        return -1;
    }

    uint8_t* out = outSample->data;
    if (m_seiBuffer)
    {
        memcpy(out, m_seiBuffer, m_seiSize);
        out += m_seiSize;
        clearBufferedSeiState();
    }
    for (uint32_t i = 0; i < sample.nalCount; i++)
    {
        memcpy(out, sample.nal[i].payload, sample.nal[i].sizeBytes);
        out += sample.nal[i].sizeBytes;
    }

    outSample->dts = prep.sampleDts;
    outSample->cts = prep.sampleCts;
    outSample->index = m_sampleEntry;
    outSample->prop.ra_flags = prep.keyframe
                             ? ISOM_SAMPLE_RANDOM_ACCESS_FLAG_SYNC
                             : ISOM_SAMPLE_RANDOM_ACCESS_FLAG_NONE;

    general_log(NULL, "mp4", X265_LOG_DEBUG, "appending MP4 sample track=%u entry=%u\n",
                m_track, m_sampleEntry);
    if (lsmash_append_sample(m_root, m_track, outSample))
    {
        lsmash_delete_sample(outSample);
        MP4_LOG_ERROR("failed to append a video frame.\n");
        m_fail = true;
        return -1;
    }

    if (isFirstSample() || prep.sampleCts < m_firstCts)
        m_firstCts = prep.sampleCts;
    m_prevDts = prep.sampleDts;
    if (isFirstSample())
    {
        m_lastPts = prep.pts;
        m_secondLastPts = prep.pts;
    }
    else if (prep.pts >= m_lastPts)
    {
        m_secondLastPts = m_lastPts;
        m_lastPts = prep.pts;
    }
    else if (prep.pts > m_secondLastPts)
        m_secondLastPts = prep.pts;
    m_numFrames++;

    return prep.sampleSize;
}

void MP4Muxer::finalize(int64_t largestPts, int64_t secondLargestPts)
{
    if (!m_root)
    {
        MP4_LOG_ERROR("MP4 muxer lost root state before finalize.\n");
        m_fail = true;
    }

    bool validTimeline = !m_fail;
    if (validTimeline)
    {
        if (!validateParameterState("MP4 muxer reached finalize with partial parameter state.\n",
                                    "MP4 muxer parameters are incomplete before finalize.\n"))
            validTimeline = m_fail = true;
        if ((m_seiBuffer && !m_seiSize) || (!m_seiBuffer && m_seiSize))
        {
            MP4_LOG_ERROR("inconsistent SEI transition state before finalize.\n");
            validTimeline = m_fail = true;
        }
        if (!isFirstSample() && m_seiBuffer)
        {
            MP4_LOG_ERROR("stale SEI transition buffer remained after writing MP4 samples.\n");
            validTimeline = m_fail = true;
        }
        if (!(m_track != 0) || !(m_sampleEntry != 0) || isFirstSample())
        {
            if (!(m_track != 0) && isFirstSample() && !(m_sampleEntry != 0))
                MP4_LOG_ERROR("MP4 muxer finalized before track initialization.\n");
            else if (!(m_track != 0))
                MP4_LOG_ERROR("MP4 muxer lost track state before finalize.\n");
            else if (!(m_sampleEntry != 0))
                MP4_LOG_ERROR("MP4 muxer finalized before headers were configured.\n");
            else if (isFirstSample())
                MP4_LOG_ERROR("cannot finalize MP4 after headers were written without any samples.\n");
            validTimeline = m_fail = true;
        }
    }

    const bool singleSample = m_numFrames == 1;
    if (validTimeline)
    {
        if ((singleSample && largestPts != m_lastPts)
            || (!singleSample && (largestPts != m_lastPts || secondLargestPts != m_secondLastPts)))
        {
            MP4_LOG_ERROR("finalize PTS inputs do not match the MP4 samples that were written.\n");
            validTimeline = m_fail = true;
        }
        else if (singleSample && secondLargestPts != largestPts)
        {
            MP4_LOG_ERROR("single-sample finalize must repeat the only PTS value.\n");
            validTimeline = m_fail = true;
        }
        else if (largestPts < secondLargestPts)
        {
            MP4_LOG_ERROR("largest PTS precedes second largest PTS during finalize.\n");
            validTimeline = m_fail = true;
        }
        else if (!singleSample && largestPts == secondLargestPts)
        {
            MP4_LOG_ERROR("largest PTS matches second largest PTS during finalize.\n");
            validTimeline = m_fail = true;
        }
    }

    int64_t lastDelta = 1;
    if (validTimeline)
    {
        if (singleSample)
        {
            const uint32_t fpsNum = m_fpsNum;
            const uint32_t fpsDenom = m_fpsDenom;
            const int timebaseNum = m_timebaseNum;
            const int timebaseDenom = m_timebaseDenom;
            uint64_t lastDeltaNumerator = 0;
            uint64_t lastDeltaDenominator = 0;
            if (!fpsNum || timebaseNum <= 0 || timebaseDenom <= 0
                || !checkedMulU64((uint64_t)fpsDenom, (uint64_t)timebaseDenom, lastDeltaNumerator)
                || !checkedMulU64((uint64_t)fpsNum, (uint64_t)timebaseNum, lastDeltaDenominator)
                || !lastDeltaDenominator)
            {
                MP4_LOG_ERROR("invalid timing state while deriving single-sample finalize delta.\n");
                validTimeline = m_fail = true;
            }
            else
            {
                uint64_t roundedLastDelta = (lastDeltaNumerator + lastDeltaDenominator / 2) / lastDeltaDenominator;
                if (!roundedLastDelta || roundedLastDelta > (uint64_t)INT64_MAX)
                {
                    MP4_LOG_ERROR("single-sample finalize delta is out of range.\n");
                    validTimeline = m_fail = true;
                }
                else
                    lastDelta = (int64_t)roundedLastDelta;
            }
        }
        else if (largestPts > secondLargestPts)
        {
            if (!checkedSubInt64(largestPts, secondLargestPts, lastDelta) || lastDelta <= 0)
            {
                MP4_LOG_ERROR("timestamp overflow while deriving finalize delta.\n");
                validTimeline = m_fail = true;
            }
        }
    }

    if (validTimeline && !finalizeTimeline(largestPts, lastDelta))
        validTimeline = m_fail = true;

    if (!m_fail)
    {
        sign();
        if (lsmash_finish_movie(m_root, NULL))
        {
            MP4_LOG_ERROR("failed to finish movie.\n");
            m_fail = true;
        }
    }

    cleanupHandle();
    if (m_fail)
        cleanupOutputFile();
}

bool MP4Muxer::isFail() const
{
    return m_fail;
}

void MP4Muxer::abort()
{
    m_fail = true;
    cleanupHandle();
    cleanupOutputFile();
}

MP4Output::MP4Output(const char* fname, InputFileInfo& inputInfo)
{
    m_fail = false;
    m_paramSet = false;
    m_headersWritten = false;
    m_closed = false;

    if (!m_muxer.init(fname, inputInfo))
        m_fail = true;
}

void MP4Output::setParam(x265_param* param)
{
    if (!param || m_closed)
    {
        m_fail = true;
        return;
    }

    if ((m_fail || m_muxer.isFail()) || m_paramSet || m_headersWritten || m_closed)
    {
        m_fail = true;
        return;
    }

    param->bAnnexB = false;
    param->bRepeatHeaders = false;
    param->bEnableAccessUnitDelimiters = false;
    param->bEnableEndOfSequence = false;
    param->bEnableEndOfBitstream = false;
    if (!m_muxer.setParam(param))
    {
        m_muxer.abort();
        m_fail = true;
    }
    else
        m_paramSet = true;
}

int MP4Output::writeHeaders(const x265_nal* nal, uint32_t nalcount)
{
    if ((m_fail || m_muxer.isFail()) || !m_paramSet || m_headersWritten || m_closed)
    {
        m_fail = true;
        return -1;
    }

    general_log(NULL, "mp4", X265_LOG_DEBUG, "configuring MP4 parameter sets\n");
    if (!m_muxer.configureParameterSets(nal, nalcount))
    {
        m_muxer.abort();
        m_fail = true;
        return -1;
    }

    general_log(NULL, "mp4", X265_LOG_DEBUG, "beginning MP4 stream\n");
    int bytes = m_muxer.beginStream(nal, nalcount);
    if (bytes < 0)
    {
        m_muxer.abort();
        m_fail = true;
    }
    else
        m_headersWritten = true;

    return bytes;
}

int MP4Output::writeFrame(const x265_nal* nal, uint32_t nalcount, x265_picture& pic)
{
    if ((m_fail || m_muxer.isFail()) || !m_paramSet || !m_headersWritten || m_closed)
    {
        m_fail = true;
        return -1;
    }

    ContainerSample sample;
    sample.nal = nal;
    sample.nalCount = nalcount;
    sample.pic = &pic;

    general_log(NULL, "mp4", X265_LOG_DEBUG, "writing MP4 sample pts=%" PRId64 " dts=%" PRId64 " nal=%u\n",
                pic.pts, pic.dts, nalcount);
    int bytes = m_muxer.writeSample(sample);
    if (bytes < 0)
    {
        m_muxer.abort();
        m_fail = true;
    }

    return bytes;
}

void MP4Output::closeFile(int64_t largest_pts, int64_t second_largest_pts)
{
    if (m_closed)
    {
        m_fail = true;
        return;
    }
    m_closed = true;

    if ((m_fail || m_muxer.isFail()))
    {
        m_muxer.abort();
        m_fail = true;
        return;
    }
    if (!m_paramSet)
    {
        MP4_LOG_ERROR("cannot finalize MP4 before parameters were set.\n");
        m_muxer.abort();
        m_fail = true;
        return;
    }
    if (!m_headersWritten)
    {
        MP4_LOG_ERROR("cannot finalize MP4 before headers were written.\n");
        m_muxer.abort();
        m_fail = true;
        return;
    }

    m_muxer.finalize(largest_pts, second_largest_pts);
    if (m_muxer.isFail())
    {
        m_fail = true;
    }
}
