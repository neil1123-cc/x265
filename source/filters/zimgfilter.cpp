/*****************************************************************************
 * Copyright (C) 2013-2020 x265 project
 *
 * Authors: Xinyue Lu <i@7086.in>
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

#ifdef ENABLE_ZIMG
#include "zimgfilter.h"

#include <cmath>
#include <cerrno>
#include <cstdio>
#include <cstring>

using namespace X265_NS;

#if _WIN32
#define strcasecmp _stricmp
#endif

const char* Resizers[] = {"point", "bilinear", "bicubic", "spline16", "spline36", "lanczos"};

namespace {

bool mulOverflowSizeT(size_t a, size_t b, size_t& out)
{
    if (!a || !b)
    {
        out = 0;
        return false;
    }

    if (a > SIZE_MAX / b)
        return true;

    out = a * b;
    return false;
}

bool copyZimgSegment(char* dst, size_t dstSize, const char* begin, const char* end, const char* context)
{
    size_t length = static_cast<size_t>(end - begin);
    if (length >= dstSize)
    {
        general_log(nullptr, "zimg", X265_LOG_ERROR, "%s exceeds supported length\n", context);
        return false;
    }

    if (length)
        std::memcpy(dst, begin, length);
    dst[length] = 0;
    return true;
}

const char* findZimgChar(const char* begin, const char* end, char target)
{
    if (!begin || !end || begin > end)
        return nullptr;

    const void* match = std::memchr(begin, target, static_cast<size_t>(end - begin));
    return static_cast<const char*>(match);
}

enum ZimgClauseParseResult
{
    ZIMG_CLAUSE_OK,
    ZIMG_CLAUSE_MISSING_PARAMETER_LIST,
    ZIMG_CLAUSE_MISSING_CLOSING_PAREN,
    ZIMG_CLAUSE_COPY_ERROR,
};

ZimgClauseParseResult parseZimgClause(const char* cursor, const char* end, const char*& next,
                                      char* name, size_t nameSize, char* value, size_t valueSize)
{
    if (!cursor || !end || cursor > end || !name || nameSize < 2 || !value || valueSize < 2)
        return ZIMG_CLAUSE_COPY_ERROR;

    const char* open = findZimgChar(cursor, end, '(');
    if (!open)
    {
        if (!copyZimgSegment(name, nameSize, cursor, end, "Filter keyword"))
            return ZIMG_CLAUSE_COPY_ERROR;
        value[0] = '\0';
        next = end;
        return ZIMG_CLAUSE_MISSING_PARAMETER_LIST;
    }

    if (!copyZimgSegment(name, nameSize, cursor, open, "Filter keyword"))
        return ZIMG_CLAUSE_COPY_ERROR;

    const char* valueBegin = open + 1;
    const char* close = findZimgChar(valueBegin, end, ')');
    const char* valueEnd = close ? close : end;
    if (!copyZimgSegment(value, valueSize, valueBegin, valueEnd, "Filter parameters"))
        return ZIMG_CLAUSE_COPY_ERROR;

    if (!close)
    {
        next = end;
        return ZIMG_CLAUSE_MISSING_CLOSING_PAREN;
    }

    next = close + 1;
    return ZIMG_CLAUSE_OK;
}

int splitZimgCommaTokens(const char* value, const char* parts[], size_t lengths[], int maxParts)
{
    if (!value || !parts || !lengths || maxParts <= 0)
        return -1;

    int count = 0;
    const char* token = value;
    while (token)
    {
        if (count >= maxParts)
            return -1;

        const char* comma = std::strchr(token, ',');
        size_t length = comma ? (size_t)(comma - token) : std::strlen(token);
        if (!length)
            return -1;

        parts[count] = token;
        lengths[count] = length;
        count++;

        token = comma ? comma + 1 : nullptr;
    }

    return count;
}

bool parseZimgDoubleToken(const char* token, size_t length, double& value)
{
    if (!token || !length)
        return false;

    char number[64];
    if (length >= sizeof(number))
        return false;

    std::memcpy(number, token, length);
    number[length] = '\0';
    errno = 0;
    char* end = nullptr;
    value = std::strtod(number, &end);
    return errno != ERANGE && end && *end == '\0' && end != number && std::isfinite(value);
}

bool parseZimgIntToken(const char* token, size_t length, int& value)
{
    if (!token || !length)
        return false;

    char number[32];
    if (length >= sizeof(number))
        return false;

    std::memcpy(number, token, length);
    number[length] = '\0';
    errno = 0;
    char* end = nullptr;
    long parsed = std::strtol(number, &end, 10);
    if (errno == ERANGE || !end || *end != '\0' || end == number || parsed < 0 || parsed > INT_MAX)
        return false;

    value = (int)parsed;
    return true;
}

}

void ZimgFilter::release()
{
    if (temp)
    {
        x265_free(temp);
        temp = nullptr;
    }

    if (graph)
    {
        zimg_filter_graph_free(graph);
        graph = nullptr;
    }
    if (planes_all)
    {
        x265_free(planes_all);
        planes_all = nullptr;
    }
}

uint32_t mod4(uint32_t size)
{
    if (size % 4 == 0)
        return size;
    int denom = 16;
    while (denom >= 4)
    {
        int reminder = size % denom;
        if (reminder <= (denom >> 2)) return size - reminder;
        reminder -= denom;
        if (reminder >= -(denom >> 2)) return size - reminder;
        denom >>= 1;
    }
    /* If it's still non-mod4, cut it */
    return size - size % 4;
}

