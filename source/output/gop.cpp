/*****************************************************************************
 * MIT License
 *
 * Copyright (c) 2018-2019 Xinyue Lu
 *
 * Authors: Xinyue Lu <i@7086.in>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *****************************************************************************
 * The MIT License applies to this file only.
 *****************************************************************************/

#include "gop.h"

#include <cerrno>
#include <cstdio>
#include <cstring>
#ifndef _MSC_VER
#include <unistd.h>
#endif

using namespace X265_NS;

#ifdef _MSC_VER
    #include <windows.h>
    #define sleep(x) Sleep((x) * 1000)
#endif
#define TIME_WAIT 30

FILE* GOPOutput::open_file_for_write(const std::string fname, bool retry)
{
    while(true)
    {
        FILE* fp = x265_fopen(fname.c_str(), "wb");
        if(fp != nullptr && !std::ferror(fp))
            return fp;
        if (fp != nullptr)
        {
            bool closeFailed = std::ferror(fp) != 0;
            if (std::fclose(fp))
                closeFailed = true;
            if (closeFailed)
                general_log(nullptr, getName(), X265_LOG_WARNING,
                    "unable to close file %s after open failure.\n", fname.c_str());
        }
        if(!retry)
            break;
        // Retrying
        general_log(nullptr, getName(), X265_LOG_WARNING,
            "unable to open file %s for writing, error %d %s, retrying in %d seconds.\n", fname.c_str(), errno, std::strerror(errno), TIME_WAIT);
        sleep(TIME_WAIT);
    }
    // Failed
    b_fail = true;
    general_log(nullptr, getName(), X265_LOG_ERROR,
        "unable to open file %s for writing, error %d %s.\n", fname.c_str(), errno, std::strerror(errno));
    return nullptr;
}

bool GOPOutput::smart_fwrite(const void* data, std::size_t size, FILE* file)
{
    std::size_t written;
    int err = 0;
    while(true)
    {
        written = std::fwrite(data, 1, size, file);
        if(written == size)
        {
            data_pos += written;
            return true;
        }

        err = errno ? errno : EIO;
        if (err == ENOSPC)
        {
            clearerr(file);
            if (std::fseek(file, data_pos, SEEK_SET) == 0)
            {
                general_log(nullptr, getName(), X265_LOG_WARNING,
                    "unable to write, error %d %s, retrying in %d seconds.\n", err, std::strerror(err), TIME_WAIT);
                sleep(TIME_WAIT);
                continue;
            }
        }
        break;
    }

    b_fail = true;
    general_log(nullptr, getName(), X265_LOG_ERROR,
        "unable to write, error %d %s.\n", err, std::strerror(err));
    return false;
}

void GOPOutput::clean_up()
{
    if (data_file)
    {
        bool closeFailed = std::ferror(data_file) != 0;
        if (std::fclose(data_file))
            closeFailed = true;
        if (closeFailed)
            b_fail = true;
    }
    if (gop_file)
    {
        bool closeFailed = std::ferror(gop_file) != 0;
        if (std::fclose(gop_file))
            closeFailed = true;
        if (closeFailed)
            b_fail = true;
    }
    data_file = nullptr;
    gop_file = nullptr;
}

int GOPOutput::openFile(const char* gop_filename)
{
    gop_file = open_file_for_write(gop_filename, false);
    if(!gop_file) return -1;

    std::string gop_fn(gop_filename);
    std::size_t pos;
    if((pos = gop_fn.rfind('/')) != std::string::npos || (pos = gop_fn.rfind('\\')) != std::string::npos)
    {
        dir_prefix = gop_fn.substr(0, pos+1);
        gop_fn = gop_fn.substr(pos+1);
    }

    if((pos = gop_fn.rfind('.')) != std::string::npos)
        filename_prefix = gop_fn.substr(0, pos);
    else
        filename_prefix = gop_fn;

    return 0;
}

