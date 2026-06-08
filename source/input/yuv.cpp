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
#define _FILE_OFFSET_BITS 64
#define _LARGEFILE_SOURCE
#include "yuv.h"
#include "common.h"

#include <climits>
#include <cstdio>
#include <cstring>

#define ENABLE_THREADING 1

#if _WIN32
#define strncasecmp _strnicmp
#include <io.h>
#include <fcntl.h>
#if defined(_MSC_VER)
#pragma warning(disable: 4996) // POSIX setmode and fileno deprecated
#endif
#endif

using namespace X265_NS;

YUVInput::YUVInput(InputFileInfo& info, bool alpha, int format)
{
    for (int i = 0; i < QUEUE_SIZE; i++)
        buf[i] = nullptr;

    depth = info.depth;
    width = info.width;
    height = info.height;
    colorSpace = info.csp;
    alphaAvailable = alpha;
    threadActive.store(false);
    failed.store(true);
    ifs = nullptr;

    if (colorSpace < 0 || colorSpace >= X265_CSP_MAX)
    {
        x265_log(nullptr, X265_LOG_ERROR, "Invalid color space: %d\n", colorSpace);
        return;
    }

    if (width <= 0 || height <= 0 || info.fpsNum <= 0 || info.fpsDenom <= 0)
    {
        x265_log(nullptr, X265_LOG_ERROR, "yuv: width, height, and FPS must be specified\n");
        return;
    }

    uint32_t pixelbytes = depth > 8 ? 2 : 1;
    size_t packedWidth = (size_t)width * (size_t)(format == 1 ? 2 : 1);
    size_t packedHeight = (size_t)height * (size_t)(format == 2 ? 2 : 1);
    framesize = 0;
    for (int i = 0; i < x265_cli_csps[colorSpace].planes + alphaAvailable; i++)
    {
        size_t w = packedWidth >> x265_cli_csps[colorSpace].width[i];
        size_t h = packedHeight >> x265_cli_csps[colorSpace].height[i];
        size_t planeBytes = w * h * pixelbytes;
        if (!w || !h || planeBytes / pixelbytes / h != w || framesize > SIZE_MAX - planeBytes)
        {
            x265_log(nullptr, X265_LOG_ERROR, "yuv: frame size exceeds supported range\n");
            return;
        }
        framesize += planeBytes;
    }
    if (!std::strcmp(info.filename, "-"))
    {
        ifs = stdin;
#if _WIN32
        setmode(fileno(stdin), O_BINARY);
#endif
    }
    else
        ifs = x265_fopen(info.filename, "rb");
    if (ifs && !std::ferror(ifs))
        threadActive.store(true);
    else
    {
        if (ifs && ifs != stdin)
        {
            bool closeFailed = std::ferror(ifs) != 0;
            if (std::fclose(ifs))
                closeFailed = true;
            if (closeFailed)
                x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to close input file after open failure\n");
        }
        ifs = nullptr;
        return;
    }

    for (uint32_t i = 0; i < QUEUE_SIZE; i++)
    {
        buf[i] = X265_MALLOC(char, framesize);
        if (buf[i] == nullptr)
        {
            x265_log(nullptr, X265_LOG_ERROR, "yuv: buffer allocation failure, aborting\n");
            threadActive.store(false);
            return;
        }
    }

    info.frameCount = -1;
    /* try to estimate frame count, if this is not stdin */
#if _WIN32
    if (ifs != stdin && strncasecmp(info.filename, "\\\\.\\pipe\\", 9))
#else
    if (ifs != stdin)
#endif
    {
        int64_t cur = ftello(ifs);
        if (cur >= 0)
        {
            if (fseeko(ifs, 0, SEEK_END) == 0)
            {
                int64_t size = ftello(ifs);
                if (fseeko(ifs, cur, SEEK_SET) < 0)
                {
                    x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to restore input position after frame count estimate\n");
                    failed.store(true);
                    threadActive.store(false);
                    return;
                }
                if (size > 0)
                    info.frameCount = (int)((size - cur) / framesize);
                else if (size < 0)
                    clearerr(ifs);
            }
            else
                clearerr(ifs);
        }
        else
            clearerr(ifs);
    }
    if (info.skipFrames)
    {
#if _WIN32
        if (ifs != stdin && strncasecmp(info.filename, "\\\\.\\pipe\\", 9))
#else
        if (ifs != stdin)
#endif
        {
            if ((uint64_t)framesize > (uint64_t)INT64_MAX / (uint64_t)info.skipFrames)
            {
                x265_log(nullptr, X265_LOG_ERROR, "yuv: skip offset exceeds supported range\n");
                failed.store(true);
                threadActive.store(false);
            }
            else if (fseeko(ifs, (int64_t)framesize * info.skipFrames, SEEK_CUR) < 0)
            {
                x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to skip requested frames\n");
                failed.store(true);
                threadActive.store(false);
            }
        }
        else
            for (int i = 0; i < info.skipFrames; i++)
            {
                size_t skipFrameBytes = std::fread(buf[0], 1, framesize, ifs);
                if (skipFrameBytes != framesize)
                {
                    x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: skip frame payload truncated\n" : "yuv: skip frame payload read failed\n");
                    failed.store(true);
                    threadActive.store(false);
                    break;
                }
            }
    }

    failed.store(!threadActive.load());
}
YUVInput::~YUVInput()
{
    if (ifs && ifs != stdin)
    {
        bool closeFailed = std::ferror(ifs) != 0;
        if (std::fclose(ifs))
            closeFailed = true;
        if (closeFailed)
            x265_log(nullptr, X265_LOG_WARNING, "yuv: unable to finalize input file state\n");
    }
    for (int i = 0; i < QUEUE_SIZE; i++)
        X265_FREE(buf[i]);
}

