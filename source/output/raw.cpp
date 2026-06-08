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
#include "raw.h"

#include <cstdio>
#include <cstring>
#if _WIN32
#include <io.h>
#include <fcntl.h>
#if defined(_MSC_VER)
#pragma warning(disable: 4996) // POSIX setmode and fileno deprecated
#endif
#endif

using namespace X265_NS;
RAWOutput::RAWOutput(const char* fname, InputFileInfo&)
{
    b_fail = false;
    if (!std::strcmp(fname, "-"))
    {
        ofs = stdout;
#if _WIN32
        setmode(fileno(stdout), O_BINARY);
#endif
        return;
    }
    ofs = x265_fopen(fname, "wb");
    if (!ofs)
        b_fail = true;
    else if (std::ferror(ofs))
    {
        bool closeFailed = std::ferror(ofs) != 0;
        if (std::fclose(ofs))
            closeFailed = true;
        if (closeFailed)
            x265_log(nullptr, X265_LOG_WARNING, "raw: unable to close output file after open failure\n");
        ofs = nullptr;
        b_fail = true;
    }
}

void RAWOutput::setParam(x265_param* param)
{
    param->bAnnexB = true;
}

int RAWOutput::writeHeaders(const x265_nal* nal, uint32_t nalcount)
{
    if (b_fail || !ofs)
    {
        b_fail = true;
        return -1;
    }

    uint32_t bytes = 0;

    for (uint32_t i = 0; i < nalcount; i++)
    {
        size_t written = std::fwrite((const void*)nal->payload, 1, nal->sizeBytes, ofs);
        if (written != nal->sizeBytes || std::ferror(ofs))
        {
            b_fail = true;
            return -1;
        }
        bytes += nal->sizeBytes;
        nal++;
    }

    return bytes;
}

int RAWOutput::writeFrame(const x265_nal* nal, uint32_t nalcount, x265_picture&)
{
    if (b_fail || !ofs)
    {
        b_fail = true;
        return -1;
    }

    uint32_t bytes = 0;

    for (uint32_t i = 0; i < nalcount; i++)
    {
        size_t written = std::fwrite((const void*)nal->payload, 1, nal->sizeBytes, ofs);
        if (written != nal->sizeBytes || std::ferror(ofs))
        {
            b_fail = true;
            return -1;
        }
        bytes += nal->sizeBytes;
        nal++;
    }

    return bytes;
}

void RAWOutput::closeFile(int64_t, int64_t)
{
    if (!ofs)
    {
        b_fail = true;
        return;
    }

    bool closeFailed = false;
    if (ofs == stdout)
        closeFailed = std::fflush(ofs) || std::ferror(ofs);
    else
    {
        closeFailed = std::ferror(ofs) != 0;
        if (std::fclose(ofs))
            closeFailed = true;
    }
    if (closeFailed)
        b_fail = true;
    ofs = nullptr;
}
