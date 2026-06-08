/*****************************************************************************
* Copyright (C) 2013-2020 MulticoreWare, Inc
*
* Authors: Pooja Venkatesan <pooja@multicorewareinc.com>
*          Aruna Matheswaran <aruna@multicorewareinc.com>
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

#include "abrEncApp.h"
#include "mv.h"
#include "slice.h"
#include "param.h"

#include <algorithm>
#include <csignal>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <new>

#include <queue>

using namespace X265_NS;

/* Ctrl-C handler */
static volatile sig_atomic_t b_ctrl_c /* = 0 */;
static void sigint_handler(int)
{
    b_ctrl_c = 1;
}

namespace X265_NS {
    // private namespace
#define X265_INPUT_QUEUE_SIZE 250

    static int getConfiguredViewCount(const x265_param& param)
    {
        return param.format != 0 ? 1 : param.numViews;
    }

    static bool usesAbrScalerMode(const CLIOptions& cliopt, uint32_t encoderId)
    {
        return cliopt.enableScaler && encoderId != 0;
    }

    static void configureAbrReuseFileState(x265_param* param, const CLIOptions& cliopt)
    {
        if (!param)
            return;

        param->analysisLoadReuseLevel = cliopt.loadLevel;
        param->analysisSaveReuseLevel = cliopt.saveLevel;
        std::snprintf(param->analysisSave, sizeof(param->analysisSave), "%s", cliopt.saveLevel ? "save.dat" : "");
        std::snprintf(param->analysisLoad, sizeof(param->analysisLoad), "%s", cliopt.loadLevel ? "load.dat" : "");
        param->bUseAnalysisFile = 0;
    }

    static void propagateAbrRefConfWin(x265_param* param, const x265_param* refParam, int scaleFactor)
    {
        if (!param || !refParam)
            return;

        param->confWinBottomOffset = refParam->confWinBottomOffset * scaleFactor;
        param->confWinRightOffset = refParam->confWinRightOffset * scaleFactor;
    }

    AbrEncoder::AbrEncoder(CLIOptions cliopt[], uint8_t numEncodes, int &ret)
    {
        m_numEncodes = numEncodes;
        m_numInputViews = 0;
        m_numActiveEncodes.set(numEncodes);
        m_queueSize = (numEncodes > 1) ? X265_INPUT_QUEUE_SIZE : 1;
        m_passEnc = nullptr;
        m_clioptArray = cliopt;
        m_param = nullptr;
        m_inputPicBuffer = nullptr;
        m_analysisBuffer = nullptr;
        m_readFlag = nullptr;
        m_picWriteCnt = nullptr;
        m_picReadCnt = nullptr;
        m_picIdxReadCnt = nullptr;
        m_analysisWriteCnt = nullptr;
        m_analysisReadCnt = nullptr;
        m_analysisWrite = nullptr;
        m_analysisRead = nullptr;
        m_passEnc = X265_MALLOC(PassEncoder*, m_numEncodes);
        if (!m_passEnc)
        {
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate memory for ABR pass list\n");
            m_numActiveEncodes.set(0);
            ret = 4;
            return;
        }
        std::fill_n(m_passEnc, m_numEncodes, nullptr);
        m_param = X265_MALLOC(x265_param, m_numEncodes);
        if (!m_param)
        {
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate memory for ABR parameter list\n");
            m_numActiveEncodes.set(0);
            ret = 4;
            return;
        }

        for (uint8_t i = 0; i < m_numEncodes; i++)
        {
            m_passEnc[i] = new PassEncoder(i, cliopt[i], this);
            if (!m_passEnc[i])
            {
                x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate memory for passEncoder\n");
                ret = 4;
                m_numActiveEncodes.decr();
                continue;
            }
            m_passEnc[i]->init(ret);
            if (m_passEnc[i]->m_ret)
            {
                if (!ret)
                    ret = m_passEnc[i]->m_ret;
                m_numActiveEncodes.decr();
            }
        }

        PassEncoder *primaryPass = (m_numEncodes && m_passEnc) ? m_passEnc[0] : nullptr;
        x265_param *primaryParam = primaryPass ? primaryPass->m_param : nullptr;
        if (!primaryParam)
        {
            x265_log(nullptr, X265_LOG_ERROR, "Missing primary ABR parameters\n");
            m_numActiveEncodes.set(0);
            ret = 4;
            return;
        }

        m_numInputViews = primaryParam->numViews > 1 ? getConfiguredViewCount(*primaryParam) : 0;
        if (!allocBuffers())
        {
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate memory for buffers\n");
            m_numActiveEncodes.set(0);
            ret = 4;
            return;
        }

        /* start passEncoder worker threads */
        for (uint8_t pass = 0; pass < m_numEncodes; pass++)
        {
            if (!m_passEnc[pass])
                continue;

            if (m_passEnc[pass]->m_ret)
                continue;

            if (usesAbrScalerMode(m_passEnc[pass]->m_cliopt, pass))
            {
                PassEncoder *srcPass = m_passEnc[pass - 1];
                if (!srcPass || srcPass->m_ret)
                {
                    m_passEnc[pass]->m_ret = srcPass ? srcPass->m_ret : 4;
                    if (!ret)
                        ret = m_passEnc[pass]->m_ret;
                    m_numActiveEncodes.decr();
                    continue;
                }
            }

            if (!m_passEnc[pass]->m_ret && !m_passEnc[pass]->startThreads() && !ret)
                ret = m_passEnc[pass]->m_ret ? m_passEnc[pass]->m_ret : 4;
        }
    }

