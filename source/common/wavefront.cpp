/*****************************************************************************
 * Copyright (C) 2013-2020 MulticoreWare, Inc
 *
 * Authors: Steve Borho <steve@borho.org>
 *          Min Chen <chenm003@163.com>
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
 * For more information, contact us at license @ x265.com
 *****************************************************************************/

#include "threadpool.h"
#include "threading.h"
#include "wavefront.h"
#include "common.h"

#include <atomic>
#include <new>

namespace X265_NS {
// x265 private namespace

void WaveFront::releaseState()
{
    x265_free((void*)m_row_to_idx);
    x265_free((void*)m_idx_to_row);
    delete[] m_internalDependencyBitmap;
    delete[] m_externalDependencyBitmap;

    m_row_to_idx = nullptr;
    m_idx_to_row = nullptr;
    m_internalDependencyBitmap = nullptr;
    m_externalDependencyBitmap = nullptr;
    m_numWords = 0;
    m_numRows = 0;
}

bool WaveFront::init(int numRows)
{
    releaseState();
    m_numRows = numRows;

    m_numWords = (numRows + 31) >> 5;
    std::atomic<uint32_t>* internalDependencyBitmap = new (std::nothrow) std::atomic<uint32_t>[m_numWords];
    std::atomic<uint32_t>* externalDependencyBitmap = new (std::nothrow) std::atomic<uint32_t>[m_numWords];
    uint32_t* rowToIdx = X265_MALLOC(uint32_t, m_numRows);
    uint32_t* idxToRow = X265_MALLOC(uint32_t, m_numRows);

    if (!internalDependencyBitmap || !externalDependencyBitmap || !rowToIdx || !idxToRow)
    {
        delete[] internalDependencyBitmap;
        delete[] externalDependencyBitmap;
        x265_free((void*)rowToIdx);
        x265_free((void*)idxToRow);
        m_numWords = 0;
        m_numRows = 0;
        return false;
    }

    m_internalDependencyBitmap = internalDependencyBitmap;
    for (int w = 0; w < m_numWords; w++)
        m_internalDependencyBitmap[w].store(0);

    m_externalDependencyBitmap = externalDependencyBitmap;
    for (int w = 0; w < m_numWords; w++)
        m_externalDependencyBitmap[w].store(0);

    m_row_to_idx = rowToIdx;
    m_idx_to_row = idxToRow;

    return true;
}

WaveFront::~WaveFront()
{
    releaseState();
}

void WaveFront::setLayerId(int layer)
{
    m_sLayerId = layer;
}

void WaveFront::clearEnabledRowMask()
{
    for (int w = 0; w < m_numWords; w++)
    {
        m_externalDependencyBitmap[w].store(0);
        m_internalDependencyBitmap[w].store(0);
    }
}

void WaveFront::enqueueRow(int row)
{
    uint32_t bit = 1 << (row & 31);
    m_internalDependencyBitmap[row >> 5].fetch_or(bit);
}

void WaveFront::enableRow(int row)
{
    uint32_t bit = 1 << (row & 31);
    m_externalDependencyBitmap[row >> 5].fetch_or(bit);
}

void WaveFront::enableAllRows()
{
    for (int w = 0; w < m_numWords; w++)
        m_externalDependencyBitmap[w].store(~0U);
}

bool WaveFront::dequeueRow(int row)
{
    uint32_t bit = 1 << (row & 31);
    return (m_internalDependencyBitmap[row >> 5].fetch_and(~bit) & bit) != 0;
}

void WaveFront::findJob(int threadId)
{
    unsigned long id;

    /* Loop over each word until all available rows are finished */
    for (int w = 0; w < m_numWords; w++)
    {
        uint32_t oldval = m_internalDependencyBitmap[w].load() & m_externalDependencyBitmap[w].load();
        while (oldval)
        {
            BSF(id, oldval);

            uint32_t bit = 1 << id;
            if (m_internalDependencyBitmap[w].fetch_and(~bit) & bit)
            {
                /* we cleared the bit, we get to process the row */
                processRow(w * 32 + id, threadId, m_sLayerId);
                m_helpWanted.store(true);
                return; /* check for a higher priority task */
            }

            oldval = m_internalDependencyBitmap[w].load() & m_externalDependencyBitmap[w].load();
        }
    }

    m_helpWanted.store(false);
}
}