void YUVInput::release()
{
    threadActive.store(false);
    readCount.poke();
    stop();
    delete this;
}

void YUVInput::startReader()
{
#if ENABLE_THREADING
    if (threadActive.load() && !start())
    {
        x265_log(nullptr, X265_LOG_ERROR, "yuv: unable to start reader thread\n");
        failed.store(true);
        threadActive.store(false);
        writeCount.poke();
    }
#endif
}

void YUVInput::threadMain()
{
    THREAD_NAME("YUVRead", 0);
    while (threadActive.load())
    {
        if (!populateFrameQueue())
            break;
    }

    threadActive.store(false);
    writeCount.poke();
}
bool YUVInput::populateFrameQueue()
{
    if (!ifs || std::ferror(ifs))
        return false;
    /* wait for room in the ring buffer */
    int written = writeCount.get();
    int read = readCount.get();
    while (written - read > QUEUE_SIZE - 2)
    {
        read = readCount.waitForChange(read);
        if (!threadActive.load())
            // release() has been called
            return false;
    }
    ProfileScopeEvent(frameRead);
    size_t frameBytes = std::fread(buf[written % QUEUE_SIZE], 1, framesize, ifs);
    if (!frameBytes && std::feof(ifs))
        return false;
    if (frameBytes == framesize)
    {
        writeCount.incr();
        return true;
    }
    else
    {
        x265_log(nullptr, X265_LOG_ERROR, std::feof(ifs) ? "yuv: frame payload truncated\n" : "yuv: frame payload read failed\n");
        failed.store(true);
        return false;
    }
}

bool YUVInput::readPicture(x265_picture& pic)
{
    int read = readCount.get();
    int written = writeCount.get();

#if ENABLE_THREADING

    /* only wait if the read thread is still active */
    while (threadActive.load() && read == written)
        written = writeCount.waitForChange(written);

#else

    populateFrameQueue();

#endif // if ENABLE_THREADING

    if (read < written)
    {
        uint32_t pixelbytes = depth > 8 ? 2 : 1;
        pic.colorSpace = colorSpace;
        pic.bitDepth = depth;
        pic.framesize = framesize;
        pic.height = height;
        pic.width = width;
        pic.stride[0] = width * pixelbytes * (pic.format == 1 ? 2 : 1);
        pic.stride[1] = pic.stride[0] >> x265_cli_csps[colorSpace].width[1];
        pic.stride[2] = pic.stride[0] >> x265_cli_csps[colorSpace].width[2];
        pic.planes[0] = buf[read % QUEUE_SIZE];
        pic.planes[1] = (char*)pic.planes[0] + pic.stride[0] * (height * (pic.format == 2 ? 2 : 1));
        pic.planes[2] = (char*)pic.planes[1] + pic.stride[1] * ((height * (pic.format == 2 ? 2 : 1)) >> x265_cli_csps[colorSpace].height[1]);
#if ENABLE_ALPHA
        if (alphaAvailable)
        {
            pic.stride[3] = pic.stride[0] >> x265_cli_csps[colorSpace].width[3];
            pic.planes[3] = (char*)pic.planes[2] + pic.stride[2] * (height >> x265_cli_csps[colorSpace].height[2]);
        }
#endif
        readCount.incr();
        return true;
    }
    else
        return false;
}