void GOPOutput::setParam(x265_param *p_param)
{
    if (b_fail || !gop_file)
    {
        b_fail = true;
        return;
    }

    p_param->bAnnexB = false;
    p_param->bRepeatHeaders = false;

    i_numframe = 0;
    FILE* opt_file = open_file_for_write(dir_prefix + filename_prefix + ".options", false);
    if(!opt_file) return;

    if (!options_written)
    {
        if (std::fprintf(gop_file, "#options %s.options\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))
        {
            b_fail = true;
            bool closeFailed = std::ferror(opt_file) != 0;
            if (std::fclose(opt_file))
                closeFailed = true;
            if (closeFailed)
                b_fail = true;
            return;
        }
        options_written = true;
    }

    std::fprintf(opt_file, "b-frames %d\n",           p_param->bframes);
    std::fprintf(opt_file, "b-pyramid %d\n",          p_param->bBPyramid);
    std::fprintf(opt_file, "input-timebase-num %d\n", info.timebaseNum);
    std::fprintf(opt_file, "input-timebase-den %d\n", info.timebaseDenom);
    std::fprintf(opt_file, "output-fps-num %u\n",     p_param->fpsNum);
    std::fprintf(opt_file, "output-fps-den %u\n",     p_param->fpsDenom);
    std::fprintf(opt_file, "source-width %d\n",       p_param->sourceWidth);
    std::fprintf(opt_file, "source-height %d\n",      p_param->sourceHeight);
    std::fprintf(opt_file, "sar-width %d\n",          p_param->vui.sarWidth);
    std::fprintf(opt_file, "sar-height %d\n",         p_param->vui.sarHeight);
    std::fprintf(opt_file, "primaries-index %d\n",    p_param->vui.colorPrimaries);
    std::fprintf(opt_file, "transfer-index %d\n",     p_param->vui.transferCharacteristics);
    std::fprintf(opt_file, "matrix-index %d\n",       p_param->vui.matrixCoeffs >= 0 ? p_param->vui.matrixCoeffs : GOP_ISOM_MATRIX_INDEX_UNSPECIFIED);
    std::fprintf(opt_file, "full-range %d\n",         p_param->vui.bEnableVideoFullRangeFlag >= 0 ? p_param->vui.bEnableVideoFullRangeFlag : 0);

    bool closeFailed = std::ferror(opt_file) != 0;
    if (std::fclose(opt_file))
        closeFailed = true;
    if (closeFailed)
        b_fail = true;
}

int GOPOutput::writeHeaders(const x265_nal* p_nal, uint32_t nalcount)
{
    assert(nalcount >= 3); // header should contain 3+ nals

    if (b_fail || !gop_file)
    {
        b_fail = true;
        return -1;
    }

    FILE* hdr_file = open_file_for_write(dir_prefix + filename_prefix + ".headers", false);
    if(!hdr_file) return -1;

    if (std::fprintf(gop_file, "#headers %s.headers\n", filename_prefix.c_str()) < 0 || std::fflush(gop_file))
    {
        b_fail = true;
        bool closeFailed = std::ferror(hdr_file) != 0;
        if (std::fclose(hdr_file))
            closeFailed = true;
        if (closeFailed)
            b_fail = true;
        return -1;
    }

    for(unsigned int i = 0; i < nalcount; i++)
    {
        if (!smart_fwrite(p_nal[i].payload, p_nal[i].sizeBytes, hdr_file))
        {
            bool closeFailed = std::ferror(hdr_file) != 0;
            if (std::fclose(hdr_file))
                closeFailed = true;
            if (closeFailed)
                b_fail = true;
            return -1;
        }
    }

    bool closeFailed = std::ferror(hdr_file) != 0;
    if (std::fclose(hdr_file))
        closeFailed = true;
    if (closeFailed)
    {
        b_fail = true;
        return -1;
    }
    return p_nal[0].sizeBytes + p_nal[1].sizeBytes + p_nal[2].sizeBytes;
}

int GOPOutput::writeFrame(const x265_nal* p_nalu, uint32_t nalcount, x265_picture& pic)
{
    if (b_fail || !gop_file)
    {
        b_fail = true;
        return -1;
    }

    const bool is_keyframe = pic.sliceType == X265_TYPE_IDR;
    int i_size = 0;

    if (is_keyframe) {
        if (data_file)
        {
            bool closeFailed = std::ferror(data_file) != 0;
            if (std::fclose(data_file))
                closeFailed = true;
            if (closeFailed)
            {
                b_fail = true;
                data_file = nullptr;
                return -1;
            }
            data_file = nullptr;
        }
        std::stringstream ss;
        ss << filename_prefix << std::string("-") << std::setfill('0') << std::setw(6) << i_numframe << std::string(".hevc-gop-data");
        std::string data_filename = ss.str();
        data_file = open_file_for_write(dir_prefix + data_filename, i_numframe > 0);
        if(!data_file) return -1;
        data_pos = 0;
        if (std::fprintf(gop_file, "%s\n", data_filename.c_str()) < 0 || std::fflush(gop_file))
        {
            b_fail = true;
            bool closeFailed = std::ferror(data_file) != 0;
            if (std::fclose(data_file))
                closeFailed = true;
            if (closeFailed)
                b_fail = true;
            data_file = nullptr;
            return -1;
        }
    }
    else if (!data_file)
    {
        b_fail = true;
        return -1;
    }
    int8_t ts_len = 2 * sizeof(int64_t);
    int8_t ts_lenx[4] = {0, 0, 0, ts_len};
    if (!smart_fwrite(&ts_lenx, 4, data_file) ||
        !smart_fwrite(&pic.pts, sizeof(int64_t), data_file) ||
        !smart_fwrite(&pic.dts, sizeof(int64_t), data_file))
        return -1;

    for(uint8_t i = 0; i < nalcount; i++)
        i_size += p_nalu[i].sizeBytes;

    for(uint8_t i = 0; i < nalcount; i++)
    {
        if (!smart_fwrite(p_nalu[i].payload, p_nalu[i].sizeBytes, data_file))
            return -1;
    }

    i_numframe++;

    return i_size;
}

void GOPOutput::closeFile(int64_t, int64_t)
{
    clean_up();
}
