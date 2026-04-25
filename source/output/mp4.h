/****************************************************************************
 * Copyright (C) 2026 x265 project
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *****************************************************************************/

#ifndef X265_HEVC_MP4_H
#define X265_HEVC_MP4_H

#include "output.h"
#include "containerMuxer.h"
#include "common.h"

#include <lsmash.h>

#include <array>
#include <string>
#include <vector>

namespace X265_NS {

class MP4Muxer : public ContainerMuxer
{
protected:
    bool m_fail;
    bool m_paramConfigured;
    int m_timebaseNum;
    int m_timebaseDenom;
    uint8_t m_maxTemporalId;

    lsmash_root_t* m_root;
    lsmash_video_summary_t* m_summary;
    lsmash_file_parameters_t m_fileParam;
    bool m_fileOpen;
    std::array<lsmash_brand_type, 6> m_brands;

    uint32_t m_movieTimescale;
    uint32_t m_videoTimescale;
    uint32_t m_track;
    uint32_t m_sampleEntry;

    uint64_t m_timeInc;
    int64_t m_startOffset;
    uint64_t m_firstCts;
    uint64_t m_prevDts;
    uint64_t m_lastIntraCts;
    int64_t m_lastPts;
    int64_t m_secondLastPts;

    uint32_t m_seiSize;
    uint8_t* m_seiBuffer;
    std::vector<uint8_t> m_vpsData;
    std::vector<uint8_t> m_spsData;
    std::vector<uint8_t> m_ppsData;

    int m_numFrames;

    uint64_t m_oldTimescale;
    uint32_t m_fpsNum;
    uint32_t m_fpsDenom;
    uint32_t m_fpsScale;
    int m_dtsDelayFrames;
    std::string m_filename;

    bool validateParameterState(const char* partialMessage, const char* incompleteMessage) const;
    bool isFirstSample() const;
    bool finalizeTimeline(int64_t largestPts, int64_t lastDelta);
    bool scaleTimestampWithOffset(int64_t ts, const char* prepareError, const char* scaleError,
                                  const char* invalidError, uint64_t& scaledTs) const;
    bool scaleSampleTimestamps(int64_t pts, int64_t dts, uint64_t& sampleDts, uint64_t& sampleCts);
    bool fail();
    int failWrite();
    void clearBufferedSeiState();
    void resetRuntimeState();
    void fixTimeScale(uint64_t& mediaTimescale, uint32_t fpsDenom);
    int64_t getTimeScaled(int64_t ts) const;
    void cleanupHandle();
    void cleanupOutputFile();
    void sign();

public:
    MP4Muxer();
    ~MP4Muxer() override;

    bool init(const char* fname, const InputFileInfo& info) override;
    bool configureParameterSets(const x265_nal* nal, uint32_t nalcount) override;
    int beginStream(const x265_nal* nal, uint32_t nalcount) override;
    int writeSample(const ContainerSample& sample) override;
    void finalize(int64_t largestPts, int64_t secondLargestPts) override;
    void abort() override;

    bool setParam(const x265_param* param);
    bool isFail() const;
};

class MP4Output : public OutputFile
{
protected:
    bool m_fail;
    bool m_paramSet;
    bool m_headersWritten;
    bool m_closed;
    MP4Muxer m_muxer;

public:
    MP4Output(const char* fname, InputFileInfo& inputInfo);

    bool isFail() const override { return m_fail || m_muxer.isFail(); }

    bool needPTS() const override { return true; }

    const char* getName() const override { return "mp4"; }

    void setParam(x265_param* param) override;

    int writeHeaders(const x265_nal* nal, uint32_t nalcount) override;

    int writeFrame(const x265_nal* nal, uint32_t nalcount, x265_picture& pic) override;

    void closeFile(int64_t largest_pts, int64_t second_largest_pts) override;

    void release() override { delete this; }
};

}

#endif // ifndef X265_HEVC_MP4_H