    bool AbrEncoder::allocBuffers()
    {
        m_inputPicBuffer = nullptr;
        m_analysisBuffer = nullptr;
        m_picWriteCnt = nullptr;
        m_picReadCnt = nullptr;
        m_analysisWriteCnt = nullptr;
        m_analysisReadCnt = nullptr;
        m_picIdxReadCnt = nullptr;
        m_analysisWrite = nullptr;
        m_analysisRead = nullptr;
        m_readFlag = nullptr;

        uint8_t queueOwnerCount = m_numEncodes;
        size_t inputPicBufferCount = m_numEncodes;
        PassEncoder *primaryPass = (m_numEncodes && m_passEnc) ? m_passEnc[0] : nullptr;
        x265_param *primaryParam = primaryPass ? primaryPass->m_param : nullptr;
        if (!primaryParam)
            goto fail;
#if ENABLE_MULTIVIEW
        if(m_numInputViews > 1)
        {
            m_inputPicBuffer = X265_MALLOC(x265_picture**, MAX_VIEWS);
            inputPicBufferCount = MAX_VIEWS;
            queueOwnerCount = m_numInputViews;
        }
        else
#endif
            m_inputPicBuffer = X265_MALLOC(x265_picture**, m_numEncodes);
        if (!m_inputPicBuffer)
            goto fail;
        std::fill_n(m_inputPicBuffer, inputPicBufferCount, nullptr);
        m_analysisBuffer = X265_MALLOC(x265_analysis_data*, m_numEncodes);
        if (!m_analysisBuffer)
            goto fail;
        std::fill_n(m_analysisBuffer, m_numEncodes, nullptr);

        m_picWriteCnt = new ThreadSafeInteger[m_numEncodes];
        m_picReadCnt = new ThreadSafeInteger[m_numEncodes];
        m_analysisWriteCnt = new ThreadSafeInteger[m_numEncodes];
        m_analysisReadCnt = new ThreadSafeInteger[m_numEncodes];

        m_picIdxReadCnt = X265_MALLOC(ThreadSafeInteger*, m_numEncodes);
        if (!m_picIdxReadCnt)
            goto fail;
        std::fill_n(m_picIdxReadCnt, m_numEncodes, nullptr);
        m_analysisWrite = X265_MALLOC(ThreadSafeInteger*, m_numEncodes);
        if (!m_analysisWrite)
            goto fail;
        std::fill_n(m_analysisWrite, m_numEncodes, nullptr);
        m_analysisRead = X265_MALLOC(ThreadSafeInteger*, m_numEncodes);
        if (!m_analysisRead)
            goto fail;
        std::fill_n(m_analysisRead, m_numEncodes, nullptr);
        m_readFlag = X265_MALLOC(int*, m_numEncodes);
        if (!m_readFlag)
            goto fail;
        std::fill_n(m_readFlag, m_numEncodes, nullptr);

#if ENABLE_MULTIVIEW
        if (primaryParam->numViews > 1)
        {
            for (uint8_t pass = 0; pass < m_numInputViews; pass++)
            {
                m_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);
                if (!m_inputPicBuffer[pass])
                    goto fail;
                for (uint32_t idx = 0; idx < m_queueSize; idx++)
                {
                    m_inputPicBuffer[pass][idx] = x265_picture_alloc();
                    if (!m_inputPicBuffer[pass][idx])
                    {
                        while (idx--)
                            x265_picture_free(m_inputPicBuffer[pass][idx]);
                        X265_FREE(m_inputPicBuffer[pass]);
                        m_inputPicBuffer[pass] = nullptr;
                        goto fail;
                    }
                    x265_picture_init(primaryParam, m_inputPicBuffer[pass][idx]);
                }
                if (pass == 0)
                {
                    CHECKED_MALLOC_ZERO(m_analysisBuffer[pass], x265_analysis_data, m_queueSize);
                    m_picIdxReadCnt[pass] = new (std::nothrow) ThreadSafeInteger[m_queueSize];
                    if (!m_picIdxReadCnt[pass])
                        goto fail;
                    m_analysisWrite[pass] = new (std::nothrow) ThreadSafeInteger[m_queueSize];
                    if (!m_analysisWrite[pass])
                        goto fail;
                    m_analysisRead[pass] = new (std::nothrow) ThreadSafeInteger[m_queueSize];
                    if (!m_analysisRead[pass])
                        goto fail;
                    m_readFlag[pass] = X265_MALLOC(int, m_queueSize);
                    if (!m_readFlag[pass])
                        goto fail;
                }
            }
        }
        else
        {
#endif
            for (uint8_t pass = 0; pass < m_numEncodes; pass++)
            {
                m_inputPicBuffer[pass] = X265_MALLOC(x265_picture*, m_queueSize);
                if (!m_inputPicBuffer[pass])
                    goto fail;
                for (uint32_t idx = 0; idx < m_queueSize; idx++)
                {
                    m_inputPicBuffer[pass][idx] = x265_picture_alloc();
                    if (!m_inputPicBuffer[pass][idx])
                    {
                        while (idx--)
                            x265_picture_free(m_inputPicBuffer[pass][idx]);
                        X265_FREE(m_inputPicBuffer[pass]);
                        m_inputPicBuffer[pass] = nullptr;
                        goto fail;
                    }
                    x265_picture_init(m_passEnc[pass]->m_param, m_inputPicBuffer[pass][idx]);
                }

                CHECKED_MALLOC_ZERO(m_analysisBuffer[pass], x265_analysis_data, m_queueSize);
                m_picIdxReadCnt[pass] = new (std::nothrow) ThreadSafeInteger[m_queueSize];
                if (!m_picIdxReadCnt[pass])
                    goto fail;
                m_analysisWrite[pass] = new (std::nothrow) ThreadSafeInteger[m_queueSize];
                if (!m_analysisWrite[pass])
                    goto fail;
                m_analysisRead[pass] = new (std::nothrow) ThreadSafeInteger[m_queueSize];
                if (!m_analysisRead[pass])
                    goto fail;
                m_readFlag[pass] = X265_MALLOC(int, m_queueSize);
                if (!m_readFlag[pass])
                    goto fail;
            }
#if ENABLE_MULTIVIEW
        }
#endif
        return true;
    fail:
        for (uint8_t pass = 0; pass < queueOwnerCount; pass++)
        {
            if (m_inputPicBuffer && m_inputPicBuffer[pass])
            {
                for (uint32_t index = 0; index < m_queueSize; index++)
                {
                    if (m_inputPicBuffer[pass][index])
                    {
                        X265_FREE(m_inputPicBuffer[pass][index]->planes[0]);
                        x265_picture_free(m_inputPicBuffer[pass][index]);
                    }
                }
                X265_FREE(m_inputPicBuffer[pass]);
            }

            if (pass < m_numEncodes)
            {
                X265_FREE(m_analysisBuffer ? m_analysisBuffer[pass] : nullptr);
                X265_FREE(m_readFlag ? m_readFlag[pass] : nullptr);
                if (m_picIdxReadCnt && m_picIdxReadCnt[pass])
                    delete[] m_picIdxReadCnt[pass];
                if (m_analysisWrite && m_analysisWrite[pass])
                    delete[] m_analysisWrite[pass];
                if (m_analysisRead && m_analysisRead[pass])
                    delete[] m_analysisRead[pass];
            }
        }
        X265_FREE(m_readFlag);
        X265_FREE(m_analysisRead);
        X265_FREE(m_analysisWrite);
        X265_FREE(m_picIdxReadCnt);
        X265_FREE(m_analysisBuffer);
        X265_FREE(m_inputPicBuffer);
        delete[] m_analysisReadCnt;
        delete[] m_analysisWriteCnt;
        delete[] m_picReadCnt;
        delete[] m_picWriteCnt;
        m_readFlag = nullptr;
        m_analysisRead = nullptr;
        m_analysisWrite = nullptr;
        m_picIdxReadCnt = nullptr;
        m_analysisBuffer = nullptr;
        m_inputPicBuffer = nullptr;
        m_analysisReadCnt = nullptr;
        m_analysisWriteCnt = nullptr;
        m_picReadCnt = nullptr;
        m_picWriteCnt = nullptr;
        return false;
    }

    void AbrEncoder::destroy()
    {
        x265_cleanup(); /* Free library singletons */
#if ENABLE_MULTIVIEW
        if(m_numInputViews != 0 && m_inputPicBuffer)
        {
            for (uint8_t pass = 0; pass < m_numInputViews; pass++)
            {
                if (m_inputPicBuffer[pass])
                {
                    for (uint32_t index = 0; index < m_queueSize; index++)
                    {
                        if (m_inputPicBuffer[pass][index])
                        {
                            X265_FREE(m_inputPicBuffer[pass][index]->planes[0]);
                            x265_picture_free(m_inputPicBuffer[pass][index]);
                        }
                    }
                    X265_FREE(m_inputPicBuffer[pass]);
                }

                if (pass == 0)
                {
                    X265_FREE(m_analysisBuffer ? m_analysisBuffer[pass] : nullptr);
                    X265_FREE(m_readFlag ? m_readFlag[pass] : nullptr);
                    if (m_picIdxReadCnt)
                        delete[] m_picIdxReadCnt[pass];
                    if (m_analysisWrite)
                        delete[] m_analysisWrite[pass];
                    if (m_analysisRead)
                        delete[] m_analysisRead[pass];
                    if (m_passEnc && m_passEnc[pass])
                    {
                        m_passEnc[pass]->destroy();
                        delete m_passEnc[pass];
                    }
                }
            }
        }
        else
        {
#endif
            for (uint8_t pass = 0; pass < m_numEncodes; pass++)
            {
                if (m_inputPicBuffer && m_inputPicBuffer[pass])
                {
                    for (uint32_t index = 0; index < m_queueSize; index++)
                    {
                        if (m_inputPicBuffer[pass][index])
                        {
                            X265_FREE(m_inputPicBuffer[pass][index]->planes[0]);
                            x265_picture_free(m_inputPicBuffer[pass][index]);
                        }
                        if (m_param && m_analysisBuffer && m_analysisBuffer[pass])
                            x265_free_analysis_data(&m_param[pass], &m_analysisBuffer[pass][index]);
                    }
                    X265_FREE(m_inputPicBuffer[pass]);
                }

                X265_FREE(m_analysisBuffer ? m_analysisBuffer[pass] : nullptr);
                X265_FREE(m_readFlag ? m_readFlag[pass] : nullptr);
                if (m_picIdxReadCnt)
                    delete[] m_picIdxReadCnt[pass];
                if (m_analysisWrite)
                    delete[] m_analysisWrite[pass];
                if (m_analysisRead)
                    delete[] m_analysisRead[pass];
                if (m_passEnc && m_passEnc[pass])
                {
                    m_passEnc[pass]->destroy();
                    delete m_passEnc[pass];
                }
            }
#if ENABLE_MULTIVIEW
        }
#endif
        X265_FREE(m_inputPicBuffer);
        X265_FREE(m_analysisBuffer);
        X265_FREE(m_readFlag);

        delete[] m_picWriteCnt;
        delete[] m_picReadCnt;
        delete[] m_analysisWriteCnt;
        delete[] m_analysisReadCnt;

        X265_FREE(m_picIdxReadCnt);
        X265_FREE(m_analysisWrite);
        X265_FREE(m_analysisRead);

        X265_FREE(m_passEnc);
        X265_FREE_ZERO(m_param);
    }

    PassEncoder::PassEncoder(uint32_t id, CLIOptions cliopt, AbrEncoder *parent)
    {
        m_id = id;
        m_cliopt = cliopt;
        m_parent = parent;
        for (int view = 0; view < MAX_VIEWS; view++)
            m_input[view] = nullptr;
        if (!(m_cliopt.enableScaler && m_id))
        {
            const int viewCount = getConfiguredViewCount(*m_cliopt.param);
            for (int view = 0; view < viewCount; view++)
                m_input[view] = m_cliopt.input[view];
        }
        m_param = cliopt.param;
        m_inputOver.store(false);
        m_threadActive.store(false);
        m_lastIdx = -1;
        m_encoder = nullptr;
        m_scaler = nullptr;
        m_reader = nullptr;
        m_ret = 0;
    }

    int PassEncoder::init(int &result)
    {
        auto rollbackInputHelper = [&]()
        {
            if (m_reader)
            {
                delete m_reader;
                m_reader = nullptr;
            }
            else if (m_scaler)
            {
                m_scaler->destroy();
                delete m_scaler;
                m_scaler = nullptr;
            }
        };

        if (!m_param)
        {
            x265_log(nullptr, X265_LOG_ERROR, "Missing encoder parameters for encoder %u\n", m_id);
            result = 4;
            m_ret = 4;
            return -1;
        }

        if (m_parent->m_numEncodes > 1)
            setReuseLevel();
        if (m_ret)
        {
            if (!result)
                result = m_ret;
            return -1;
        }
        
        const bool useScaler = usesAbrScalerMode(m_cliopt, m_id);
        if (!(m_cliopt.enableScaler && m_id))
        {
            m_reader = new (std::nothrow) Reader(m_id, this);
            if (!m_reader)
            {
                x265_log(m_param, X265_LOG_ERROR, "\n MALLOC failure in Reader");
                result = 4;
                m_ret = 4;
                return -1;
            }
        }
        else if (useScaler)
        {
            VideoDesc *src = nullptr, *dst = nullptr;
            dst = new (std::nothrow) VideoDesc(m_param->sourceWidth, m_param->sourceHeight, m_param->internalCsp, m_param->internalBitDepth);
            PassEncoder *srcPass = m_parent->m_passEnc[m_id - 1];
            if (!srcPass || !srcPass->m_param)
            {
                delete dst;
                x265_log(m_param, X265_LOG_ERROR, "Missing scaler source parameters for encoder %u\n", m_id);
                result = 4;
                m_ret = 4;
                return -1;
            }
            int dstW = srcPass->m_param->sourceWidth;
            int dstH = srcPass->m_param->sourceHeight;
            src = new (std::nothrow) VideoDesc(dstW, dstH, m_param->internalCsp, m_param->internalBitDepth);
            if (!src || !dst)
            {
                delete src;
                delete dst;
                x265_log(m_param, X265_LOG_ERROR, "\n MALLOC failure in Scaler");
                result = 4;
                m_ret = 4;
                return -1;
            }
            if (src != nullptr && dst != nullptr)
            {
                m_scaler = new (std::nothrow) Scaler(0, 1, m_id, src, dst, this);
                if (!m_scaler)
                {
                    delete src;
                    delete dst;
                    x265_log(m_param, X265_LOG_ERROR, "\n MALLOC failure in Scaler");
                    result = 4;
                    m_ret = 4;
                    return -1;
                }
                else if (!m_scaler->m_initOk)
                {
                    rollbackInputHelper();
                    result = 4;
                    m_ret = 4;
                    return -1;
                }
            }
        }
        m_param->isAbrLadderEnable = m_parent->m_numEncodes > 1;
        if (m_cliopt.zoneFile)
        {
            if (!m_cliopt.parseZoneFile())
            {
                x265_log(nullptr, X265_LOG_ERROR, "Unable to parse zonefile\n");
                bool closeFailed = std::ferror(m_cliopt.zoneFile) != 0;
                if (std::fclose(m_cliopt.zoneFile))
                    closeFailed = true;
                if (closeFailed)
                    x265_log(m_param, X265_LOG_WARNING, "Unable to close zonefile after parse failure\n");
                m_cliopt.zoneFile = nullptr;
                if (m_parent && m_parent->m_clioptArray)
                    m_parent->m_clioptArray[m_id].zoneFile = nullptr;
                rollbackInputHelper();
                m_ret = 1;
                if (!result)
                    result = m_ret;
                return -1;
            }
        }

        for (auto &&i : m_cliopt.filters)
        {
            if (!i)
            {
                rollbackInputHelper();
                m_ret = 4;
                if (!result)
                    result = m_ret;
                return -1;
            }
            i->setParam(m_param);
            if (i->isFail())
            {
                rollbackInputHelper();
                m_ret = 4;
                if (!result)
                    result = m_ret;
                return -1;
            }
        }
        if (!m_cliopt.output)
        {
            rollbackInputHelper();
            m_ret = 3;
            if (!result)
                result = m_ret;
            return -1;
        }
        m_cliopt.output->setParam(m_param);
        if (m_cliopt.output->isFail())
        {
            rollbackInputHelper();
            m_ret = 3;
            if (!result)
                result = m_ret;
            return -1;
        }
        /* note: we could try to acquire a different libx265 API here based on
        * the profile found during option parsing, but it must be done before
        * opening an encoder */

        if (!m_cliopt.api)
        {
            rollbackInputHelper();
            m_ret = 2;
            if (!result)
                result = m_ret;
            return -1;
        }
        if (m_param)
            m_encoder = m_cliopt.api->encoder_open(m_param);
        if (!m_encoder)
        {
            x265_log(nullptr, X265_LOG_ERROR, "x265_encoder_open() failed for Enc, \n");
            rollbackInputHelper();
            m_ret = 2;
            if (!result)
                result = m_ret;
            return -1;
        }

        /* get the encoder parameters post-initialization */
        m_cliopt.api->encoder_parameters(m_encoder, m_param);

        return 1;
    }

    void PassEncoder::setReuseLevel()
    {
        uint32_t r, padh = 0, padw = 0;

        m_param->confWinBottomOffset = m_param->confWinRightOffset = 0;
        configureAbrReuseFileState(m_param, m_cliopt);

        if (m_cliopt.loadLevel)
        {
            PassEncoder *refPass = m_parent->m_passEnc[m_cliopt.refId];
            if (!refPass || !refPass->m_param)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing reference analysis parameters for encoder %u\n", m_id);
                m_ret = 4;
            }
            else
            {
                x265_param *refParam = refPass->m_param;

                int srcH = refParam->sourceHeight - refParam->confWinBottomOffset;
                int srcW = refParam->sourceWidth - refParam->confWinRightOffset;
                if (m_param->sourceHeight == srcH &&
                    m_param->sourceWidth == srcW)
                {
                    propagateAbrRefConfWin(m_parent->m_passEnc[m_id]->m_param, refParam, 1);
                }
                else if (srcH > 0 && srcW > 0)
                {
                    double scaleFactorH = double(m_param->sourceHeight) / srcH;
                    double scaleFactorW = double(m_param->sourceWidth) / srcW;

                    const int roundedScaleFactorHInTenths = static_cast<int>(10 * scaleFactorH + 0.5);
                    const int roundedScaleFactorWInTenths = static_cast<int>(10 * scaleFactorW + 0.5);
                    const bool isDoubleHeightScale = roundedScaleFactorHInTenths == 20;
                    const bool isDoubleWidthScale = roundedScaleFactorWInTenths == 20;

                    if (isDoubleHeightScale && isDoubleWidthScale)
                    {
                        m_param->scaleFactor = 2;
                        propagateAbrRefConfWin(m_parent->m_passEnc[m_id]->m_param, refParam, 2);
                    }
                }
            }
        }

        int h = m_param->sourceHeight + m_param->confWinBottomOffset;
        int w = m_param->sourceWidth + m_param->confWinRightOffset;
        if (h & (m_param->minCUSize - 1))
        {
            r = h & (m_param->minCUSize - 1);
            padh = m_param->minCUSize - r;
            m_param->confWinBottomOffset += padh;

        }

        if (w & (m_param->minCUSize - 1))
        {
            r = w & (m_param->minCUSize - 1);
            padw = m_param->minCUSize - r;
            m_param->confWinRightOffset += padw;
        }
    }

    bool PassEncoder::startThreads()
    {
        auto handleInputWorkerStartFailure = [&](const char* threadName, std::atomic<bool>& workerActive)
        {
            x265_log(m_param, X265_LOG_ERROR, "Unable to start %s thread for encoder %u\n", threadName, m_id);
            if (!m_ret)
                m_ret = 4;
            workerActive.store(false);
            m_inputOver.store(true);
            if (m_parent && m_parent->m_picWriteCnt)
                m_parent->m_picWriteCnt[m_id].poke();
            return false;
        };

        /* Start slave worker threads */
        m_threadActive.store(true);
        if (!start())
        {
            x265_log(m_param, X265_LOG_ERROR, "Unable to start pass thread for encoder %u\n", m_id);
            if (!m_ret)
                m_ret = 4;
            m_threadActive.store(false);
            m_inputOver.store(true);
            m_parent->m_numActiveEncodes.decr();
            return false;
        }
        /* Start reader threads*/
        if (m_reader != nullptr)
        {
            m_reader->m_threadActive.store(true);
            if (!m_reader->start())
                return handleInputWorkerStartFailure("reader", m_reader->m_threadActive);
        }
        /* Start scaling worker threads */
        if (m_scaler != nullptr)
        {
            m_scaler->m_threadActive.store(true);
            if (!m_scaler->start())
                return handleInputWorkerStartFailure("scaler", m_scaler->m_threadActive);
        }

        return true;
    }

    void PassEncoder::copyInfo(x265_analysis_data * src)
    {
        if (!src)
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing analysis source data for encoder %u\n", m_id);
            m_ret = 4;
            return;
        }

        uint32_t written = m_parent->m_analysisWriteCnt[m_id].get();
        int index = selectAnalysisWriteIndex(written);
        if (m_ret)
            return;

        if (!m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[m_id])
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue slot for encoder %u\n", m_id);
            m_ret = 4;
            return;
        }

        x265_analysis_data *m_analysisInfo = &m_parent->m_analysisBuffer[m_id][index];
        if (!prepareAnalysisCopySlot(index, src, m_analysisInfo))
            return;

        bool isVbv = m_param->rc.vbvBufferSize && m_param->rc.vbvMaxBitrate;
        if (m_param->bDisableLookahead && isVbv)
        {
            if (!m_analysisInfo->lookahead.intraSatdForVbv || !src->lookahead.intraSatdForVbv ||
                !m_analysisInfo->lookahead.satdForVbv || !src->lookahead.satdForVbv ||
                !m_analysisInfo->lookahead.intraVbvCost || !src->lookahead.intraVbvCost ||
                !m_analysisInfo->lookahead.vbvCost || !src->lookahead.vbvCost)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing VBV lookahead analysis buffers for encoder %u\n", m_id);
                m_ret = 4;
                return;
            }
            std::memcpy(m_analysisInfo->lookahead.intraSatdForVbv, src->lookahead.intraSatdForVbv, src->numCuInHeight * sizeof(uint32_t));
            std::memcpy(m_analysisInfo->lookahead.satdForVbv, src->lookahead.satdForVbv, src->numCuInHeight * sizeof(uint32_t));
            std::memcpy(m_analysisInfo->lookahead.intraVbvCost, src->lookahead.intraVbvCost, src->numCUsInFrame * sizeof(uint32_t));
            std::memcpy(m_analysisInfo->lookahead.vbvCost, src->lookahead.vbvCost, src->numCUsInFrame * sizeof(uint32_t));
        }

        if (src->sliceType == X265_TYPE_IDR || src->sliceType == X265_TYPE_I)
        {
            if (m_param->analysisSaveReuseLevel < 2)
                goto ret;
            if (!copyIntraAnalysis(m_analysisInfo, src))
                return;
        }
        else
        {
            if (!copyInterAnalysis(m_analysisInfo, src))
                return;
        }

