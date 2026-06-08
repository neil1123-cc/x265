/*****************************************************************************
 * Copyright (C) 2013-2020 MulticoreWare, Inc
 *
 * Authors: Steve Borho <steve@borho.org>
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
#include "output.h"
#include "yuv.h"

#include <new>

using namespace X265_NS;

namespace {
bool addPlanePixelsToFrameSize(uint64_t& frameSize, int width, int height, int csp)
{
    for (int i = 0; i < x265_cli_csps[csp].planes; i++)
    {
        uint64_t planeWidth = (uint64_t)(width >> x265_cli_csps[csp].width[i]);
        uint64_t planeHeight = (uint64_t)(height >> x265_cli_csps[csp].height[i]);
        uint64_t planeSize = planeWidth * planeHeight;
        if (planeWidth && planeSize / planeWidth != planeHeight)
            return false;
        if (UINT64_MAX - frameSize < planeSize)
            return false;
        frameSize += planeSize;
    }
    return true;
}
}

YUVOutput::YUVOutput(const char *filename, int w, int h, uint32_t d, int csp, int inputdepth)
    : width(w)
    , height(h)
    , depth(d)
    , colorSpace(csp)
    , frameSize(0)
    , inputDepth(inputdepth)
    , ofs(nullptr)
    , failed(false)
    , finalized(false)
{
    ofs = x265_fopen(filename, "wb");
    failed = !ofs;
    if (width <= 0 || height <= 0)
    {
        buf = nullptr;
        return;
    }
    buf = new (std::nothrow) char[width];
    if (!buf)
    {
        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate YUV output row buffer\n");
        failed = true;
        return;
    }

    if (!addPlanePixelsToFrameSize(frameSize, width, height, colorSpace))
    {
        delete [] buf;
        buf = nullptr;
        failed = true;
    }
}

YUVOutput::~YUVOutput()
{
    finalize();
    delete [] buf;
}

bool YUVOutput::finalize()
{
    if (finalized)
        return !failed;

    finalized = true;
    if (ofs)
    {
        failed |= std::ferror(ofs) != 0;
        failed |= std::fflush(ofs) != 0;
        failed |= std::fclose(ofs) != 0;
        ofs = nullptr;
    }
    return !failed;
}

bool YUVOutput::writePicture(const x265_picture& pic)
{
    if (!buf || !ofs || failed)
        return false;

    uint64_t fileOffset = pic.poc;
    if (frameSize && fileOffset > UINT64_MAX / frameSize)
    {
        failed = true;
        return false;
    }
    fileOffset *= frameSize;

    X265_CHECK(pic.colorSpace == colorSpace, "invalid chroma subsampling\n");
    X265_CHECK(pic.bitDepth == (int)depth, "invalid bit depth\n");

#if HIGH_BIT_DEPTH
    if (depth == 8)
    {
        int shift = pic.bitDepth - 8;
        failed |= fseeko(ofs, (int64_t)fileOffset, SEEK_SET) != 0;
        if (failed)
            return false;
        for (int i = 0; i < x265_cli_csps[colorSpace].planes; i++)
        {
            uint16_t* src = (uint16_t*)pic.planes[i];
            for (int h = 0; h < height >> x265_cli_csps[colorSpace].height[i]; h++)
            {
                for (int w = 0; w < width >> x265_cli_csps[colorSpace].width[i]; w++)
                    buf[w] = (char)(src[w] >> shift);

                size_t rowBytes = (size_t)(width >> x265_cli_csps[colorSpace].width[i]);
                failed |= std::fwrite(buf, 1, rowBytes, ofs) != rowBytes;
                if (failed)
                    return false;
                src += pic.stride[i] / sizeof(*src);
            }
        }
    }
    else
    {
        if (fileOffset > UINT64_MAX / 2)
        {
            failed = true;
            return false;
        }
        failed |= fseeko(ofs, (int64_t)(fileOffset * 2), SEEK_SET) != 0;
        if (failed)
            return false;
        for (int i = 0; i < x265_cli_csps[colorSpace].planes; i++)
        {
            uint16_t* src = (uint16_t*)pic.planes[i];
            for (int h = 0; h < height >> x265_cli_csps[colorSpace].height[i]; h++)
            {
                size_t rowBytes = (size_t)((width * 2) >> x265_cli_csps[colorSpace].width[i]);
                failed |= std::fwrite((const char*)src, 1, rowBytes, ofs) != rowBytes;
                if (failed)
                    return false;
                src += pic.stride[i] / sizeof(*src);
            }
        }
    }
#else
    failed |= fseeko(ofs, (int64_t)fileOffset, SEEK_SET) != 0;
    if (failed)
        return false;
    for (int i = 0; i < x265_cli_csps[colorSpace].planes; i++)
    {
        char* src = (char*)pic.planes[i];
        for (int h = 0; h < height >> x265_cli_csps[colorSpace].height[i]; h++)
        {
            size_t rowBytes = (size_t)(width >> x265_cli_csps[colorSpace].width[i]);
            failed |= std::fwrite(src, 1, rowBytes, ofs) != rowBytes;
            if (failed)
                return false;
            src += pic.stride[i] / sizeof(*src);
        }
    }
#endif

    return !failed;
}
