/*****************************************************************************
* Copyright (C) 2013-2020 MulticoreWare, Inc
*
* Author: Steve Borho <steve@borho.org>
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

#include "framedata.h"
#include "picyuv.h"
#include "search.h"
#include "threadedme.h"

#include <algorithm>
#include <cstring>
#include <new>

using namespace X265_NS;

FrameData::FrameData() = default;

bool FrameData::create(const x265_param& param, const SPS& sps, int csp)
{
    bool isallocated = false;
    m_param = &param;
    m_slice  = new (std::nothrow) Slice;
    if (!m_slice)
        return false;

    if (m_param->bThreadedME)
    {
        uint32_t numCUs = sps.numCuInWidth * sps.numCuInHeight;
        uint32_t totalPUs = numCUs * MAX_NUM_PUS_PER_CTU;
        m_slice->m_ctuMV = X265_MALLOC(MEData, totalPUs);
        if (!m_slice->m_ctuMV)
            goto fail;
    }

    m_picCTU = new (std::nothrow) CUData[sps.numCUsInFrame];
    if (!m_picCTU)
        goto fail;
    m_picCsp = csp;
    m_spsrpsIdx = -1;
    if (param.rc.bStatWrite)
        m_spsrps = const_cast<RPS*>(sps.spsrps);
    isallocated = m_cuMemPool.create(0, param.internalCsp, sps.numCUsInFrame, param);
    if (m_param->bDynamicRefine)
    {
        CHECKED_MALLOC_ZERO(m_cuMemPool.dynRefineRdBlock, uint64_t, MAX_NUM_DYN_REFINE * sps.numCUsInFrame);
        CHECKED_MALLOC_ZERO(m_cuMemPool.dynRefCntBlock, uint32_t, MAX_NUM_DYN_REFINE * sps.numCUsInFrame);
        CHECKED_MALLOC_ZERO(m_cuMemPool.dynRefVarBlock, uint32_t, MAX_NUM_DYN_REFINE * sps.numCUsInFrame);
    }
    if (isallocated)
    {
        for (uint32_t ctuAddr = 0; ctuAddr < sps.numCUsInFrame; ctuAddr++)
        {
            if (m_param->bDynamicRefine)
            {
                m_picCTU[ctuAddr].m_collectCURd = m_cuMemPool.dynRefineRdBlock + (ctuAddr * MAX_NUM_DYN_REFINE);
                m_picCTU[ctuAddr].m_collectCUVariance = m_cuMemPool.dynRefVarBlock + (ctuAddr * MAX_NUM_DYN_REFINE);
                m_picCTU[ctuAddr].m_collectCUCount = m_cuMemPool.dynRefCntBlock + (ctuAddr * MAX_NUM_DYN_REFINE);
            }
            m_picCTU[ctuAddr].initialize(m_cuMemPool, 0, param, ctuAddr);
        }
    }
    else
        goto fail;
    CHECKED_MALLOC_ZERO(m_cuStat, RCStatCU, sps.numCUsInFrame + 1);
    CHECKED_MALLOC(m_rowStat, RCStatRow, sps.numCuInHeight);
    reinit(sps);
    
    for (int i = 0; i < INTEGRAL_PLANE_NUM; i++)
    {
        m_meBuffer[i] = nullptr;
        m_meIntegral[i] = nullptr;
    }
    return true;

fail:
    destroy();
    return false;
}

void FrameData::reinit(const SPS& sps)
{
    std::fill_n(m_cuStat, sps.numCUsInFrame, RCStatCU());
    std::fill_n(m_rowStat, sps.numCuInHeight, RCStatRow());
    if (m_param->bThreadedME)
    {
        uint32_t totalPUs = sps.numCuInWidth * sps.numCuInHeight * MAX_NUM_PUS_PER_CTU;
        const MV zeroMV(0, 0);
        const MEData resetMEData = { { zeroMV, zeroMV }, { zeroMV, zeroMV }, { 0, 0 }, { REF_NOT_VALID, REF_NOT_VALID }, 0, 0 };
        std::fill_n(m_slice->m_ctuMV, totalPUs, resetMEData);
    }
    if (m_param->bDynamicRefine)
    {
        std::fill_n(m_picCTU->m_collectCURd, MAX_NUM_DYN_REFINE * sps.numCUsInFrame, uint64_t(0));
        std::fill_n(m_picCTU->m_collectCUVariance, MAX_NUM_DYN_REFINE * sps.numCUsInFrame, uint32_t(0));
        std::fill_n(m_picCTU->m_collectCUCount, MAX_NUM_DYN_REFINE * sps.numCUsInFrame, uint32_t(0));
    }
}

void FrameData::destroySEAIntegralBuffers()
{
    for (int i = 0; i < INTEGRAL_PLANE_NUM; i++)
    {
        if (m_meBuffer[i] != nullptr)
        {
            X265_FREE(m_meBuffer[i]);
            m_meBuffer[i] = nullptr;
        }
        m_meIntegral[i] = nullptr;
    }
}

void FrameData::destroy()
{
    delete [] m_picCTU;
    m_picCTU = nullptr;

    if (m_slice)
    {
        X265_FREE(m_slice->m_ctuMV);
        delete m_slice;
        m_slice = nullptr;
    }
    delete m_saoParam;
    m_saoParam = nullptr;

    m_cuMemPool.destroy();

    if (m_param && m_param->bDynamicRefine)
    {
        X265_FREE(m_cuMemPool.dynRefineRdBlock);
        X265_FREE(m_cuMemPool.dynRefCntBlock);
        X265_FREE(m_cuMemPool.dynRefVarBlock);
    }
    X265_FREE(m_cuStat);
    m_cuStat = nullptr;
    X265_FREE(m_rowStat);
    m_rowStat = nullptr;
    destroySEAIntegralBuffers();
}
