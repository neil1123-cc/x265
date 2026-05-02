/****************************************************************************
 * Copyright (C) 2026 x265 project
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *****************************************************************************/

#ifndef X265_CONTAINER_MUXER_H
#define X265_CONTAINER_MUXER_H

#include "x265.h"
#include "input/input.h"

namespace X265_NS {

struct ContainerSample
{
    const x265_nal* nal;
    uint32_t nalCount;
    const x265_picture* pic;
};

class ContainerMuxer
{
public:
    virtual ~ContainerMuxer() {}

    virtual bool init(const char* fname, const InputFileInfo& info) = 0;
    virtual bool configureParameterSets(const x265_nal* nal, uint32_t nalcount) = 0;
    virtual int beginStream(const x265_nal* nal, uint32_t nalcount) = 0;
    virtual int writeSample(const ContainerSample& sample) = 0;
    virtual void finalize(int64_t largestPts, int64_t secondLargestPts) = 0;
    virtual void abort() = 0;
};

}

#endif // ifndef X265_CONTAINER_MUXER_H
