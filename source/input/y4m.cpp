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
#include "y4m.h"
#include "common.h"

#include <climits>
#include <limits>
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
static const char header[] = {'F','R','A','M','E'};
Y4MInput::Y4MInput(InputFileInfo& info, bool alpha, int format)
{
    for (int i = 0; i < QUEUE_SIZE; i++)
        buf[i] = nullptr;

    threadActive.store(false);
    colorSpace = info.csp;
    alphaAvailable = alpha;
    sarWidth = info.sarWidth;
    sarHeight = info.sarHeight;
    width = info.width;
    height = info.height;
    rateNum = info.fpsNum;
    rateDenom = info.fpsDenom;
    depth = info.depth;
    framesize = 0;

    ifs = nullptr;
    if (!std::strcmp(info.filename, "-"))
    {
        ifs = stdin;
#if _WIN32
        setmode(fileno(stdin), O_BINARY);
#endif
    }
    else
        ifs = x265_fopen(info.filename, "rb");
    if (ifs && !std::ferror(ifs) && parseHeader())
    {
        if (format == 1) width /= 2;
        if (format == 2) height /= 2;
        bool frameSizeValid = true;
        uint32_t pixelbytes = depth > 8 ? 2 : 1;
        size_t packedWidth = (size_t)width * (size_t)(format == 1 ? 2 : 1);
        size_t packedHeight = (size_t)height * (size_t)(format == 2 ? 2 : 1);
        for (int i = 0; i < x265_cli_csps[colorSpace].planes + alphaAvailable; i++)
        {
            size_t w = packedWidth >> x265_cli_csps[colorSpace].width[i];
            size_t h = packedHeight >> x265_cli_csps[colorSpace].height[i];
            size_t planeBytes = w * h * pixelbytes;
            if (!w || !h || planeBytes / pixelbytes / h != w || framesize > SIZE_MAX - planeBytes)
            {
                x265_log(nullptr, X265_LOG_ERROR, "y4m: frame size exceeds supported range\n");
                frameSizeValid = false;
                break;
            }
            framesize += planeBytes;
        }

        if (frameSizeValid && framesize && framesize <= SIZE_MAX - sizeof(header) - 1)
        {
            threadActive.store(true);
            for (int q = 0; q < QUEUE_SIZE; q++)
            {
                buf[q] = X265_MALLOC(char, framesize);
                if (!buf[q])
                {
                    x265_log(nullptr, X265_LOG_ERROR, "y4m: buffer allocation failure, aborting\n");
                    threadActive.store(false);
                    break;
                }
            }
        }
        else if (frameSizeValid && framesize)
            x265_log(nullptr, X265_LOG_ERROR, "y4m: frame size exceeds supported range\n");
    }
    if (!threadActive.load())
    {
        if (ifs && ifs != stdin)
            std::fclose(ifs);
        ifs = nullptr;
        return;
    }

    info.width = width;
    info.height = height;
    info.sarHeight = sarHeight;
    info.sarWidth = sarWidth;
    info.fpsNum = rateNum;
    info.fpsDenom = rateDenom;
    info.csp = colorSpace;
    info.depth = depth;
    info.frameCount = -1;
    size_t estFrameSize = framesize + sizeof(header) + 1; /* assume basic FRAME\n headers */
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
            fseeko(ifs, 0, SEEK_END);
            int64_t size = ftello(ifs);
            fseeko(ifs, cur, SEEK_SET);
            if (size > 0)
                info.frameCount = (int)((size - cur) / estFrameSize);
        }
    }
    if (info.skipFrames)
    {
#if _WIN32
        if (ifs != stdin && strncasecmp(info.filename, "\\\\.\\pipe\\", 9))
#else
        if (ifs != stdin)
#endif
        {
            if ((uint64_t)estFrameSize > (uint64_t)INT64_MAX / (uint64_t)info.skipFrames)
            {
                x265_log(nullptr, X265_LOG_ERROR, "y4m: skip offset exceeds supported range\n");
                threadActive.store(false);
            }
            else
                fseeko(ifs, (int64_t)estFrameSize * info.skipFrames, SEEK_CUR);
        }
        else
            for (int i = 0; i < info.skipFrames; i++)
                if (std::fread(buf[0], estFrameSize - framesize, 1, ifs) + std::fread(buf[0], framesize, 1, ifs) != 2)
                    break;
    }
}
Y4MInput::~Y4MInput()
{
    if (ifs && ifs != stdin)
        std::fclose(ifs);
    for (int i = 0; i < QUEUE_SIZE; i++)
        X265_FREE(buf[i]);
}