uint32_t round_up_64(uint32_t size)
{
    if ((size & 63) == 0) return size;
    return size - (size & 63) + 64;
}

ZimgFilter::ZimgFilter(char* paramString)
{
    // zimg:crop(a,b,c,d)lanczos(a,b)
    cLeft = cRight = cTop = cBottom = 0;
    rWidth = rHeight = 0;
    resizer = -1;
    param1 = param2 = 0.0;
    xp = nullptr;
    bFail = false;
    graph = nullptr;
    planes_all = nullptr;
    planes[0] = nullptr;
    temp = nullptr;

    const char* cursor = paramString;
    const char* end = paramString + std::strlen(paramString);

    while (cursor < end)
    {
        char pName[1024];
        char pValue[1024];
        const char* next = cursor;
        switch (parseZimgClause(cursor, end, next, pName, sizeof(pName), pValue, sizeof(pValue)))
        {
        case ZIMG_CLAUSE_COPY_ERROR:
            bFail = true;
            return;
        case ZIMG_CLAUSE_MISSING_PARAMETER_LIST:
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Filter keyword %s missing parameter list\n", pName);
            bFail = true;
            return;
        case ZIMG_CLAUSE_MISSING_CLOSING_PAREN:
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Filter keyword %s missing closing ')'\n", pName);
            bFail = true;
            return;
        case ZIMG_CLAUSE_OK:
            break;
        default:
            bFail = true;
            return;
        }
        cursor = next;

        if (!pName[0])
            continue;
        if (!strcasecmp(pName, "crop"))
        {
            double dLeft, dTop, dRight, dBottom;
            const char* parts[4];
            size_t lengths[4];
            if (splitZimgCommaTokens(pValue, parts, lengths, 4) != 4 ||
                !parseZimgDoubleToken(parts[0], lengths[0], dLeft) ||
                !parseZimgDoubleToken(parts[1], lengths[1], dTop) ||
                !parseZimgDoubleToken(parts[2], lengths[2], dRight) ||
                !parseZimgDoubleToken(parts[3], lengths[3], dBottom))
            {
                general_log(nullptr, "zimg", X265_LOG_ERROR, "Crop: invalid parameters: (%s), should be (L,T,W,H) or (L,T,-R,-B)\n", pValue);
                bFail = true;
                return;
            }
            cLeft   = static_cast<int>(1024 * dLeft);
            cTop    = static_cast<int>(1024 * dTop);
            cRight  = static_cast<int>(1024 * dRight);
            cBottom = static_cast<int>(1024 * dBottom);
            continue;
        }
        for (unsigned int i = 0; i < sizeof(Resizers) / sizeof(char*); i++)
            if (!strcasecmp(pName, Resizers[i]))
            {
                resizer = i;
                break;
            }
        if (resizer < 0)
        {
            // Unknown keyword
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Unknown keyword: %s\n", pName);
            bFail = true;
            return;
        }
        const char* parts[4];
        size_t lengths[4];
        int count = splitZimgCommaTokens(pValue, parts, lengths, 4);
        int parsedWidth = 0;
        int parsedHeight = 0;
        if (!((count == 2 || count == 4) &&
              parseZimgIntToken(parts[0], lengths[0], parsedWidth) &&
              parseZimgIntToken(parts[1], lengths[1], parsedHeight) &&
              (count == 2 || (parseZimgDoubleToken(parts[2], lengths[2], param1) &&
                               parseZimgDoubleToken(parts[3], lengths[3], param2)))))
        {
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Resize: invalid parameters: (%s), should be (W,H[,P1,P2])\n", pValue);
            bFail = true;
            return;
        }
        rWidth = (uint32_t)parsedWidth;
        rHeight = (uint32_t)parsedHeight;
    }
}

