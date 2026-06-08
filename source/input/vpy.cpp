/*****************************************************************************
 * Copyright (C) 2013-2020 MulticoreWare, Inc
 *
 * Authors: Vladimir Kontserenko <djatom@beatrice-raws.org>
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

#include "vpy.h"
#include "common.h"

#include <cstring>

static void frameDoneCallback(void* userData, const VSFrameRef* f, const int n, VSNodeRef* node, const char*)
{
    VSFDCallbackData* vpyCallbackData = static_cast<VSFDCallbackData*>(userData);

    {
        std::lock_guard<std::mutex> lock(vpyCallbackData->reorderMapMutex);
        vpyCallbackData->reorderMap[n] = f;
    }
    ++vpyCallbackData->completedFrames;

    if(!f)
    {
        vpyCallbackData->isRunning = false;
        return;
    }

    size_t retries = 0;
    while((vpyCallbackData->completedFrames - vpyCallbackData->outputFrames) > vpyCallbackData->parallelRequests) // wait until x265 asks more frames
    {
        Sleep(15);
        if(retries > vpyCallbackData->parallelRequests * 1.5) // we don't want to wait for eternity
            break;
        retries++;
    }

    if(vpyCallbackData->requestedFrames < vpyCallbackData->totalFrames && vpyCallbackData->isRunning) // don't ask for new frames if user cancelled execution
    {
        //x265::general_log(nullptr, "vpy", X265_LOG_FULL, "Callback: retries: %d, current frame: %d, requested: %d, completed: %d, output: %d  \n", retries, n, vpyCallbackData->requestedFrames.load(), vpyCallbackData->completedFrames.load(), vpyCallbackData->outputFrames.load());
        vpyCallbackData->vsapi->getFrameAsync(vpyCallbackData->requestedFrames, node, frameDoneCallback, vpyCallbackData);
        ++vpyCallbackData->requestedFrames;
    }
}

using namespace X265_NS;

void VPYInput::load_vs() {
    vpyFailed = true;
    vs_open();
    if (!vss_library)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to load VapourSynth\n");
        return;
    }
    LOAD_VS_FUNC(init, "_vsscript_init@0");
    LOAD_VS_FUNC(finalize, "_vsscript_finalize@0");
    LOAD_VS_FUNC(evaluateFile, "_vsscript_evaluateFile@12");
    LOAD_VS_FUNC(freeScript, "_vsscript_freeScript@4");
    LOAD_VS_FUNC(getError, "_vsscript_getError@4");
    LOAD_VS_FUNC(getOutput, "_vsscript_getOutput@8");
    LOAD_VS_FUNC(getCore, "_vsscript_getCore@4");
    LOAD_VS_FUNC(getVSApi2, "_vsscript_getVSApi2@4");

    if(!vss_func.init())
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to initialize VapourSynth environment\n");
        return;
    }
    vpyCallbackData.vsapi = vsapi = vss_func.getVSApi2(VAPOURSYNTH_API_VERSION);
    if(!vsapi)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth API\n");
        return;
    }

    vpyFailed = false;
    return;
fail:
    general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to load VapourSynth\n");
    vs_close();
}

VPYInput::VPYInput(InputFileInfo& info)
{
    const char * filename_pos = std::strstr(info.filename, "]://");
    if(info.filename[0] == '[' && filename_pos) {
        char real_libname[BUFFER_SIZE] {0};
        std::snprintf(real_libname, sizeof(real_libname), "%s", info.filename + 1);
        std::snprintf(real_filename, sizeof(real_filename), "%s", filename_pos + 4);
        real_libname[filename_pos - info.filename - 1] = 0;
        #if _WIN32
            if(MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, real_libname, -1, libname_buffer, sizeof(libname_buffer)/sizeof(wchar_t))) {
                libname = libname_buffer;
            }
            else {
                general_log(nullptr, "vpy", X265_LOG_ERROR, "Unable to parse VapourSynth library path\n");
                vpyFailed = true;
                return;
            }
        #else
            std::snprintf(libname_buffer, sizeof(libname_buffer), "%s", real_libname);
            libname = libname_buffer;
        #endif
        general_log(nullptr, "vpy", X265_LOG_INFO, "Using external VapourSynth library from %s\n", real_libname);
    }
    else {
        std::snprintf(real_filename, sizeof(real_filename), "%s", info.filename);
    }

    load_vs();
    if(vpyFailed)
        return;

    if (info.skipFrames)
    {
        nextFrame = info.skipFrames;
        vpyCallbackData.outputFrames = nextFrame;
        vpyCallbackData.requestedFrames = nextFrame;
        vpyCallbackData.completedFrames = nextFrame;
        vpyCallbackData.startFrame = nextFrame;
    }

    if(vss_func.evaluateFile(&script, real_filename, efSetWorkingDir))
    {
        const char* scriptError = vss_func.getError(script);
        general_log(nullptr, "vpy", X265_LOG_ERROR, "Can't evaluate script: %s\n", scriptError ? scriptError : "unknown VapourSynth script error");
        vpyFailed = true;
        return;
    }

    node = vss_func.getOutput(script, 0);
    if(!node)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "`%s' has no video data\n", real_filename);
        vpyFailed = true;
        return;
    }

    VSCore* core = vss_func.getCore(script);
    if(!core)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth core\n");
        vpyFailed = true;
        return;
    }

    const VSCoreInfo* core_info = vsapi->getCoreInfo(core);
    if(!core_info)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to query VapourSynth core info\n");
        vpyFailed = true;
        return;
    }
    vpyCallbackData.parallelRequests = core_info->numThreads;
    general_log(nullptr, "vpy", X265_LOG_INFO, "VapourSynth Core R%d\n", core_info->core);

    const VSVideoInfo* vi = vsapi->getVideoInfo(node);
    if(!vi)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth video info\n");
        vpyFailed = true;
        return;
    }
    if(!isConstantFormat(vi))
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "only constant video formats are supported\n");
        vpyFailed = true;
        return;
    }
    if(!vi->format)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "VapourSynth returned a null video format\n");
        vpyFailed = true;
        return;
    }

    info.width = vi->width;
    info.height = vi->height;

    char errbuf[256];
    frame0 = vsapi->getFrame(nextFrame, node, errbuf, sizeof(errbuf));
    if(!frame0)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "%s occurred while getting frame 0\n", errbuf);
        vpyFailed = true;
        return;
    }
    const VSMap* frameProps0 = vsapi->getFramePropsRO(frame0);
    if(!frameProps0)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth frame properties for frame 0\n");
        vpyFailed = true;
        return;
    }

    info.sarWidth = vsapi->propNumElements(frameProps0, "_SARNum") > 0 ? vsapi->propGetInt(frameProps0, "_SARNum", 0, nullptr) : 0;
    info.sarHeight =vsapi->propNumElements(frameProps0, "_SARDen") > 0 ? vsapi->propGetInt(frameProps0, "_SARDen", 0, nullptr) : 0;
    if(vi->fpsNum == 0 && vi->fpsDen == 0) // VFR detection
    {
        int errDurNum, errDurDen;
        int64_t rateDen = vsapi->propGetInt(frameProps0, "_DurationNum", 0, &errDurNum);
        int64_t rateNum = vsapi->propGetInt(frameProps0, "_DurationDen", 0, &errDurDen);

        if(errDurNum || errDurDen)
        {
            general_log(nullptr, "vpy", X265_LOG_ERROR, "VFR: missing FPS values at frame 0");
            vpyFailed = true;
            return;
        }

        if(!rateNum)
        {
            general_log(nullptr, "vpy", X265_LOG_ERROR, "VFR: FPS numerator is zero at frame 0");
            vpyFailed = true;
            return;
        }

        /* Force CFR until we have support for VFR by x265 */
        info.fpsNum   = rateNum;
        info.fpsDenom = rateDen;
        general_log(nullptr, "vpy", X265_LOG_INFO, "VideoNode is VFR, but x265 doesn't support that at the moment. Forcing CFR\n");
    }
    else
    {
        info.fpsNum   = vi->fpsNum;
        info.fpsDenom = vi->fpsDen;
    }

    info.frameCount = vpyCallbackData.totalFrames = vi->numFrames;
    info.depth = vi->format->bitsPerSample;

    if (info.encodeToFrame)
    {
        vpyCallbackData.totalFrames = info.encodeToFrame + nextFrame;
    }

    const char* pixelType = vi->format->name ? vi->format->name : "unknown";
    bool supportedFormat = false;
    if(vi->format->bitsPerSample >= 8 && vi->format->bitsPerSample <= 16)
    {
        if(vi->format->colorFamily == cmYUV)
        {
            if(vi->format->subSamplingW == 0 && vi->format->subSamplingH == 0) {
                info.csp = X265_CSP_I444;
                supportedFormat = true;
                general_log(nullptr, "vpy", X265_LOG_INFO, "Video colorspace: YUV444 (YV24)\n");
            }
            else if(vi->format->subSamplingW == 1 && vi->format->subSamplingH == 0) {
                info.csp = X265_CSP_I422;
                supportedFormat = true;
                general_log(nullptr, "vpy", X265_LOG_INFO, "Video colorspace: YUV422 (YV16)\n");
            }
            else if(vi->format->subSamplingW == 1 && vi->format->subSamplingH == 1) {
                info.csp = X265_CSP_I420;
                supportedFormat = true;
                general_log(nullptr, "vpy", X265_LOG_INFO, "Video colorspace: YUV420 (YV12)\n");
            }
        }
        else if(vi->format->colorFamily == cmGray) {
            info.csp = X265_CSP_I400;
            supportedFormat = true;
            general_log(nullptr, "vpy", X265_LOG_INFO, "Video colorspace: YUV400 (Y8)\n");
        }
    }
    if (!supportedFormat)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "not supported pixel type: %s\n", pixelType);
        vpyFailed = true;
        return;
    }
    general_log(nullptr, "vpy", X265_LOG_INFO, "Video depth: %d\n", info.depth);
    general_log(nullptr, "vpy", X265_LOG_INFO, "Video resolution: %dx%d\n", info.width, info.height);
    general_log(nullptr, "vpy", X265_LOG_INFO, "Video framerate: %d/%d\n", info.fpsNum, info.fpsDenom);
    general_log(nullptr, "vpy", X265_LOG_INFO, "Video framecount: %d\n", info.frameCount);
    vpyCallbackData.reorderMap[nextFrame] = frame0;
    ++vpyCallbackData.completedFrames;
    _info = info;
}