ret:
        //increment analysis Write counter 
        commitAnalysisCopy(index);
        return;
    }

    int PassEncoder::selectAnalysisWriteIndex(uint32_t written)
    {
        int index = written % m_parent->m_queueSize;
        // If all streams have read analysis data, reuse that position in queue.
        int read = m_parent->m_analysisRead[m_id][index].get();
        int write = m_parent->m_analysisWrite[m_id][index].get();

        int overwrite = written / m_parent->m_queueSize;
        bool emptyIdxFound = false;
        while (!emptyIdxFound && overwrite)
        {
            for (uint32_t i = 0; i < m_parent->m_queueSize; i++)
            {
                read = m_parent->m_analysisRead[m_id][i].get();
                write = m_parent->m_analysisWrite[m_id][i].get();
                write *= m_cliopt.numRefs;

                if (read == write)
                {
                    index = i;
                    emptyIdxFound = true;
                    break;
                }
            }
            if (!emptyIdxFound && m_threadActive.load())
            {
                int prevReadCnt = m_parent->m_analysisReadCnt[m_id].get();
                m_parent->m_analysisReadCnt[m_id].waitForChange(prevReadCnt);
            }
        }
        if (!emptyIdxFound && overwrite)
        {
            x265_log(m_param, X265_LOG_ERROR, "Timed out waiting for reusable analysis queue slot for encoder %u\n", m_id);
            m_ret = 4;
        }

        return index;
    }

    bool PassEncoder::loadAnalysisData(int ipread, int& ipwrite, int& readPos, x265_analysis_data*& resultData)
    {
        /*If stream is master of each slave pass, then fetch analysis data from prev pass*/
        int analysisQId = m_cliopt.refId;
        PassEncoder *analysisPass = m_parent->m_passEnc[analysisQId];
        if (!analysisPass || !m_parent->m_analysisBuffer || !m_parent->m_analysisBuffer[analysisQId] ||
            !m_parent->m_analysisRead || !m_parent->m_analysisRead[analysisQId] ||
            !m_parent->m_analysisWrite || !m_parent->m_analysisWrite[analysisQId] ||
            !m_parent->m_analysisReadCnt || !m_parent->m_analysisWriteCnt)
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing analysis queue state for encoder %u\n", m_id);
            m_ret = 4;
            return false;
        }
        /*Check and wait if there any analysis Data to read*/
        int analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].get();
        int written = analysisWrite * analysisPass->m_cliopt.numRefs;
        int analysisRead = m_parent->m_analysisReadCnt[analysisQId].get();

        while (m_threadActive.load() && written == analysisRead)
        {
            analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].waitForChange(analysisWrite);
            written = analysisWrite * analysisPass->m_cliopt.numRefs;
        }

        if (analysisRead < written)
        {
            int analysisIdx = 0;
            if (!m_param->bDisableLookahead)
            {
                bool analysisdRead = false;
                while ((analysisRead < written) && !analysisdRead)
                {
                    while (analysisWrite < ipread)
                    {
                        analysisWrite = m_parent->m_analysisWriteCnt[analysisQId].waitForChange(analysisWrite);
                        written = analysisWrite * analysisPass->m_cliopt.numRefs;
                    }
                    for (uint32_t i = 0; i < m_parent->m_queueSize; i++)
                    {
                        resultData = &m_parent->m_analysisBuffer[analysisQId][i];
                        int read = m_parent->m_analysisRead[analysisQId][i].get();
                        int write = m_parent->m_analysisWrite[analysisQId][i].get() * analysisPass->m_cliopt.numRefs;
                        if ((resultData->poc == (uint32_t)(ipread)) && (read < write))
                        {
                            analysisIdx = i;
                            analysisdRead = true;
                            break;
                        }
                    }
                }
            }
            else
            {
                analysisIdx = analysisRead % m_parent->m_queueSize;
                resultData = &m_parent->m_analysisBuffer[analysisQId][analysisIdx];
                int slotWrite = m_parent->m_analysisWrite[analysisQId][analysisIdx].get();
                while (m_threadActive.load() && resultData->poc == (uint32_t)ipread && !slotWrite)
                    slotWrite = m_parent->m_analysisWrite[analysisQId][analysisIdx].waitForChange(slotWrite);
                int write = slotWrite * analysisPass->m_cliopt.numRefs;
                int read = m_parent->m_analysisRead[analysisQId][analysisIdx].get();
                if ((resultData->poc != (uint32_t)ipread) || (read >= write))
                {
                    x265_log(m_param, X265_LOG_ERROR, "Mismatched no-lookahead analysis slot for frame %d at slot %d encoder %u\n",
                        ipread, analysisIdx, m_id);
                    m_ret = 4;
                    return false;
                }
                readPos = resultData->poc % m_parent->m_queueSize;
                while ((ipwrite < readPos) || ((ipwrite - 1) < (int)resultData->poc))
                {
                    ipwrite = m_parent->m_picWriteCnt[m_id].waitForChange(ipwrite);
                }
            }

            m_lastIdx = analysisIdx;
            return true;
        }

        return false;
    }

    bool PassEncoder::copyIntraAnalysis(x265_analysis_data* dstAnalysis, const x265_analysis_data* srcAnalysis)
    {
        x265_analysis_intra_data *intraDst, *intraSrc;
        intraDst = (x265_analysis_intra_data*)dstAnalysis->intraData;
        intraSrc = (x265_analysis_intra_data*)srcAnalysis->intraData;
        if (!intraDst || !intraSrc)
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing intra analysis buffers for encoder %u\n", m_id);
            m_ret = 4;
            return false;
        }
        if (!intraDst->depth || !intraSrc->depth || !intraDst->modes || !intraSrc->modes ||
            !intraDst->partSizes || !intraSrc->partSizes || !intraDst->chromaModes || !intraSrc->chromaModes)
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing intra analysis array buffers for encoder %u\n", m_id);
            m_ret = 4;
            return false;
        }
        std::memcpy(intraDst->depth, intraSrc->depth, sizeof(uint8_t) * srcAnalysis->depthBytes);
        std::memcpy(intraDst->modes, intraSrc->modes, sizeof(uint8_t) * srcAnalysis->numCUsInFrame * srcAnalysis->numPartitions);
        std::memcpy(intraDst->partSizes, intraSrc->partSizes, sizeof(char) * srcAnalysis->depthBytes);
        std::memcpy(intraDst->chromaModes, intraSrc->chromaModes, sizeof(uint8_t) * srcAnalysis->depthBytes);
        if (m_param->rc.cuTree)
        {
            if (!intraDst->cuQPOff || !intraSrc->cuQPOff)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing intra cuTree analysis buffers for encoder %u\n", m_id);
                m_ret = 4;
                return false;
            }
            std::memcpy(intraDst->cuQPOff, intraSrc->cuQPOff, sizeof(int8_t) * srcAnalysis->depthBytes);
        }

        return true;
    }

    bool PassEncoder::prepareAnalysisCopySlot(int index, x265_analysis_data* srcAnalysis, x265_analysis_data*& dstAnalysis)
    {
        (void)index;

        if (!srcAnalysis || !dstAnalysis)
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing analysis copy slot state for encoder %u\n", m_id);
            m_ret = 4;
            return false;
        }

        x265_free_analysis_data(m_param, dstAnalysis);
        std::memcpy(dstAnalysis, srcAnalysis, sizeof(x265_analysis_data));
        dstAnalysis->wt = nullptr;
        x265_alloc_analysis_data(m_param, dstAnalysis);
        return true;
    }

    void PassEncoder::commitAnalysisCopy(int index)
    {
        // Increment analysis write counters only after the destination slot is fully populated.
        m_parent->m_analysisWriteCnt[m_id].incr();
        m_parent->m_analysisWrite[m_id][index].incr();
    }

    bool PassEncoder::copyInterAnalysis(x265_analysis_data* dstAnalysis, const x265_analysis_data* srcAnalysis)
    {
        bool bIntraInInter = (srcAnalysis->sliceType == X265_TYPE_P || m_param->bIntraInBFrames);
        int numDir = 2;
        if (srcAnalysis->sliceType == X265_TYPE_P)
            numDir = 1;
        if (!dstAnalysis->wt || !srcAnalysis->wt)
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing weighted prediction buffers for encoder %u\n", m_id);
            m_ret = 4;
            return false;
        }
        std::memcpy(dstAnalysis->wt, srcAnalysis->wt, sizeof(WeightParam) * 3 * numDir);
        if (m_param->analysisSaveReuseLevel < 2)
            return true;

        x265_analysis_inter_data *interDst, *interSrc;
        interDst = (x265_analysis_inter_data*)dstAnalysis->interData;
        interSrc = (x265_analysis_inter_data*)srcAnalysis->interData;
        if (!interDst || !interSrc)
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing inter analysis buffers for encoder %u\n", m_id);
            m_ret = 4;
            return false;
        }
        if (!interDst->depth || !interSrc->depth || !interDst->modes || !interSrc->modes)
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing inter analysis array buffers for encoder %u\n", m_id);
            m_ret = 4;
            return false;
        }
        std::memcpy(interDst->depth, interSrc->depth, sizeof(uint8_t) * srcAnalysis->depthBytes);
        std::memcpy(interDst->modes, interSrc->modes, sizeof(uint8_t) * srcAnalysis->depthBytes);
        if (m_param->rc.cuTree)
        {
            if (!interDst->cuQPOff || !interSrc->cuQPOff)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing inter cuTree analysis buffers for encoder %u\n", m_id);
                m_ret = 4;
                return false;
            }
            std::memcpy(interDst->cuQPOff, interSrc->cuQPOff, sizeof(int8_t) * srcAnalysis->depthBytes);
        }
        if (m_param->analysisSaveReuseLevel > 4)
        {
            if (!interDst->partSize || !interSrc->partSize || !interDst->mergeFlag || !interSrc->mergeFlag)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing inter partition analysis buffers for encoder %u\n", m_id);
                m_ret = 4;
                return false;
            }
            std::memcpy(interDst->partSize, interSrc->partSize, sizeof(uint8_t) * srcAnalysis->depthBytes);
            std::memcpy(interDst->mergeFlag, interSrc->mergeFlag, sizeof(uint8_t) * srcAnalysis->depthBytes);
            if (m_param->analysisSaveReuseLevel == 10)
            {
                if (!interDst->interDir || !interSrc->interDir)
                {
                    x265_log(m_param, X265_LOG_ERROR, "Missing inter direction analysis buffers for encoder %u\n", m_id);
                    m_ret = 4;
                    return false;
                }
                std::memcpy(interDst->interDir, interSrc->interDir, sizeof(uint8_t) * srcAnalysis->depthBytes);
                for (int dir = 0; dir < numDir; dir++)
                {
                    if (!interDst->mvpIdx[dir] || !interSrc->mvpIdx[dir] ||
                        !interDst->refIdx[dir] || !interSrc->refIdx[dir] ||
                        !interDst->mv[dir] || !interSrc->mv[dir])
                    {
                        x265_log(m_param, X265_LOG_ERROR, "Missing motion vector analysis buffers for encoder %u direction %d\n", m_id, dir);
                        m_ret = 4;
                        return false;
                    }
                    std::memcpy(interDst->mvpIdx[dir], interSrc->mvpIdx[dir], sizeof(uint8_t) * srcAnalysis->depthBytes);
                    std::memcpy(interDst->refIdx[dir], interSrc->refIdx[dir], sizeof(int8_t) * srcAnalysis->depthBytes);
                    std::memcpy(interDst->mv[dir], interSrc->mv[dir], sizeof(MV) * srcAnalysis->depthBytes);
                }
                if (bIntraInInter)
                {
                    x265_analysis_intra_data *intraDst = (x265_analysis_intra_data*)dstAnalysis->intraData;
                    x265_analysis_intra_data *intraSrc = (x265_analysis_intra_data*)srcAnalysis->intraData;
                    if (!intraDst || !intraSrc)
                    {
                        x265_log(m_param, X265_LOG_ERROR, "Missing intra-in-inter analysis buffers for encoder %u\n", m_id);
                        m_ret = 4;
                        return false;
                    }
                    if (!intraDst->modes || !intraSrc->modes || !intraDst->chromaModes || !intraSrc->chromaModes)
                    {
                        x265_log(m_param, X265_LOG_ERROR, "Missing intra-in-inter analysis arrays for encoder %u\n", m_id);
                        m_ret = 4;
                        return false;
                    }
                    std::memcpy(intraDst->modes, intraSrc->modes, sizeof(uint8_t) * srcAnalysis->numPartitions * srcAnalysis->numCUsInFrame);
                    std::memcpy(intraDst->chromaModes, intraSrc->chromaModes, sizeof(uint8_t) * srcAnalysis->depthBytes);
                }
            }
        }
        if (m_param->analysisSaveReuseLevel != 10)
        {
            if (!interDst->ref || !interSrc->ref)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing inter reference analysis buffers for encoder %u\n", m_id);
                m_ret = 4;
                return false;
            }
            std::memcpy(interDst->ref, interSrc->ref, sizeof(int32_t) * srcAnalysis->numCUsInFrame * X265_MAX_PRED_MODE_PER_CTU * numDir);
        }

        return true;
    }

    void PassEncoder::copyInputPictureState(x265_picture* dstPic, const x265_picture* srcPic)
    {
        dstPic->colorSpace = srcPic->colorSpace;
        dstPic->bitDepth = srcPic->bitDepth;
        dstPic->framesize = srcPic->framesize;
        dstPic->height = srcPic->height;
        dstPic->pts = srcPic->pts;
        dstPic->dts = srcPic->dts;
        dstPic->reorderedPts = srcPic->reorderedPts;
        dstPic->width = srcPic->width;
        dstPic->analysisData = srcPic->analysisData;
        dstPic->userSEI = srcPic->userSEI;
        dstPic->stride[0] = srcPic->stride[0];
        dstPic->stride[1] = srcPic->stride[1];
        dstPic->stride[2] = srcPic->stride[2];
        dstPic->planes[0] = srcPic->planes[0];
        dstPic->planes[1] = srcPic->planes[1];
        dstPic->planes[2] = srcPic->planes[2];
        dstPic->planes[3] = srcPic->planes[3];
        dstPic->format = srcPic->format;
    }

    bool PassEncoder::handleEncodedOutput(uint32_t numEncoded, x265_picture* pic_recon, x265_picture pic_out[],
                                          ReconPlay* reconPlay, x265_analysis_data* analysisInfo,
                                          x265_nal* p_nal, uint32_t nal, uint32_t& outFrameCount,
                                          std::priority_queue<int64_t>* pts_queue, bool isAbrSave)
    {
        if (reconPlay && numEncoded)
        {
            if (!pic_recon)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing recon output state for encoder %u\n", m_id);
                m_ret = 4;
                return false;
            }
            if (!reconPlay->writePicture(*pic_recon))
            {
                x265_log(m_param, X265_LOG_ERROR, "Failed recon playback output for encoder %u\n", m_id);
                m_ret = 4;
                return false;
            }
        }

        outFrameCount += numEncoded;

        if (isAbrSave && numEncoded)
        {
            if (!pic_recon)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing analysis save state for encoder %u\n", m_id);
                m_ret = 4;
                return false;
            }
            copyInfo(analysisInfo);
        }

        for (int layer = 0; layer < m_param->numLayers; layer++)
        {
            if (numEncoded && m_cliopt.recon[layer])
            {
                if (!pic_recon)
                {
                    x265_log(m_param, X265_LOG_ERROR, "Missing layered recon state for encoder %u layer %d\n", m_id, layer);
                    m_ret = 4;
                    return false;
                }
                if (!m_cliopt.recon[layer]->writePicture(pic_out[layer]))
                {
                    x265_log(m_param, X265_LOG_ERROR, "Failed layered recon output for encoder %u layer %d\n", m_id, layer);
                    m_ret = 4;
                    return false;
                }
            }
        }

        if (nal)
        {
            if (m_cliopt.output->needPTS())
            {
                if (!pic_recon)
                {
                    x265_log(m_param, X265_LOG_ERROR, "Missing output picture state for encoder %u\n", m_id);
                    m_ret = 3;
                    return false;
                }
            }
            int frameBytes = m_cliopt.output->writeFrame(p_nal, nal, pic_out[0]);
            if (frameBytes < 0)
            {
                m_ret = 3;
                return false;
            }
            m_cliopt.totalbytes += frameBytes;
            if (pts_queue)
            {
                pts_queue->push(-pic_out[0].pts);
                if (pts_queue->size() > 2)
                    pts_queue->pop();
            }
        }

        m_cliopt.printStatus(outFrameCount);
        return true;
    }


    bool PassEncoder::readPicture(x265_picture* dstPic, int view)
    {
        if (!m_parent->m_picReadCnt || !m_parent->m_picWriteCnt)
        {
            x265_log(m_param, X265_LOG_ERROR, "Missing picture counter state for encoder %u\n", m_id);
            m_ret = 4;
            return false;
        }
        /*Check and wait if there any input frames to read*/
        int ipread = m_parent->m_picReadCnt[m_id].get();
        int ipwrite = m_parent->m_picWriteCnt[m_id].get();

        bool isAbrLoad = m_cliopt.loadLevel && (m_parent->m_numEncodes > 1);
        while (!m_inputOver.load() && (ipread == ipwrite))
        {
            ipwrite = m_parent->m_picWriteCnt[m_id].waitForChange(ipwrite);
        }

        if (m_threadActive.load() && ipread < ipwrite)
        {
            /*Get input index to read from inputQueue. If doesn't need analysis info, it need not wait to fetch poc from analysisQueue*/
            int readPos = ipread % m_parent->m_queueSize;
            x265_analysis_data* analysisData = 0;
            if (!m_parent->m_inputPicBuffer || (m_param->numViews > 1 && !m_parent->m_inputPicBuffer[view]) ||
                (m_param->numViews <= 1 && !m_parent->m_inputPicBuffer[m_id]))
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing input queue state for encoder %u view %d\n", m_id, view);
                m_ret = 4;
                return false;
            }

            if (isAbrLoad)
            {
                if (!loadAnalysisData(ipread, ipwrite, readPos, analysisData))
                    return false;
            }

            x265_picture* srcPic = (m_param->numViews > 1) ? (x265_picture*)(m_parent->m_inputPicBuffer[view][readPos]) : (x265_picture*)(m_parent->m_inputPicBuffer[m_id][readPos]);
            if (!srcPic)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing input picture at queue position %d for view %d\n", readPos, view);
                m_ret = 4;
                return false;
            }

            x265_picture* pic = dstPic;
            copyInputPictureState(pic, srcPic);
            if (isAbrLoad)
            {
                if (!analysisData)
                {
                    x265_log(m_param, X265_LOG_ERROR, "Missing analysis data for frame %d\n", ipread);
                    m_ret = 4;
                    return false;
                }
                pic->analysisData = *analysisData;
            }
            return true;
        }
        else
            return false;
    }

    void PassEncoder::threadMain()
    {
        THREAD_NAME("PassEncoder", m_id);

        while (m_threadActive.load())
        {

#if ENABLE_LIBVMAF
            x265_vmaf_data* vmafdata = m_cliopt.vmafData;
#endif
            if (!m_parent->m_param)
            {
                x265_log(m_param, X265_LOG_ERROR, "Missing parent parameter cache for encoder %u\n", m_id);
                m_ret = 4;
                m_threadActive.store(false);
                m_parent->m_numActiveEncodes.decr();
                return;
            }
            std::memcpy(&m_parent->m_param[m_id], m_param, sizeof(x265_param));
#ifdef SVT_HEVC
            m_parent->m_param[m_id].svtHevcParam = nullptr;
#endif
            /* This allows muxers to modify bitstream format */
            if (!m_cliopt.output)
            {
                m_ret = 3;
                m_threadActive.store(false);
                m_parent->m_numActiveEncodes.decr();
                return;
            }
            m_cliopt.output->setParam(m_param);
            if (m_cliopt.output->isFail())
            {
                m_ret = 3;
                m_cliopt.output->closeFile(0, 0);
                m_threadActive.store(false);
                m_parent->m_numActiveEncodes.decr();
                return;
            }
            const x265_api* api = m_cliopt.api;
            if (!api)
            {
                m_ret = 2;
                m_threadActive.store(false);
                m_parent->m_numActiveEncodes.decr();
                return;
            }
            /* This allows muxers to modify bitstream format */
            ReconPlay* reconPlay = nullptr;
            const char* profileName = m_cliopt.encName[0] ? m_cliopt.encName : "x265";
            x265_picture pic_orig[MAX_VIEWS];
            x265_picture* pic_in[MAX_VIEWS] = { nullptr };
            std::priority_queue<int64_t>* pts_queue = nullptr;
            x265_picture* pic_recon = nullptr;
            x265_picture pic_out[MAX_LAYERS];
            uint32_t inFrameCount = 0;
            uint32_t outFrameCount = 0;
            x265_nal* p_nal = nullptr;
            x265_stats stats = {};
            uint32_t nal = 0;
            int16_t* errorBuf = nullptr;
            bool bDolbyVisionRPU = false;
            uint8_t* rpuPayloads[MAX_VIEWS] = { nullptr };
            uint8_t* fieldRpuPayloads[2] = { nullptr, nullptr };
            int inputPicNum = 1;
            x265_picture picField1, picField2;
            bool fieldBuffersCreated = false;
            bool hasReconOutput = false;
            bool hasAnalysisData = false;
            bool needsPtsQueue = false;
            bool hasReconPlay = false;
            bool hasCsvLog = false;
            bool needsReconPicture = false;
            x265_analysis_data* analysisInfo = &pic_out[0].analysisData;
            bool isAbrSave = m_cliopt.saveLevel && (m_parent->m_numEncodes > 1);
            const int viewCount = getConfiguredViewCount(*m_param);
            auto failDolbyVisionRpu = [&]()
            {
                if (!m_cliopt.dolbyVisionRpu)
                    return;

                bool closeFailed = std::ferror(m_cliopt.dolbyVisionRpu) != 0;
                if (std::fclose(m_cliopt.dolbyVisionRpu))
                    closeFailed = true;
                if (closeFailed)
                    x265_log(m_param, X265_LOG_WARNING, "Unable to close Dolby Vision RPU stream after read failure in %s\n",
                        profileName);
                m_cliopt.dolbyVisionRpu = nullptr;
                if (m_parent && m_parent->m_clioptArray)
                    m_parent->m_clioptArray[m_id].dolbyVisionRpu = nullptr;
            };
            if (m_cliopt.reconPlayCmd)
            {
                reconPlay = new (std::nothrow) ReconPlay(m_cliopt.reconPlayCmd, *m_param);
                if (!reconPlay)
                {
                    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate recon playback helper in %s\n",
                        m_cliopt.encName[0] ? m_cliopt.encName : "x265");
                    m_ret = 4;
                    goto fail;
                }
            }

            if (signal(SIGINT, sigint_handler) == SIG_ERR)
                x265_log(m_param, X265_LOG_ERROR, "Unable to register CTRL+C handler: %s in %s\n",
                    strerror(errno), profileName);

            for (int view = 0; view < viewCount; view++)
                pic_in[view] = &pic_orig[view];
            /* Allocate recon picture if analysis save/load is enabled */
            pts_queue = m_cliopt.output->needPTS() ? new (std::nothrow) std::priority_queue<int64_t>() : nullptr;
            if (m_cliopt.output->needPTS() && !pts_queue)
            {
                x265_log(m_param, X265_LOG_ERROR, "Unable to allocate PTS queue in %s\n",
                    m_cliopt.encName[0] ? m_cliopt.encName : "x265");
                m_ret = 4;
                goto fail;
            }
            hasReconOutput = m_cliopt.recon[0] != nullptr;
            hasAnalysisData = std::strlen(m_param->analysisSave) != 0 || std::strlen(m_param->analysisLoad) != 0;
            needsPtsQueue = pts_queue != nullptr;
            hasReconPlay = reconPlay != nullptr;
            hasCsvLog = m_param->csvLogLevel != 0;
            needsReconPicture = hasReconOutput || hasAnalysisData || needsPtsQueue || hasReconPlay || hasCsvLog;
            pic_recon = needsReconPicture ? pic_out : nullptr;

            if (m_param->numViews > 1 && m_param->bField && m_param->interlaceMode)
            {
                x265_log(m_param, X265_LOG_ERROR, "Multiview field/interlace encoding is not supported in %s\n",
                    profileName);
                m_ret = 4;
                goto fail;
            }

            if (!m_param->bRepeatHeaders && !m_param->bEnableSvtHevc)
            {
                if (api->encoder_headers(m_encoder, &p_nal, &nal) < 0)
                {
                    x265_log(m_param, X265_LOG_ERROR, "Failure generating stream headers in %s\n", profileName);
                    m_ret = 3;
                    goto fail;
                }
                else
                {
                    m_cliopt.output->setPS(m_encoder);
                    int headerBytes = m_cliopt.output->writeHeaders(p_nal, nal);
                    if (headerBytes < 0)
                    {
                        m_ret = 3;
                        goto fail;
                    }
                    m_cliopt.totalbytes += headerBytes;
                }
            }

            for (int view = 0; view < viewCount; view++)
            {
                if (m_param->bField && m_param->interlaceMode)
                {
                    api->picture_init(m_param, &picField1);
                    api->picture_init(m_param, &picField2);
                    // return back the original height of input
                    m_param->sourceHeight *= 2;
                    api->picture_init(m_param, &pic_orig[view]);
                }
                else
                    api->picture_init(m_param, &pic_orig[view]);
            }

            if (m_param->dolbyProfile && m_cliopt.dolbyVisionRpu)
            {
                if (m_param->bField && m_param->interlaceMode)
                {
                    fieldRpuPayloads[0] = X265_MALLOC(uint8_t, 1024);
                    fieldRpuPayloads[1] = X265_MALLOC(uint8_t, 1024);
                    if (!fieldRpuPayloads[0] || !fieldRpuPayloads[1])
                    {
                        x265_log(m_param, X265_LOG_ERROR, "Unable to allocate Dolby Vision RPU payload buffers for field input\n");
                        m_ret = 4;
                        goto fail;
                    }
                    picField1.rpu.payload = fieldRpuPayloads[0];
                    picField2.rpu.payload = fieldRpuPayloads[1];
                }
                else
                {
                    for (int view = 0; view < viewCount; view++)
                    {
                        rpuPayloads[view] = X265_MALLOC(uint8_t, 1024);
                        if (!rpuPayloads[view])
                        {
                            x265_log(m_param, X265_LOG_ERROR, "Unable to allocate Dolby Vision RPU payload buffer for view %d\n", view);
                            m_ret = 4;
                            goto fail;
                        }
                        pic_in[view]->rpu.payload = rpuPayloads[view];
                    }
                }
                bDolbyVisionRPU = true;
            }

            if (m_cliopt.bDither)
            {
                errorBuf = X265_MALLOC(int16_t, m_param->sourceWidth + 1);
                if (errorBuf)
                    std::fill_n(errorBuf, m_param->sourceWidth + 1, int16_t(0));
                else
                    m_cliopt.bDither = false;
            }

            // main encoder loop
            while (pic_in[0] && !b_ctrl_c)
            {
                for (int view = 0; view < viewCount; view++)
                {
                    pic_in[view] = &pic_orig[view];
                    pic_orig[view].poc = (m_param->bField && m_param->interlaceMode) ? inFrameCount * 2 : inFrameCount;
                    if (m_cliopt.qpfile)
                    {
                        if (!m_cliopt.parseQPFile(pic_orig[view]))
                        {
                            x265_log(nullptr, X265_LOG_ERROR, "can't parse qpfile for frame %d in %s\n",
                                pic_orig[view].poc, profileName);
                            bool closeFailed = std::ferror(m_cliopt.qpfile) != 0;
                            if (std::fclose(m_cliopt.qpfile))
                                closeFailed = true;
                            if (closeFailed)
                                x265_log(m_param, X265_LOG_WARNING, "Unable to close qpfile after parse failure in %s\n",
                                    profileName);
                            m_cliopt.qpfile = nullptr;
                            if (m_parent && m_parent->m_clioptArray)
                                m_parent->m_clioptArray[m_id].qpfile = nullptr;
                            m_ret = 1;
                            goto fail;
                        }
                    }

                    if (m_cliopt.framesToBeEncoded && inFrameCount >= m_cliopt.framesToBeEncoded)
                        pic_in[view] = nullptr;
                    else if (readPicture(pic_in[view], view)){
                        if(view == viewCount - 1)
                            inFrameCount++;
                    }
                    else if (m_ret != 0)
                        goto fail;
                    else
                        pic_in[view] = nullptr;
                    if (pic_in[view])
                    {
                        if (pic_in[view]->bitDepth > m_param->internalBitDepth && m_cliopt.bDither)
                        {
                            if (!m_cliopt.input[view])
                            {
                                x265_log(m_param, X265_LOG_ERROR, "Missing dither input state for view %d in %s\n",
                                    view, profileName);
                                m_ret = 4;
                                goto fail;
                            }
                            x265_dither_image(pic_in[view], m_cliopt.input[view]->getWidth(), m_cliopt.input[view]->getHeight(), errorBuf, m_param->internalBitDepth);
                            pic_in[view]->bitDepth = m_param->internalBitDepth;
                        }
                        /* Overwrite PTS */
                        pic_in[view]->pts = pic_in[view]->poc;

                        // convert to field
                        if (m_param->bField && m_param->interlaceMode)
                        {
                            int height = pic_in[view]->height >> 1;

                            if (!fieldBuffersCreated)
                            {
                                inputPicNum = 2;
                                picField1.fieldNum = 1;
                                picField2.fieldNum = 2;

                                picField1.bitDepth = picField2.bitDepth = pic_in[view]->bitDepth;
                                picField1.colorSpace = picField2.colorSpace = pic_in[view]->colorSpace;
                                picField1.height = picField2.height = pic_in[view]->height >> 1;
                                picField1.framesize = picField2.framesize = pic_in[view]->framesize >> 1;

                                size_t fieldFrameSize = (size_t)pic_in[view]->framesize >> 1;
                                char* field1Buf = X265_MALLOC(char, fieldFrameSize);
                                char* field2Buf = X265_MALLOC(char, fieldFrameSize);
                                if (!field1Buf || !field2Buf)
                                {
                                    X265_FREE(field1Buf);
                                    X265_FREE(field2Buf);
                                    x265_log(m_param, X265_LOG_ERROR, "Unable to allocate field picture buffers for view %d in %s\n",
                                        view, profileName);
                                    m_ret = 4;
                                    goto fail;
                                }

                                uint64_t requiredFieldFrameSize = pic_in[view]->stride[0] *
                                    (height >> x265_cli_csps[pic_in[view]->colorSpace].height[0]);
                                for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)
                                    requiredFieldFrameSize += pic_in[view]->stride[i] *
                                        (height >> x265_cli_csps[pic_in[view]->colorSpace].height[i]);
                                if (requiredFieldFrameSize != fieldFrameSize || requiredFieldFrameSize != picField1.framesize)
                                {
                                    X265_FREE(field1Buf);
                                    X265_FREE(field2Buf);
                                    x265_log(m_param, X265_LOG_ERROR, "Field picture layout mismatch for view %d in %s\n",
                                        view, profileName);
                                    m_ret = 4;
                                    goto fail;
                                }

                                int stride = picField1.stride[0] = picField2.stride[0] = pic_in[view]->stride[0];
                                uint64_t framesize = stride * (height >> x265_cli_csps[pic_in[view]->colorSpace].height[0]);
                                picField1.planes[0] = field1Buf;
                                picField2.planes[0] = field2Buf;
                                for (int i = 1; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)
                                {
                                    picField1.planes[i] = field1Buf + framesize;
                                    picField2.planes[i] = field2Buf + framesize;

                                    stride = picField1.stride[i] = picField2.stride[i] = pic_in[view]->stride[i];
                                    framesize += (stride * (height >> x265_cli_csps[pic_in[view]->colorSpace].height[i]));
                                }
                                assert(framesize == requiredFieldFrameSize);
                                fieldBuffersCreated = true;
                            }
                            else if (picField1.bitDepth != pic_in[view]->bitDepth ||
                                picField1.colorSpace != pic_in[view]->colorSpace ||
                                picField1.height != (pic_in[view]->height >> 1) ||
                                picField1.framesize != (pic_in[view]->framesize >> 1))
                            {
                                x265_log(m_param, X265_LOG_ERROR, "Mismatched field buffer metadata for view %d in %s\n",
                                    view, profileName);
                                m_ret = 4;
                                goto fail;
                            }
                            else
                            {
                                for (int i = 0; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)
                                {
                                    if (picField1.stride[i] != pic_in[view]->stride[i] || picField2.stride[i] != pic_in[view]->stride[i])
                                    {
                                        x265_log(m_param, X265_LOG_ERROR, "Mismatched field buffer stride for view %d plane %d in %s\n",
                                            view, i, profileName);
                                        m_ret = 4;
                                        goto fail;
                                    }
                                }
                            }

                            picField1.pts = picField1.poc = pic_in[view]->poc;
                            picField2.pts = picField2.poc = pic_in[view]->poc + 1;

                            picField1.userSEI = picField2.userSEI = pic_in[view]->userSEI;

                            //if (pic_in->userData)
                            //{
                            //    // Have to handle userData here
                            //}

                            if (pic_in[view]->framesize)
                            {
                                for (int i = 0; i < x265_cli_csps[pic_in[view]->colorSpace].planes; i++)
                                {
                                    if (!pic_in[view]->planes[i] || !picField1.planes[i] || !picField2.planes[i])
                                    {
                                        x265_log(m_param, X265_LOG_ERROR, "Missing field plane state for view %d plane %d in %s\n",
                                            view, i, profileName);
                                        m_ret = 4;
                                        goto fail;
                                    }
                                    char* srcP1 = (char*)pic_in[view]->planes[i];
                                    char* srcP2 = (char*)pic_in[view]->planes[i] + pic_in[view]->stride[i];
                                    char* p1 = (char*)picField1.planes[i];
                                    char* p2 = (char*)picField2.planes[i];

                                    int stride = picField1.stride[i];

                                    for (int y = 0; y < (height >> x265_cli_csps[pic_in[view]->colorSpace].height[i]); y++)
                                    {
                                        std::memcpy(p1, srcP1, stride);
                                        std::memcpy(p2, srcP2, stride);
                                        srcP1 += 2 * stride;
                                        srcP2 += 2 * stride;
                                        p1 += stride;
                                        p2 += stride;
                                    }
                                }
                            }
                        }

                        if (bDolbyVisionRPU)
                        {

                            if (m_param->bField && m_param->interlaceMode)
                            {
                                if (m_cliopt.rpuParser(&picField1) > 0)
                                {
                                    if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))
                                        failDolbyVisionRpu();
                                    m_ret = 4;
                                    goto fail;
                                }
                                if (m_cliopt.rpuParser(&picField2) > 0)
                                {
                                    if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))
                                        failDolbyVisionRpu();
                                    m_ret = 4;
                                    goto fail;
                                }
                            }
                            else
                            {
                                if (m_cliopt.rpuParser(pic_in[view]) > 0)
                                {
                                    if (m_cliopt.dolbyVisionRpu && std::ferror(m_cliopt.dolbyVisionRpu))
                                        failDolbyVisionRpu();
                                    m_ret = 4;
                                    goto fail;
                                }
                            }
                        }
                    }
                }

                if (m_param->numViews > 1)
                {
                    bool hasPrimaryView = pic_in[0] != nullptr;
                    for (int view = 1; view < viewCount; view++)
                    {
                        if (hasPrimaryView != (pic_in[view] != nullptr))
                        {
                            x265_log(m_param, X265_LOG_ERROR, "Mismatched multiview input state for view %d in %s\n",
                                view, profileName);
                            m_ret = 4;
                            goto fail;
                        }
                    }
                }

                for (int inputNum = 0; inputNum < inputPicNum; inputNum++)
                {
                    x265_picture* picInput = nullptr;
                    if (inputPicNum == 2)
                        picInput = *pic_in ? (inputNum ? &picField2 : &picField1) : nullptr;
                    else
                        picInput = *pic_in;

                    int numEncoded = api->encoder_encode(m_encoder, &p_nal, &nal, picInput, pic_recon);

                    int idx = (inFrameCount - 1) % m_parent->m_queueSize;
                    if (!m_parent->m_picIdxReadCnt || !m_parent->m_picIdxReadCnt[m_id] || !m_parent->m_picReadCnt)
                    {
                        x265_log(m_param, X265_LOG_ERROR, "Missing encoder queue counter state for encoder %u\n", m_id);
                        m_ret = 4;
                        goto fail;
                    }
                    m_parent->m_picIdxReadCnt[m_id][idx].incr();
                    m_parent->m_picReadCnt[m_id].incr();
                    if (m_cliopt.loadLevel && picInput)
                    {
                        if (m_lastIdx < 0 || !m_parent->m_analysisRead || !m_parent->m_analysisRead[m_cliopt.refId] ||
                            !m_parent->m_analysisReadCnt)
                        {
                            x265_log(m_param, X265_LOG_ERROR, "Missing analysis read state for encoder %u\n", m_id);
                            m_ret = 4;
                            goto fail;
                        }
                        m_parent->m_analysisReadCnt[m_cliopt.refId].incr();
                        m_parent->m_analysisRead[m_cliopt.refId][m_lastIdx].incr();
                    }

                    if (numEncoded < 0)
                    {
                        b_ctrl_c = 1;
                        m_ret = 4;
                        break;
                    }

                    if (!handleEncodedOutput(numEncoded, pic_recon, pic_out, reconPlay, analysisInfo,
                                             p_nal, nal, outFrameCount, pts_queue, isAbrSave))
                        goto fail;
                }
            }

            /* Flush the encoder */
            while (!b_ctrl_c)
            {
                int numEncoded = api->encoder_encode(m_encoder, &p_nal, &nal, nullptr, pic_recon);
                if (numEncoded < 0)
                {
                    m_ret = 4;
                    break;
                }

                if (!handleEncodedOutput(numEncoded, pic_recon, pic_out, reconPlay, analysisInfo,
                                         p_nal, nal, outFrameCount, pts_queue, isAbrSave))
                    goto fail;

                if (!numEncoded)
                    break;
            }

            if (bDolbyVisionRPU)
            {
                if (!m_cliopt.dolbyVisionRpu)
                {
                    x265_log(m_param, X265_LOG_ERROR, "Missing Dolby Vision RPU stream state in %s\n",
                        profileName);
                    m_ret = 4;
                    goto fail;
                }

                int nextRpuByte = fgetc(m_cliopt.dolbyVisionRpu);
                if (nextRpuByte != EOF)
                    x265_log(nullptr, X265_LOG_WARNING, "Dolby Vision RPU count is greater than frame count in %s\n",
                        profileName);
                else if (ferror(m_cliopt.dolbyVisionRpu))
                {
                    x265_log(m_param, X265_LOG_ERROR, "Unable to finalize Dolby Vision RPU stream state in %s\n",
                        profileName);
                    failDolbyVisionRpu();
                    m_ret = 4;
                    goto fail;
                }
                else
                    x265_log(nullptr, X265_LOG_INFO, "VES muxing with Dolby Vision RPU file successful in %s\n",
                        profileName);
            }

            /* clear progress report */
            if (m_cliopt.bProgress)
                std::fprintf(stderr, "%*s\r", 80, " ");

        fail:

            delete reconPlay;

            if (m_encoder)
            {
                api->encoder_get_stats(m_encoder, &stats, sizeof(stats));
                if (std::strlen(m_param->csvfn) && !b_ctrl_c)
#if ENABLE_LIBVMAF
                {
                    api->vmaf_encoder_log(m_encoder, m_cliopt.argCnt, m_cliopt.argString, m_cliopt.param, vmafdata);
                    m_cliopt.vmafData = nullptr;
                    if (m_parent && m_parent->m_clioptArray)
                        m_parent->m_clioptArray[m_id].vmafData = nullptr;
                }
#else
                    api->encoder_log(m_encoder, m_cliopt.argCnt, m_cliopt.argString);
#endif
                api->encoder_close(m_encoder);
            }

            int64_t second_largest_pts = 0;
            int64_t largest_pts = 0;
            if (pts_queue)
            {
                if (!pts_queue->empty())
                {
                    largest_pts = -pts_queue->top();
                    pts_queue->pop();
                    second_largest_pts = largest_pts;
                    if (!pts_queue->empty())
                    {
                        second_largest_pts = largest_pts;
                        largest_pts = -pts_queue->top();
                        pts_queue->pop();
                    }
                }
                delete pts_queue;
                pts_queue = nullptr;
            }
            if (m_cliopt.output)
            {
                m_cliopt.output->closeFile(largest_pts, second_largest_pts);
                if (m_cliopt.output->isFail() && !m_ret)
                    m_ret = 3;
            }
            else if (!m_ret)
                m_ret = 3;

            if (b_ctrl_c)
            {
                general_log(m_param, nullptr, X265_LOG_INFO, "aborted at input frame %d, output frame %d in %s\n",
                    m_cliopt.seek + inFrameCount, stats.encodedPictureCount, profileName);
            }

            X265_FREE(errorBuf);
            if (fieldBuffersCreated)
            {
                X265_FREE(picField1.planes[0]);
                X265_FREE(picField2.planes[0]);
                picField1.planes[0] = nullptr;
                picField2.planes[0] = nullptr;
            }
            for (int view = 0; view < MAX_VIEWS; view++)
                X265_FREE(rpuPayloads[view]);
            X265_FREE(fieldRpuPayloads[0]);
            X265_FREE(fieldRpuPayloads[1]);
            if (m_cliopt.loadLevel && m_parent && m_parent->m_analysisReadCnt)
                m_parent->m_analysisReadCnt[m_cliopt.refId].poke();

            m_threadActive.store(false);
            m_parent->m_numActiveEncodes.decr();
        }
    }

    void PassEncoder::destroy()
    {
        stop();
        if (m_reader)
        {
            m_reader->stop();
            delete m_reader;
        }
        else if (m_scaler != nullptr)
        {
            m_scaler->stop();
            m_scaler->destroy();
            delete m_scaler;
        }
    }

    Scaler::Scaler(int threadId, int threadNum, int id, VideoDesc *src, VideoDesc *dst, PassEncoder *parentEnc)
    {
        m_parentEnc = parentEnc;
        m_id = id;
        m_srcFormat = src;
        m_dstFormat = dst;
        m_threadActive.store(false);
        m_scaleFrameSize = 0;
        m_filterManager = nullptr;
        m_initOk = true;
        m_threadId = threadId;
        m_threadTotal = threadNum;

        int csp = dst->m_csp;
        uint32_t pixelbytes = dst->m_inputDepth > 8 ? 2 : 1;
        for (int i = 0; i < x265_cli_csps[csp].planes; i++)
        {
            int w = dst->m_width >> x265_cli_csps[csp].width[i];
            int h = dst->m_height >> x265_cli_csps[csp].height[i];
            m_scalePlanes[i] = w * h * pixelbytes;
            m_scaleFrameSize += m_scalePlanes[i];
        }

        if (src->m_height != dst->m_height || src->m_width != dst->m_width)
        {
            m_filterManager = new (std::nothrow) ScalerFilterManager;
            if (!m_filterManager || m_filterManager->init(4, m_srcFormat, m_dstFormat) < 0)
            {
                x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Unable to initialize ABR ladder scaler\n");
                m_initOk = false;
                delete m_filterManager;
                m_filterManager = nullptr;
            }
        }
    }

    bool Scaler::scalePic(x265_picture * destination, x265_picture * source)
    {
        if (!destination || !source)
            return false;
        x265_param* param = m_parentEnc->m_param;
        int pixelBytes = m_dstFormat->m_inputDepth > 8 ? 2 : 1;
        if (m_srcFormat->m_height != m_dstFormat->m_height || m_srcFormat->m_width != m_dstFormat->m_width)
        {
            void **srcPlane = nullptr, **dstPlane = nullptr;
            int srcStride[3], dstStride[3];
            destination->bitDepth = m_dstFormat->m_inputDepth;
            destination->colorSpace = source->colorSpace;
            destination->framesize = m_scaleFrameSize;
            destination->height = m_dstFormat->m_height;
            destination->width = m_dstFormat->m_width;
            destination->pts = source->pts;
            destination->dts = source->dts;
            destination->reorderedPts = source->reorderedPts;
            destination->poc = source->poc;
            destination->userSEI = source->userSEI;
            destination->format = source->format;
            srcPlane = source->planes;
            dstPlane = destination->planes;
            srcStride[0] = source->stride[0];
            destination->stride[0] = m_dstFormat->m_width * pixelBytes;
            dstStride[0] = destination->stride[0];
            if (param->internalCsp != X265_CSP_I400)
            {
                srcStride[1] = source->stride[1];
                srcStride[2] = source->stride[2];
                destination->stride[1] = destination->stride[0] >> x265_cli_csps[param->internalCsp].width[1];
                destination->stride[2] = destination->stride[0] >> x265_cli_csps[param->internalCsp].width[2];
                dstStride[1] = destination->stride[1];
                dstStride[2] = destination->stride[2];
            }
            if (m_scaleFrameSize)
            {
                m_filterManager->scale_pic(srcPlane, dstPlane, srcStride, dstStride);
                return true;
            }
            else
                x265_log(param, X265_LOG_INFO, "Empty frame received\n");
        }
        return false;
    }

    void Scaler::threadMain()
    {
        THREAD_NAME("Scaler", m_id);

        /* unscaled picture is stored in the last index */
        uint32_t srcId = m_id - 1;
        if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||
            !m_parentEnc->m_parent->m_picIdxReadCnt || !m_parentEnc->m_parent->m_picIdxReadCnt[m_id] ||
            !m_parentEnc->m_parent->m_picIdxReadCnt[srcId] ||
            !m_parentEnc->m_parent->m_inputPicBuffer || !m_parentEnc->m_parent->m_inputPicBuffer[m_id] ||
            !m_parentEnc->m_parent->m_inputPicBuffer[srcId])
        {
            x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing scaler queue state for layer %d\n", m_id);
            if (m_parentEnc)
                m_parentEnc->m_ret = 4;
            m_threadActive.store(false);
            return;
        }
        int QDepth = m_parentEnc->m_parent->m_queueSize;
        while (!m_parentEnc->m_inputOver.load())
        {

            uint32_t scaledWritten = m_parentEnc->m_parent->m_picWriteCnt[m_id].get();

            if (m_parentEnc->m_cliopt.framesToBeEncoded && scaledWritten >= m_parentEnc->m_cliopt.framesToBeEncoded)
                break;

            if (m_threadTotal > 1 && (m_threadId != scaledWritten % m_threadTotal))
            {
                continue;
            }
            uint32_t written = m_parentEnc->m_parent->m_picWriteCnt[srcId].get();

            /*If all the input pictures are scaled by the current scale worker thread wait for input pictures*/
            while (m_threadActive.load() && (scaledWritten == written)) {
                written = m_parentEnc->m_parent->m_picWriteCnt[srcId].waitForChange(written);
            }

            if (m_threadActive.load() && scaledWritten < written)
            {

                int scaledWriteIdx = scaledWritten % QDepth;
                int overWritePicBuffer = scaledWritten / QDepth;
                int read = m_parentEnc->m_parent->m_picIdxReadCnt[m_id][scaledWriteIdx].get();

                while (overWritePicBuffer && read < overWritePicBuffer)
                {
                    read = m_parentEnc->m_parent->m_picIdxReadCnt[m_id][scaledWriteIdx].waitForChange(read);
                }

                if (!m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx])
                {
                    x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate scaled input picture slot\n");
                    m_parentEnc->m_ret = 4;
                    m_threadActive.store(false);
                    m_parentEnc->m_inputOver.store(true);
                    m_parentEnc->m_parent->m_picWriteCnt[srcId].poke();
                    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                    break;
                }

                x265_picture* scaledPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];
                int csp = m_dstFormat->m_csp;
                int pixelBytes = m_dstFormat->m_inputDepth > 8 ? 2 : 1;
                int planeSize[3] = { 0, 0, 0 };
                int stride[3] = { m_dstFormat->m_width * pixelBytes, 0, 0 };
                int frameSize = 0;
                stride[1] = stride[0] >> x265_cli_csps[csp].width[1];
                stride[2] = stride[0] >> x265_cli_csps[csp].width[2];
                for (int i = 0; i < x265_cli_csps[csp].planes; i++)
                {
                    uint32_t h = m_dstFormat->m_height >> x265_cli_csps[csp].height[i];
                    planeSize[i] = h * stride[i];
                    frameSize += planeSize[i];
                }

                if (!scaledPic->planes[0] || scaledPic->framesize != (size_t)frameSize)
                {
                    X265_FREE(scaledPic->planes[0]);
                    scaledPic->planes[0] = X265_MALLOC(char, frameSize);
                    if (!scaledPic->planes[0])
                    {
                        x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate scaled input plane\n");
                        scaledPic->planes[1] = nullptr;
                        scaledPic->planes[2] = nullptr;
                        scaledPic->planes[3] = nullptr;
                        scaledPic->framesize = 0;
                        m_parentEnc->m_ret = 4;
                        m_threadActive.store(false);
                        m_parentEnc->m_inputOver.store(true);
                        m_parentEnc->m_parent->m_picWriteCnt[srcId].poke();
                        m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                        break;
                    }
                }
                scaledPic->framesize = frameSize;
                scaledPic->stride[0] = stride[0];
                scaledPic->stride[1] = stride[1];
                scaledPic->stride[2] = stride[2];
                scaledPic->planes[1] = (char*)scaledPic->planes[0] + planeSize[0];
                scaledPic->planes[2] = (char*)scaledPic->planes[1] + planeSize[1];
                scaledPic->planes[3] = nullptr;

                x265_picture *srcPic = m_parentEnc->m_parent->m_inputPicBuffer[srcId][scaledWritten % QDepth];
                x265_picture* destPic = m_parentEnc->m_parent->m_inputPicBuffer[m_id][scaledWriteIdx];
                if (!srcPic || !destPic)
                {
                    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing scaler queue picture at src %u dst %d\n", scaledWritten % QDepth, scaledWriteIdx);
                    m_parentEnc->m_ret = 4;
                    m_threadActive.store(false);
                    m_parentEnc->m_inputOver.store(true);
                    m_parentEnc->m_parent->m_picWriteCnt[srcId].poke();
                    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                    break;
                }

                // Enqueue this picture up with the current encoder so that it will asynchronously encode
                if (!scalePic(destPic, srcPic))
                {
                    x265_log(nullptr, X265_LOG_ERROR, "Unable to copy scaled input picture to input queue \n");
                    m_parentEnc->m_ret = 4;
                    m_threadActive.store(false);
                    m_parentEnc->m_inputOver.store(true);
                    m_parentEnc->m_parent->m_picWriteCnt[srcId].poke();
                    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                    break;
                }
                m_parentEnc->m_parent->m_picWriteCnt[m_id].incr();
                m_scaledWriteCnt.incr();
                m_parentEnc->m_parent->m_picIdxReadCnt[srcId][scaledWriteIdx].incr();
            }
            if (m_threadTotal > 1)
            {
                written = m_parentEnc->m_parent->m_picWriteCnt[srcId].get();
                int totalWrite = written / m_threadTotal;
                if (written % m_threadTotal > m_threadId)
                    totalWrite++;
                if (totalWrite == m_scaledWriteCnt.get())
                {
                    m_parentEnc->m_parent->m_picWriteCnt[srcId].poke();
                    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                    break;
                }
            }
            else
            {
                /* Once end of video is reached and all frames are scaled, release wait on picwritecount */
                scaledWritten = m_parentEnc->m_parent->m_picWriteCnt[m_id].get();
                written = m_parentEnc->m_parent->m_picWriteCnt[srcId].get();
                if (written == scaledWritten)
                {
                    m_parentEnc->m_parent->m_picWriteCnt[srcId].poke();
                    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                    break;
                }
            }

        }
        m_threadActive.store(false);
        destroy();
    }

    Reader::Reader(int id, PassEncoder *parentEnc)
    {
        m_parentEnc = parentEnc;
        m_id = id;
        m_threadActive.store(false);
        for (int view = 0; view < MAX_VIEWS; view++)
            m_input[view] = parentEnc->m_input[view];
    }

    void Reader::threadMain()
    {
        THREAD_NAME("Reader", m_id);

        if (!m_parentEnc || !m_parentEnc->m_parent || !m_parentEnc->m_parent->m_picWriteCnt ||
            !m_parentEnc->m_parent->m_picIdxReadCnt || !m_parentEnc->m_parent->m_picIdxReadCnt[m_id] ||
            !m_parentEnc->m_parent->m_inputPicBuffer)
        {
            x265_log(m_parentEnc ? m_parentEnc->m_param : nullptr, X265_LOG_ERROR, "Missing reader queue state for layer %d\n", m_id);
            if (m_parentEnc)
                m_parentEnc->m_ret = 4;
            m_threadActive.store(false);
            if (m_parentEnc)
                m_parentEnc->m_inputOver.store(true);
            return;
        }

        int QDepth = m_parentEnc->m_parent->m_queueSize;
        x265_picture* src = x265_picture_alloc();
        if (!src)
        {
            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate reader input picture\n");
            m_parentEnc->m_ret = 4;
            m_threadActive.store(false);
            m_parentEnc->m_inputOver.store(true);
            m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
            return;
        }
        x265_picture_init(m_parentEnc->m_param, src);

        while (m_threadActive.load())
        {
            uint32_t written = m_parentEnc->m_parent->m_picWriteCnt[m_id].get();
            uint32_t writeIdx = written % QDepth;
            uint32_t read = m_parentEnc->m_parent->m_picIdxReadCnt[m_id][writeIdx].get();
            uint32_t overWritePicBuffer = written / QDepth;

            if (m_parentEnc->m_cliopt.framesToBeEncoded && written >= m_parentEnc->m_cliopt.framesToBeEncoded)
                break;

            while (overWritePicBuffer && read < overWritePicBuffer)
            {
                read = m_parentEnc->m_parent->m_picIdxReadCnt[m_id][writeIdx].waitForChange(read);
            }

            const int viewCount = getConfiguredViewCount(*m_parentEnc->m_param);
            for (int view = 0; view < viewCount; view++)
            {
                if (!m_input[view])
                {
                    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader input state for view %d\n", view);
                    m_parentEnc->m_ret = 4;
                    m_threadActive.store(false);
                    m_parentEnc->m_inputOver.store(true);
                    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                    break;
                }
                x265_picture* dest = m_parentEnc->m_parent->m_inputPicBuffer[m_id][writeIdx];
                if (m_parentEnc->m_param->numViews > 1)
                    dest = m_parentEnc->m_parent->m_inputPicBuffer[view][writeIdx];
                if (!dest)
                {
                    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Missing reader queue picture at view %d index %u\n", view, writeIdx);
                    m_parentEnc->m_ret = 4;
                    m_threadActive.store(false);
                    m_parentEnc->m_inputOver.store(true);
                    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                    break;
                }
                src->format = m_parentEnc->m_param->format;
                if (m_input[view]->readPicture(*src))
                {
                    dest->poc = src->poc;
                    dest->pts = src->pts;
                    dest->userSEI = src->userSEI;
                    dest->bitDepth = src->bitDepth;
                    dest->framesize = src->framesize;
                    dest->height = src->height;
                    dest->width = src->width;
                    dest->colorSpace = src->colorSpace;
                    dest->userSEI = src->userSEI;
                    dest->rpu.payload = src->rpu.payload;
                    dest->picStruct = src->picStruct;
                    dest->stride[0] = src->stride[0];
                    dest->stride[1] = src->stride[1];
                    dest->stride[2] = src->stride[2];
                    dest->format = src->format;

                    if (!dest->planes[0])
                    {
                        dest->planes[0] = X265_MALLOC(char, dest->framesize);
                        if (!dest->planes[0])
                        {
                            x265_log(nullptr, X265_LOG_ERROR, "Unable to allocate reader input plane\n");
                            m_parentEnc->m_ret = 4;
                            m_threadActive.store(false);
                            m_parentEnc->m_inputOver.store(true);
                            m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                            break;
                        }
                    }

                    std::memcpy(dest->planes[0], src->planes[0], src->framesize * sizeof(char));
                    int height = (src->height * (src->format == 2 ? 2 : 1));
                    dest->planes[1] = (char*)dest->planes[0] + src->stride[0] * height;
                    dest->planes[2] = (char*)dest->planes[1] + src->stride[1] * (height >> x265_cli_csps[src->colorSpace].height[1]);
#if ENABLE_ALPHA
                    if (m_parentEnc->m_param->numScalableLayers > 1)
                    {
                        dest->planes[3] = (char*)dest->planes[2] + src->stride[2] * (src->height >> x265_cli_csps[src->colorSpace].height[2]);
                    }
#endif
                    if (view == viewCount - 1)
                        m_parentEnc->m_parent->m_picWriteCnt[m_id].incr();
                }
                else if (m_input[view]->isFail())
                {
                    x265_log(m_parentEnc->m_param, X265_LOG_ERROR, "Reader input failed for view %d\n", view);
                    m_parentEnc->m_ret = 4;
                    m_threadActive.store(false);
                    m_parentEnc->m_inputOver.store(true);
                    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                    break;
                }
                else
                {
                    m_threadActive.store(false);
                    m_parentEnc->m_inputOver.store(true);
                    m_parentEnc->m_parent->m_picWriteCnt[m_id].poke();
                    break;
                }
            }
            if (!m_threadActive.load())
                break;
        }
        x265_picture_free(src);
    }
}