void Y4MInput::release()
{
    threadActive.store(false);
    readCount.poke();
    stop();
    delete this;
}

bool Y4MInput::parseHeader()
{
    if (!ifs)
        return false;

    auto appendBoundedDigit = [](auto& value, int digit, int maxDigit) -> bool
    {
        using ValueType = std::decay_t<decltype(value)>;
        constexpr ValueType maxValue = std::numeric_limits<ValueType>::max();
        if (digit < 0 || digit > maxDigit || value > (maxValue - (ValueType)digit) / (ValueType)10)
            return false;
        value = value * (ValueType)10 + (ValueType)digit;
        return true;
    };
    auto appendCspChar = [](int& value, int c) -> bool
    {
        int digit = c - '0';
        if (c < '0' || c > 'o' || value > (INT_MAX - digit) / 10)
            return false;
        value = value * 10 + digit;
        return true;
    };

    int csp = 0;
    int d = 0;
    int c;
    bool headerValid = true;
    while ((c = std::fgetc(ifs)) != EOF)
    {
        // Skip Y4MPEG string
        while ((c != EOF) && (c != ' ') && (c != '\n'))
            c = std::fgetc(ifs);
        while (c == ' ')
        {
            // read parameter identifier
            switch (std::fgetc(ifs))
            {
            case 'W':
                width = 0;
                while ((c = std::fgetc(ifs)) != EOF)
                {
                    if (c == ' ' || c == '\n')
                        break;
                    else if (!appendBoundedDigit(width, c - '0', 9))
                        headerValid = false;
                }
                break;
            case 'H':
                height = 0;
                while ((c = std::fgetc(ifs)) != EOF)
                {
                    if (c == ' ' || c == '\n')
                        break;
                    else if (!appendBoundedDigit(height, c - '0', 9))
                        headerValid = false;
                }
                break;

            case 'F':
                rateNum = 0;
                rateDenom = 0;
                while ((c = std::fgetc(ifs)) != EOF)
                {
                    if (c == '.')
                    {
                        rateDenom = 1;
                        while ((c = std::fgetc(ifs)) != EOF)
                        {
                            if (c == ' ' || c == '\n')
                                break;
                            else
                            {
                                if (!appendBoundedDigit(rateNum, c - '0', 9) ||
                                    !appendBoundedDigit(rateDenom, 0, 9))
                                    headerValid = false;
                            }
                        }
                        break;
                    }
                    else if (c == ':')
                    {
                        while ((c = std::fgetc(ifs)) != EOF)
                        {
                            if (c == ' ' || c == '\n')
                                break;
                            else if (!appendBoundedDigit(rateDenom, c - '0', 9))
                                headerValid = false;
                        }
                        break;
                    }
                    else if (!appendBoundedDigit(rateNum, c - '0', 9))
                        headerValid = false;
                }
                break;

            case 'A':
                sarWidth = 0;
                sarHeight = 0;
                while ((c = std::fgetc(ifs)) != EOF)
                {
                    if (c == ':')
                    {
                        while ((c = std::fgetc(ifs)) != EOF)
                        {
                            if (c == ' ' || c == '\n')
                                break;
                            else if (!appendBoundedDigit(sarHeight, c - '0', 9))
                                headerValid = false;
                        }
                        break;
                    }
                    else if (!appendBoundedDigit(sarWidth, c - '0', 9))
                        headerValid = false;
                }
                break;

            case 'C':
                csp = 0;
                d = 0;
                while ((c = std::fgetc(ifs)) != EOF)
                {
                    if (c <= 'o' && c >= '0')
                    {
                        if (!appendCspChar(csp, c))
                            headerValid = false;
                    }
                    else if (c == 'p')
                    {
                        // example: C420p16
                        while ((c = std::fgetc(ifs)) != EOF)
                        {
                            if (c <= '9' && c >= '0')
                            {
                                if (!appendBoundedDigit(d, c - '0', 9))
                                    headerValid = false;
                            }
                            else
                                break;
                        }
                        break;
                    }
                    else
                        break;
                }

                if (csp / 100 == ('m'-'0')*1000 + ('o'-'0')*100 + ('n'-'0')*10 + ('o'-'0'))
                {
                    colorSpace = X265_CSP_I400;
                    d = csp % 100;
                }
                else if (csp / 10 == ('m'-'0')*1000 + ('o'-'0')*100 + ('n'-'0')*10 + ('o'-'0'))
                {
                    colorSpace = X265_CSP_I400;
                    d = csp % 10;
                }
                else if (csp == ('m'-'0')*1000 + ('o'-'0')*100 + ('n'-'0')*10 + ('o'-'0'))
                {
                    colorSpace = X265_CSP_I400;
                    d = 8;
                }
                else
                    colorSpace = (csp == 444) ? X265_CSP_I444 : (csp == 422) ? X265_CSP_I422 : X265_CSP_I420;

                if (d >= 8 && d <= 16)
                    depth = d;
                break;
            default:
                while ((c = std::fgetc(ifs)) != EOF)
                {
                    // consume this unsupported configuration word
                    if (c == ' ' || c == '\n')
                        break;
                }
                break;
            }
        }

        if (c == '\n')
            break;
    }

    if (!headerValid)
    {
        x265_log(nullptr, X265_LOG_ERROR, "y4m: header value exceeds supported range\n");
        return false;
    }

    if (width < MIN_FRAME_WIDTH || width > MAX_FRAME_WIDTH ||
        height < MIN_FRAME_HEIGHT || height > MAX_FRAME_HEIGHT ||
        rateDenom == 0 || rateNum == 0 ||
        (rateNum / rateDenom) < 1 || (rateNum / rateDenom) > MAX_FRAME_RATE ||
        colorSpace < X265_CSP_I400 || colorSpace >= X265_CSP_COUNT)
        return false;

    return true;
}