void ZimgFilter::setParam(x265_param* xParam)
{
    xp = xParam;
    bool doCrop = cLeft != 0 || cRight != 0 || cTop != 0 || cBottom != 0;
    bool doResize = rWidth != 0 || rHeight != 0;
    byPass = !doCrop && !doResize;
    if (byPass)
    {
        general_log(xp, "zimg", X265_LOG_INFO, "Nothing to do. Bypassing\n");
        return;
    }
    sWidth = xp->sourceWidth;
    sHeight = xp->sourceHeight;
    general_log(xp, "zimg", X265_LOG_INFO, "Input: %dx%d\n", sWidth, sHeight);
    if (cLeft < 0 || cTop < 0)
    {
        general_log(nullptr, "zimg", X265_LOG_ERROR, "Crop: Left (%d) and Top (%d) must be non-negative\n", cLeft >> 10, cTop >> 10);
        bFail = true;
        return;
    }
    if (cRight <= 0 || cBottom <= 0)
    {
        if (cRight <= 0)
            cRight = (sWidth << 10) - cLeft + cRight;
        if (cBottom <= 0)
            cBottom = (sHeight << 10) - cTop + cBottom;
    }
    if (cRight <= 0 || cBottom <= 0)
    {
        general_log(nullptr, "zimg", X265_LOG_ERROR, "Crop: Size after cropping (%dx%d) must be positive\n", cRight >> 10, cBottom >> 10);
        bFail = true;
        return;
    }
    if (doCrop)
    {
        if (cRight % 1024 == 0 && cBottom % 1024 == 0)
            general_log(xp, "zimg", X265_LOG_INFO, "Crop: %dx%d\n", cRight >> 10, cBottom >> 10);
        else
            general_log(xp, "zimg", X265_LOG_INFO, "Crop: %.2lfx%.2lf\n", cRight / 1024., cBottom / 1024.);
    }
    if (doResize)
    {
        if (rWidth == 0)
            rWidth = cRight * rHeight / cBottom;
        else if(rHeight == 0)
            rHeight = cBottom * rWidth / cRight;
    }
    else
    {
        rWidth = cRight >> 10;
        rHeight = cBottom >> 10;
    }
    /* We make sure it's at least mod 4 */
    uint32_t tWidth = mod4(rWidth);
    uint32_t tHeight = mod4(rHeight);
    if (tWidth != rWidth || tHeight != rHeight)
    {
        /* We'll resize */
        rWidth = tWidth;
        rHeight = tHeight;
        if (resizer < 0)
            resizer = ZIMG_RESIZE_LANCZOS;
        doResize = true;
    }
    if (resizer < 0)
        resizer = ZIMG_RESIZE_POINT;
    if (doResize)
        general_log(xp, "zimg", X265_LOG_INFO, "Resize: %dx%d\n", rWidth, rHeight);
    xp->sourceWidth = rWidth;
    xp->sourceHeight = rHeight;

    zimg_image_format_default(&src_format, ZIMG_API_VERSION);
    zimg_image_format_default(&dst_format, ZIMG_API_VERSION);
    zimg_graph_builder_params_default(&graph_params, ZIMG_API_VERSION);

    src_format.width  = (int)sWidth;
    dst_format.width  = (int)rWidth;
    src_format.height = (int)sHeight;
    dst_format.height = (int)rHeight;

    csp = xp->internalCsp;
    if (x265_cli_csps[csp].planes > 1)
    {
        src_format.subsample_w =
        dst_format.subsample_w = x265_cli_csps[csp].width[1];
        src_format.subsample_h =
        dst_format.subsample_h = x265_cli_csps[csp].height[1];
    }

    src_format.active_region.left = cLeft / 1024.;
    src_format.active_region.top = cTop / 1024.;
    src_format.active_region.width = cRight / 1024.;
    src_format.active_region.height = cBottom / 1024.;

    graph_params.resample_filter_uv =
    graph_params.resample_filter = (zimg_resample_filter_e)resizer;
    graph_params.filter_param_a_uv =
    graph_params.filter_param_a = param1;
    graph_params.filter_param_b_uv =
    graph_params.filter_param_b = param2;
}