VPYInput::~VPYInput()
{
    if(frame0 && vsapi)
    {
        vsapi->freeFrame(frame0);
        frame0 = nullptr;
    }

    if(node && vsapi)
    {
        vsapi->freeNode(node);
        node = nullptr;
    }

    if (vss_func.freeScript)
        vss_func.freeScript(script);
    script = nullptr;

    if (vss_func.finalize)
        vss_func.finalize();

    if(vss_library)
        vs_close();
}

void VPYInput::startReader()
{
    general_log(nullptr, "vpy", X265_LOG_INFO, "using %d parallel requests\n", vpyCallbackData.parallelRequests);

    const int requestStart = vpyCallbackData.completedFrames;
    const int intitalRequestSize = std::min<int>(vpyCallbackData.parallelRequests, vpyCallbackData.totalFrames - requestStart);
    vpyCallbackData.requestedFrames = requestStart + intitalRequestSize;

    for (int n = requestStart; n < requestStart + intitalRequestSize; n++)
        vsapi->getFrameAsync(n, node, frameDoneCallback, &vpyCallbackData);
}

void VPYInput::release()
{
    vpyCallbackData.isRunning = false;

    while (vpyCallbackData.requestedFrames != vpyCallbackData.completedFrames)
    {
        general_log(nullptr, "vpy", X265_LOG_INFO, "waiting completion of %d requested frames...    \r", vpyCallbackData.requestedFrames.load() - vpyCallbackData.completedFrames.load());
        Sleep(100);
    }

    for (int frame = nextFrame; frame < vpyCallbackData.completedFrames; frame++)
    {
        const VSFrameRef* currentFrame = nullptr;
        {
            std::lock_guard<std::mutex> lock(vpyCallbackData.reorderMapMutex);
            auto currentFrameItr = vpyCallbackData.reorderMap.find(frame);
            if (currentFrameItr != vpyCallbackData.reorderMap.end())
            {
                currentFrame = currentFrameItr->second;
                vpyCallbackData.reorderMap.erase(currentFrameItr);
            }
        }
        if (currentFrame)
        {
            if (currentFrame == frame0)
                frame0 = nullptr;
            vsapi->freeFrame(currentFrame);
        }
    }

    X265_FREE(frame_buffer);
    delete this;
}

