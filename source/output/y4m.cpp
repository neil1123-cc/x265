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
#include "y4m.h"

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

Y4MOutput::Y4MOutput(const char* filename, int w, int h, uint32_t bitdepth, uint32_t fpsNum, uint32_t fpsDenom, int csp, int inputdepth)
    : width(w)
    , height(h)
    , bitDepth(bitdepth)
    , colorSpace(csp)
    , frameSize(0)
    , inputDepth(inputdepth)
    , ofs(nullptr)
    , header(0)
    , finalized(false)
{
    failed = false;
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
        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate Y4M output row buffer\n");
        failed = true;
        return;
    }

    const char *cf = (csp >= X265_CSP_I444) ? "444" : (csp >= X265_CSP_I422) ? "422" : "420";

    if (ofs)
    {
        if (bitDepth == 10)
            failed = std::fprintf(ofs, "YUV4MPEG2 W%d H%d F%u:%u Ip C%sp10 XYSCSS = %sP10\n", width, height, fpsNum, fpsDenom, cf, cf) < 0;
        else if (bitDepth == 12)
            failed = std::fprintf(ofs, "YUV4MPEG2 W%d H%d F%u:%u Ip C%sp12 XYSCSS = %sP12\n", width, height, fpsNum, fpsDenom, cf, cf) < 0;
        else
            failed = std::fprintf(ofs, "YUV4MPEG2 W%d H%d F%u:%u Ip C%s\n", width, height, fpsNum, fpsDenom, cf) < 0;

        if (!failed)
        {
            int64_t headerPos = ftello(ofs);
            failed = headerPos < 0;
            if (!failed)
                header = (uint64_t)headerPos;
        }
    }

    if (!addPlanePixelsToFrameSize(frameSize, width, height, colorSpace))
    {
        delete [] buf;
        buf = nullptr;
        failed = true;
    }
}

Y4MOutput::~Y4MOutput()
{
    finalize();
    delete [] buf;
}

bool Y4MOutput::finalize()
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

bool Y4MOutput::writePicture(const x265_picture& pic)
{
    if (!buf || !ofs || failed)
        return false;

    uint64_t outPicPos = header;
    if (pic.bitDepth > 8)
    {
        if (frameSize > (UINT64_MAX - 6) / 2)
        {
            failed = true;
            return false;
        }
        uint64_t frameSpan = 6 + frameSize * 2;
        if ((uint64_t)pic.poc > UINT64_MAX / frameSpan)
        {
            failed = true;
            return false;
        }
        outPicPos += (uint64_t)pic.poc * frameSpan;
    }
    else
    {
        if (frameSize > UINT64_MAX - 6)
        {
            failed = true;
            return false;
        }
        uint64_t frameSpan = 6 + frameSize;
        if ((uint64_t)pic.poc > UINT64_MAX / frameSpan)
        {
            failed = true;
            return false;
        }
        outPicPos += (uint64_t)pic.poc * frameSpan;
    }
    failed |= fseeko(ofs, (int64_t)outPicPos, SEEK_SET) != 0;
    if (failed)
        return false;
    failed |= std::fwrite("FRAME\n", 1, 6, ofs) != 6;
    if (failed)
        return false;

    if (inputDepth > 8)
    {
        if (pic.bitDepth == 8 && pic.poc == 0)
            x265_log(nullptr, X265_LOG_WARNING, "y4m: down-shifting reconstructed pixels to 8 bits\n");
    }

    X265_CHECK(pic.colorSpace == colorSpace, "invalid chroma subsampling\n");

    if (inputDepth > 8)//if HIGH_BIT_DEPTH
    {
        if (pic.bitDepth == 8)
        {
            // encoder gave us short pixels, downshift, then write
            X265_CHECK(pic.bitDepth == 8, "invalid bit depth\n");
            int shift = pic.bitDepth - 8;
            for (int i = 0; i < x265_cli_csps[colorSpace].planes; i++)
            {
                char *src = (char*)pic.planes[i];
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
            X265_CHECK(pic.bitDepth > 8, "invalid bit depth\n");
            for (int i = 0; i < x265_cli_csps[colorSpace].planes; i++)
            {
                uint16_t *src = (uint16_t*)pic.planes[i];
                for (int h = 0; h < (height * 1) >> x265_cli_csps[colorSpace].height[i]; h++)
                {
                    size_t rowBytes = (size_t)((width * 2) >> x265_cli_csps[colorSpace].width[i]);
                    failed |= std::fwrite((const char*)src, 1, rowBytes, ofs) != rowBytes;
                    if (failed)
                        return false;
                    src += pic.stride[i] / sizeof(*src);
                }
            }
        }
    }
    else if (inputDepth == 8 && pic.bitDepth > 8)
    {
        X265_CHECK(pic.bitDepth > 8, "invalid bit depth\n");
        for (int i = 0; i < x265_cli_csps[colorSpace].planes; i++)
        {
            uint16_t* src = (uint16_t*)pic.planes[i];
            for (int h = 0; h < (height * 1) >> x265_cli_csps[colorSpace].height[i]; h++)
            {
                size_t rowBytes = (size_t)((width * 2) >> x265_cli_csps[colorSpace].width[i]);
                failed |= std::fwrite((const char*)src, 1, rowBytes, ofs) != rowBytes;
                if (failed)
                    return false;
                src += pic.stride[i] / sizeof(*src);
            }
        }
    }
    else
    {
        X265_CHECK(pic.bitDepth == 8, "invalid bit depth\n");
        for (int i = 0; i < x265_cli_csps[colorSpace].planes; i++)
        {
            char *src = (char*)pic.planes[i];
            for (int h = 0; h < height >> x265_cli_csps[colorSpace].height[i]; h++)
            {
                size_t rowBytes = (size_t)(width >> x265_cli_csps[colorSpace].width[i]);
                failed |= std::fwrite(src, 1, rowBytes, ofs) != rowBytes;
                if (failed)
                    return false;
                src += pic.stride[i] / sizeof(*src);
            }
        }
    }

    return !failed;
}