void ZimgFilter::processFrame(x265_picture& picture)
{
    if (byPass) return;
    if (bFail) return;

    int err = 0;
    char fail_str[1024];
    int OutputDepth = X265_DEPTH;
    if (!graph) // Init
    {
        release();
        int pixelSize = OutputDepth > 8 ? 2 : 1;
        src_format.depth = picture.bitDepth;
        dst_format.depth = OutputDepth;
        src_format.pixel_type = picture.bitDepth > 8 ? ZIMG_PIXEL_WORD : ZIMG_PIXEL_BYTE;
        dst_format.pixel_type = OutputDepth > 8 ? ZIMG_PIXEL_WORD : ZIMG_PIXEL_BYTE;

        switch (picture.colorSpace)
        {
        case X265_CSP_BGR:
        case X265_CSP_BGRA:
        case X265_CSP_RGB:
            src_format.color_family = dst_format.color_family = ZIMG_COLOR_RGB;
            break;
        case X265_CSP_I400:
            src_format.color_family = dst_format.color_family = ZIMG_COLOR_GREY;
            break;
        default:
            src_format.color_family = dst_format.color_family = ZIMG_COLOR_YUV;
            break;
        }
        src_format.pixel_range =
        dst_format.pixel_range = xp->vui.bEnableVideoFullRangeFlag ? ZIMG_RANGE_FULL : ZIMG_RANGE_LIMITED;

        framesize = 0;
        size_t strideInput = (size_t)rWidth * (size_t)pixelSize;
        if (rWidth <= 0 || rHeight <= 0 || strideInput > UINT32_MAX)
        {
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid resize buffer geometry\n");
            release();
            bFail = true;
            return;
        }
        auto stride_all = round_up_64((uint32_t)strideInput);
        size_t planeBytes = 0;
        size_t totalPlaneBytes = 0;
        if (rWidth <= 0 || rHeight <= 0 ||
            mulOverflowSizeT((size_t)rHeight, (size_t)stride_all, planeBytes) ||
            mulOverflowSizeT(planeBytes, (size_t)x265_cli_csps[csp].planes, totalPlaneBytes))
        {
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid resize buffer geometry\n");
            release();
            bFail = true;
            return;
        }
        planes_all = x265_malloc(totalPlaneBytes);
        char * planes_ptr = reinterpret_cast<char *>(planes_all);
        if (!planes_all)
        {
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for resize buffer\n");
            release();
            bFail = true;
            return;
        }
        // Create buffer for resize
        for (int i = 0; i < x265_cli_csps[csp].planes; i++)
        {
            int w = rWidth  >> x265_cli_csps[csp].width[i];
            int h = rHeight >> x265_cli_csps[csp].height[i];
            size_t planeStrideInput = (size_t)w * (size_t)pixelSize;
            size_t planeFrameBytes = 0;
            if (w < 0 || h < 0 || planeStrideInput > UINT32_MAX)
            {
                general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane geometry\n");
                release();
                bFail = true;
                return;
            }
            stride[i] = round_up_64((uint32_t)planeStrideInput);
            if (mulOverflowSizeT((size_t)h, (size_t)stride[i], planeFrameBytes) ||
                SIZE_MAX - framesize < planeFrameBytes)
            {
                general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: invalid plane frame size\n");
                release();
                bFail = true;
                return;
            }
            planes[i] = planes_ptr;
            planes_ptr += planeFrameBytes;
            framesize += planeFrameBytes;
        }

        graph = zimg_filter_graph_build(&src_format, &dst_format, &graph_params);
        if (!graph)
        {
            zimg_get_last_error(fail_str, sizeof(fail_str));
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: %s\n", fail_str);
            release();
            bFail = true;
            return;
        }
        // Create temp buffer
        size_t tmp_size;
        err = zimg_filter_graph_get_tmp_size(graph, &tmp_size);
        if (err)
        {
            zimg_get_last_error(fail_str, sizeof(fail_str));
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: %s\n", fail_str);
            release();
            bFail = true;
            return;
        }
        temp = tmp_size ? x265_malloc(tmp_size) : nullptr;
        if (tmp_size && !temp)
        {
            general_log(nullptr, "zimg", X265_LOG_ERROR, "Init: error allocating memory for temp buffer\n");
            release();
            bFail = true;
            return;
        }
    }

    zimg_image_buffer_const src_buf = {};
    zimg_image_buffer dst_buf = {};
    src_buf.version = ZIMG_API_VERSION;
    dst_buf.version = ZIMG_API_VERSION;

    for (int i = 0; i < x265_cli_csps[csp].planes; i++)
    {
        src_buf.plane[i].data = picture.planes[i];
        src_buf.plane[i].stride = picture.stride[i];
        src_buf.plane[i].mask = ZIMG_BUFFER_MAX;
        dst_buf.plane[i].data = planes[i];
        dst_buf.plane[i].stride = stride[i];
        dst_buf.plane[i].mask = ZIMG_BUFFER_MAX;
    }

    err = zimg_filter_graph_process(graph, &src_buf, &dst_buf, temp, 0, 0, 0, 0);
    if (err)
    {
        zimg_get_last_error(fail_str, sizeof(fail_str));
        general_log(nullptr, "zimg", X265_LOG_ERROR, "Resize: %s\n", fail_str);
        bFail = true;
        return;
    }

    std::memcpy(picture.stride, stride, sizeof(stride));
    std::memcpy(picture.planes, planes, sizeof(planes));
    picture.bitDepth = OutputDepth;
    picture.width = rWidth;
    picture.height = rHeight;
    picture.framesize = framesize;
}

#endif
