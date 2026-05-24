/*****************************************************************************
 * Copyright (C) 2013 x265 project
 *
 * Authors: Selvakumar Nithiyaruban <selvakumar@multicorewareinc.com>
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

#include "filters.h"
#include "common.h"

#include <cstring>
#ifdef ENABLE_ZIMG
#include "zimgfilter.h"
#endif

using namespace X265_NS;

namespace {

bool copyFilterSegment(char* dst, size_t dstSize, const char* begin, const char* end, const char* context)
{
    size_t length = static_cast<size_t>(end - begin);
    if (length >= dstSize)
    {
        x265_log(nullptr, X265_LOG_ERROR, "%s exceeds supported length\n", context);
        return false;
    }

    if (length)
        std::memcpy(dst, begin, length);
    dst[length] = 0;
    return true;
}

}

bool Filter::parseFilterString(char* paramString, std::vector<Filter *>* filters)
{
    // --vf func1:param1/func2:param2
    char* end = paramString + std::strlen(paramString);
    char* begin = paramString;
    char* p = begin;
    while(p < end)
    {
        char fName[1024];
        char fParams[1024];
        // Scan to find column sign
        while (p < end && p[0] != ':' && p[0] != '/') p++;
        if (!copyFilterSegment(fName, sizeof(fName), begin, p, "Filter name"))
            return true;

        if (p < end && p[0] == ':')
        {
            p++;
            begin = p;
            while (p < end && p[0] != '/') p++;
            if (!copyFilterSegment(fParams, sizeof(fParams), begin, p, "Filter parameters"))
                return true;
        }
        else
        {
            fParams[0] = 0;
        }

        if (p < end && p[0] == '/')
            p++;
        begin = p;

        if (fName[0])
        {
            Filter* filter = nullptr;
#ifdef ENABLE_ZIMG
            if (!std::strcmp(fName, "zimg"))
                filter = new ZimgFilter(fParams);
#endif
            if (filter == nullptr)
            {
                x265_log(nullptr, X265_LOG_ERROR, "Unknown filter: %s\n", fName);
                return true;
            }
            filters->push_back(filter);
            if (filter->isFail())
                return true;
        }
    }
    return false;
}
