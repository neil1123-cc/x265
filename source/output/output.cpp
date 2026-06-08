/*****************************************************************************
 * Copyright (C) 2013-2020 MulticoreWare, Inc
 *
 * Authors: Steve Borho <steve@borho.org>
 *          Xinyue Lu <i@7086.in>
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

#include "output.h"
#include "yuv.h"
#include "y4m.h"
#include "gop.h"

#include <cstring>
#include <new>

#include "raw.h"

using namespace X265_NS;

ReconFile* ReconFile::open(const char *fname, int width, int height, uint32_t bitdepth, uint32_t fpsNum, uint32_t fpsDenom, int csp, int sourceBitDepth)
{
    const char * s = std::strrchr(fname, '.');

    if (s && !std::strcmp(s, ".y4m"))
    {
        ReconFile* output = new (std::nothrow) Y4MOutput(fname, width, height, bitdepth, fpsNum, fpsDenom, csp, sourceBitDepth);
        if (!output)
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate Y4M recon output\n");
        return output;
    }
    else
    {
        ReconFile* output = new (std::nothrow) YUVOutput(fname, width, height, bitdepth, csp, sourceBitDepth);
        if (!output)
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate YUV recon output\n");
        return output;
    }
}
#ifdef ENABLE_MKV
  #include "mkv.h"
#endif
#ifdef ENABLE_LSMASH
  #include "mp4.h"
#endif

OutputFile* OutputFile::open(const char *fname, InputFileInfo& inputInfo)
{
    const char * s = std::strrchr(fname, '.');

#ifdef ENABLE_MKV
    if (s && !std::strcmp(s, ".mkv"))
    {
        OutputFile* output = new (std::nothrow) MKVOutput(fname, inputInfo);
        if (!output)
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate MKV output\n");
        return output;
    }
#endif
#ifdef ENABLE_LSMASH
    if (s && !std::strcmp(s, ".mp4"))
    {
        OutputFile* output = new (std::nothrow) MP4Output(fname, inputInfo);
        if (!output)
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate MP4 output\n");
        return output;
    }
#endif
    if (s && !std::strcmp(s, ".gop"))
    {
        OutputFile* output = new (std::nothrow) GOPOutput(fname, inputInfo);
        if (!output)
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate GOP output\n");
        return output;
    }

    OutputFile* output = new (std::nothrow) RAWOutput(fname, inputInfo);
    if (!output)
        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate raw output\n");
    return output;
}