void Y4MInput::startReader()
{
#if ENABLE_THREADING
    if (threadActive.load())
        start();
#endif
}

void Y4MInput::threadMain()
{
    THREAD_NAME("Y4MRead", 0);
    do
    {
        if (!populateFrameQueue())
            break;
    }
    while (threadActive.load());

    threadActive.store(false);
    writeCount.poke();
}
bool Y4MInput::populateFrameQueue()
{
    if (!ifs || std::ferror(ifs))
        return false;
    /* strip off the FRAME\n header */
    char hbuf[sizeof(header) + 1];
    if (std::fread(hbuf, sizeof(hbuf), 1, ifs) != 1 || std::memcmp(hbuf, header, sizeof(header)))
    {
        if (!std::feof(ifs))
            x265_log(nullptr, X265_LOG_ERROR, "y4m: frame header missing\n");
        return false;
    }
    /* consume bytes up to line feed */
    int c = hbuf[sizeof(header)];
    while (c != '\n')
        if ((c = std::fgetc(ifs)) == EOF)
            break;
    /* wait for room in the ring buffer */
    int written = writeCount.get();
    int read = readCount.get();
    while (written - read > QUEUE_SIZE - 2)
    {
        read = readCount.waitForChange(read);
        if (!threadActive.load())
            return false;
    }
    ProfileScopeEvent(frameRead);
    if (std::fread(buf[written % QUEUE_SIZE], framesize, 1, ifs) == 1)
    {
        writeCount.incr();
        return true;
    }
    else
        return false;
}

bool Y4MInput::readPicture(x265_picture& pic)
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
        int pixelbytes = depth > 8 ? 2 : 1;
        pic.bitDepth = depth;
        pic.framesize = framesize;
        pic.height = height;
        pic.width = width;
        pic.colorSpace = colorSpace;
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

