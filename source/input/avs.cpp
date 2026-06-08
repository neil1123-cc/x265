/*****************************************************************************
 * avs.c: avisynth input
 *****************************************************************************
 * Copyright (C) 2020 Xinyue Lu
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
 *****************************************************************************/

#include "avs.h"

#define FAIL_IF_ERROR( cond, ... )\
if( cond )\
{\
    general_log( nullptr, "avs+", X265_LOG_ERROR, __VA_ARGS__ );\
    b_fail = true;\
    return;\
}

using namespace X265_NS;

void AVSInput::load_avs()
{
    avs_open();
    if (!h->library)
        return;
    LOAD_AVS_FUNC(avs_clip_get_error);
    LOAD_AVS_FUNC(avs_create_script_environment);
    LOAD_AVS_FUNC(avs_delete_script_environment);
    LOAD_AVS_FUNC(avs_get_frame);
    LOAD_AVS_FUNC(avs_get_version);
    LOAD_AVS_FUNC(avs_get_video_info);
    LOAD_AVS_FUNC(avs_function_exists);
    LOAD_AVS_FUNC(avs_invoke);
    LOAD_AVS_FUNC(avs_release_clip);
    LOAD_AVS_FUNC(avs_release_value);
    LOAD_AVS_FUNC(avs_release_video_frame);
    LOAD_AVS_FUNC(avs_take_clip);

    LOAD_AVS_FUNC(avs_is_y8);
    LOAD_AVS_FUNC(avs_is_420);
    LOAD_AVS_FUNC(avs_is_422);
    LOAD_AVS_FUNC(avs_is_444);
    LOAD_AVS_FUNC(avs_bits_per_component);
    h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);
    if (!h->env)
    {
        general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\n");
        avs_close();
        return;
    }
    return;
fail:
    avs_close();
}

void AVSInput::info_avs()
{
    if (!h->func.avs_function_exists(h->env, "VersionString"))
        return;
    AVS_Value ver = h->func.avs_invoke(h->env, "VersionString", avs_new_value_array(nullptr, 0), nullptr);
    if(avs_is_error(ver))
        return;
    if(!avs_is_string(ver))
        return;
    const char *version = avs_as_string(ver);
    general_log(nullptr, "avs+", X265_LOG_INFO, "%s\n", version ? version : "unknown");
    h->func.avs_release_value(ver);
}

void AVSInput::openfile(InputFileInfo& info)
{
#ifdef _WIN32
    wchar_t filename_wc[BUFFER_SIZE * 4];
    MultiByteToWideChar(CP_UTF8, 0, real_filename, -1, filename_wc, BUFFER_SIZE);
    WideCharToMultiByte(CP_THREAD_ACP, 0, filename_wc, -1, real_filename, BUFFER_SIZE, nullptr, nullptr);
#endif
    AVS_Value res = h->func.avs_invoke(h->env, "Import", avs_new_value_string(real_filename), nullptr);
    if (avs_is_error(res))
    {
        const char *errorText = avs_as_string(res);
        general_log(nullptr, "avs+", X265_LOG_ERROR, "Error loading file: %s\n", errorText ? errorText : "unknown Avisynth error");
        h->func.avs_release_value(res);
        b_fail = true;
        return;
    }
    if (!avs_is_clip(res))
    {
        general_log(nullptr, "avs+", X265_LOG_ERROR, "File didn't return a video clip\n");
        h->func.avs_release_value(res);
        b_fail = true;
        return;
    }
    h->clip = h->func.avs_take_clip(res, h->env);
    h->func.avs_release_value(res);
    FAIL_IF_ERROR(!h->clip, "Avisynth failed to open video clip\n");
    const AVS_VideoInfo* vi = h->func.avs_get_video_info(h->clip);
    FAIL_IF_ERROR(!vi, "Avisynth video info unavailable\n");
    info.width = vi->width;
    info.height = vi->height;
    info.fpsNum = vi->fps_numerator;
    info.fpsDenom = vi->fps_denominator;
    info.frameCount = vi->num_frames;
    info.depth = h->func.avs_bits_per_component(vi);
    h->plane_count = 3;
    if(h->func.avs_is_y8(vi))
    {
        h->plane_count = 1;
        info.csp = X265_CSP_I400;
        general_log(nullptr, "avs+", X265_LOG_INFO, "Video colorspace: YUV400 (Y8)\n");
    }
    else if(h->func.avs_is_420(vi))
    {
        info.csp = X265_CSP_I420;
        general_log(nullptr, "avs+", X265_LOG_INFO, "Video colorspace: YUV420 (YV12)\n");
    }
    else if(h->func.avs_is_422(vi))
    {
        info.csp = X265_CSP_I422;
        general_log(nullptr, "avs+", X265_LOG_INFO, "Video colorspace: YUV422 (YV16)\n");
    }
    else if(h->func.avs_is_444(vi))
    {
        info.csp = X265_CSP_I444;
        general_log(nullptr, "avs+", X265_LOG_INFO, "Video colorspace: YUV444 (YV24)\n");
    }
    else
    {
        FAIL_IF_ERROR(1, "Video colorspace is not supported\n");
    }
    general_log(nullptr, "avs+", X265_LOG_INFO, "Video depth: %d\n", info.depth);
    general_log(nullptr, "avs+", X265_LOG_INFO, "Video resolution: %dx%d\n", info.width, info.height);
    general_log(nullptr, "avs+", X265_LOG_INFO, "Video framerate: %d/%d\n", info.fpsNum, info.fpsDenom);
    general_log(nullptr, "avs+", X265_LOG_INFO, "Video framecount: %d\n", info.frameCount);
    if (info.skipFrames)
        h->next_frame = info.skipFrames;
}