bool VPYInput::readPicture(x265_picture& pic)
{
    auto addPlaneBytes = [](size_t& total, int height, int stride, size_t& planeBytes) -> bool
    {
        if (height <= 0 || stride <= 0)
            return false;
        planeBytes = (size_t)height * (size_t)stride;
        if (planeBytes / (size_t)stride != (size_t)height || total > SIZE_MAX - planeBytes)
            return false;
        total += planeBytes;
        return true;
    };

    const VSFrameRef* currentFrame = nullptr;

    if(nextFrame >= vpyCallbackData.totalFrames)
        return false;

    while (true)
    {
        {
            std::lock_guard<std::mutex> lock(vpyCallbackData.reorderMapMutex);
            auto currentFrameItr = vpyCallbackData.reorderMap.find(nextFrame);
            if (currentFrameItr != vpyCallbackData.reorderMap.end())
            {
                currentFrame = currentFrameItr->second;
                vpyCallbackData.reorderMap.erase(currentFrameItr);
                break;
            }
        }
        Sleep(10); // wait for completition a bit
    }
    ++vpyCallbackData.outputFrames;

    if(!currentFrame)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "error occurred while reading frame %d\n", nextFrame);
        vpyFailed = true;
        vpyCallbackData.isRunning = false;
        return false;
    }

    pic.width = _info.width;
    pic.height = _info.height;
    pic.colorSpace = _info.csp;
    pic.bitDepth = _info.depth;

    const int planeCount = x265_cli_csps[_info.csp].planes;
    int planeHeights[3] = { 0 };
    size_t planeBytes[3] = { 0 };

    size_t requiredFrameSize = 0;
    for (int i = 0; i < planeCount; i++)
    {
        planeHeights[i] = vsapi->getFrameHeight(currentFrame, i);
        pic.stride[i] = vsapi->getStride(currentFrame, i);
        if (!addPlaneBytes(requiredFrameSize, planeHeights[i], pic.stride[i], planeBytes[i]))
        {
            general_log(nullptr, "vpy", X265_LOG_ERROR, "Invalid VapourSynth frame geometry at frame %d plane %d\n", nextFrame, i);
            vpyFailed = true;
            vpyCallbackData.isRunning = false;
            if (currentFrame == frame0)
                frame0 = nullptr;
            vsapi->freeFrame(currentFrame);
            return false;
        }
    }

    if (!requiredFrameSize)
    {
        general_log(nullptr, "vpy", X265_LOG_ERROR, "Invalid VapourSynth frame size at frame %d\n", nextFrame);
        vpyFailed = true;
        vpyCallbackData.isRunning = false;
        if (currentFrame == frame0)
            frame0 = nullptr;
        vsapi->freeFrame(currentFrame);
        return false;
    }

    if (requiredFrameSize > frame_size || frame_buffer == nullptr)
    {
        uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));
        if (!newFrameBuffer)
        {
            general_log(nullptr, "vpy", X265_LOG_ERROR, "VapourSynth input buffer allocation failed at frame %d\n", nextFrame);
            vpyFailed = true;
            vpyCallbackData.isRunning = false;
            if (currentFrame == frame0)
                frame0 = nullptr;
            vsapi->freeFrame(currentFrame);
            return false;
        }
        X265_FREE(frame_buffer);
        frame_buffer = newFrameBuffer;
        frame_size = requiredFrameSize;
    }

    pic.framesize = requiredFrameSize;

    uint8_t* ptr = frame_buffer;
    for (int i = 0; i < planeCount; i++)
    {
        pic.planes[i] = ptr;
        if (ptr > frame_buffer + frame_size || planeBytes[i] > (size_t)(frame_buffer + frame_size - ptr))
        {
            general_log(nullptr, "vpy", X265_LOG_ERROR, "Invalid VapourSynth plane copy geometry at frame %d plane %d\n", nextFrame, i);
            vpyFailed = true;
            vpyCallbackData.isRunning = false;
            if (currentFrame == frame0)
                frame0 = nullptr;
            vsapi->freeFrame(currentFrame);
            return false;
        }

        std::memcpy(pic.planes[i], const_cast<unsigned char*>(vsapi->getReadPtr(currentFrame, i)), planeBytes[i]);
        ptr += planeBytes[i];
    }

    if (currentFrame == frame0)
        frame0 = nullptr;
    vsapi->freeFrame(currentFrame);

    nextFrame++; // for Eof method

    return true;
}