bool AVSInput::readPicture(x265_picture& pic)
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

    AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);
    const char *err = h->func.avs_clip_get_error(h->clip);
    if (err)
    {
        general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\n", err, h->next_frame);
        b_fail = true;
        return false;
    }
    if (!frm)
    {
        general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\n", h->next_frame);
        b_fail = true;
        return false;
    }
    if (!frm->vfb || !frm->vfb->data)
    {
        general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned an invalid frame buffer at frame %d\n", h->next_frame);
        b_fail = true;
        h->func.avs_release_video_frame(frm);
        return false;
    }
    pic.width = _info.width;
    pic.height = _info.height;

    if (frm->pitch <= 0 || frm->height <= 0 || (h->plane_count > 1 && (frm->pitchUV <= 0 || frm->heightUV <= 0)))
    {
        general_log(nullptr, "avs+", X265_LOG_ERROR, "Invalid Avisynth frame geometry at frame %d\n", h->next_frame);
        b_fail = true;
        h->func.avs_release_video_frame(frm);
        return false;
    }

    size_t requiredFrameSize = 0;
    size_t planeBytesY = 0;
    if (!addPlaneBytes(requiredFrameSize, frm->height, frm->pitch, planeBytesY))
    {
        general_log(nullptr, "avs+", X265_LOG_ERROR, "Invalid Avisynth luma geometry at frame %d\n", h->next_frame);
        b_fail = true;
        h->func.avs_release_video_frame(frm);
        return false;
    }
    if (h->plane_count > 1)
    {
        size_t planeBytesU = 0;
        size_t planeBytesV = 0;
        if (!addPlaneBytes(requiredFrameSize, frm->heightUV, frm->pitchUV, planeBytesU) ||
            !addPlaneBytes(requiredFrameSize, frm->heightUV, frm->pitchUV, planeBytesV))
        {
            general_log(nullptr, "avs+", X265_LOG_ERROR, "Invalid Avisynth chroma geometry at frame %d\n", h->next_frame);
            b_fail = true;
            h->func.avs_release_video_frame(frm);
            return false;
        }
    }

    if (!requiredFrameSize)
    {
        general_log(nullptr, "avs+", X265_LOG_ERROR, "Invalid Avisynth frame size at frame %d\n", h->next_frame);
        b_fail = true;
        h->func.avs_release_video_frame(frm);
        return false;
    }

    if (requiredFrameSize > frame_size || frame_buffer == nullptr)
    {
        uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));
        if (!newFrameBuffer)
        {
            general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth input buffer allocation failed at frame %d\n", h->next_frame);
            b_fail = true;
            h->func.avs_release_video_frame(frm);
            return false;
        }
        X265_FREE(frame_buffer);
        frame_buffer = newFrameBuffer;
        frame_size = requiredFrameSize;
    }
    pic.framesize = frame_size;

    uint8_t* ptr = frame_buffer;
    pic.planes[0] = ptr;
    pic.stride[0] = frm->pitch;
    std::memcpy(pic.planes[0], frm->vfb->data + frm->offset, planeBytesY);
    if (h->plane_count > 1)
    {
        size_t planeBytesUV = (size_t)frm->heightUV * (size_t)frm->pitchUV;
        ptr += planeBytesY;
        pic.planes[1] = ptr;
        pic.stride[1] = frm->pitchUV;
        std::memcpy(pic.planes[1], frm->vfb->data + frm->offsetU, planeBytesUV);

        ptr += planeBytesUV;
        pic.planes[2] = ptr;
        pic.stride[2] = frm->pitchUV;
        std::memcpy(pic.planes[2], frm->vfb->data + frm->offsetV, planeBytesUV);
    }
    pic.colorSpace = _info.csp;
    pic.bitDepth = _info.depth;

    h->func.avs_release_video_frame(frm);

    h->next_frame++;
    return true;
}

void AVSInput::release()
{
    X265_FREE(frame_buffer);
    if (h->clip)
        h->func.avs_release_clip(h->clip);
    if (h->env)
        h->func.avs_delete_script_environment(h->env);
    if (h->library)
        avs_close();
}
