#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_avs_buffer_replace_safety.py')

# Coverage probes used by the scan for AVS buffer replacement guardrails.
NORMALIZED_PROBES = (
    'missing AVS buffer replace guardrail: if (!h->library || !h->env)',
    'AVSInput::readPicture must fail on null or invalid Avisynth frame buffers before dereferencing frm',
    'forbidden AVS buffer replace regression: ',
)


def write_targets(root, contents):
    for relative, text in contents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def run_checker(repo_root):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def expect_pass(result):
    if result.returncode != 0:
        raise AssertionError(result.stdout)


def expect_fail(result, expected):
    if result.returncode == 0:
        raise AssertionError(f'expected failure containing {expected!r}')
    if expected not in result.stdout:
        raise AssertionError(result.stdout)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/avs.cpp': '\n'.join((
                    'h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);',
                    'if (!h->env)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");',
                    'avs_close();',
                    'return;',
                    'const char *version = avs_as_string(ver);',
                    'general_log(nullptr, "avs+", X265_LOG_INFO, "%s\\n", version ? version : "unknown");',
                    'h->func.avs_release_value(ver);',
                    'if (avs_is_error(res))',
                    'const char *errorText = avs_as_string(res);',
                    'general_log(nullptr, "avs+", X265_LOG_ERROR, "Error loading file: %s\\n", errorText ? errorText : "unknown Avisynth error");',
                    'h->func.avs_release_value(res);',
                    'if (!avs_is_clip(res))',
                    'general_log(nullptr, "avs+", X265_LOG_ERROR, "File didn\'t return a video clip\\n");',
                    'h->func.avs_release_value(res);',
                    'h->clip = h->func.avs_take_clip(res, h->env);',
                    'h->func.avs_release_value(res);',
                    'FAIL_IF_ERROR(!h->clip, "Avisynth failed to open video clip\\n");',
                    'const AVS_VideoInfo* vi = h->func.avs_get_video_info(h->clip);',
                    'FAIL_IF_ERROR(!vi, "Avisynth video info unavailable\\n");',
                    'info.width = vi->width;',
                    'AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);',
                    'const char *err = h->func.avs_clip_get_error(h->clip);',
                    'if (err)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);',
                    'if (!frm)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\\n", h->next_frame);',
                    'if (!frm->vfb || !frm->vfb->data)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned an invalid frame buffer at frame %d\\n", h->next_frame);',
                    'b_fail = true;',
                    'return false;',
                    'pic.width = _info.width;',
                    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
                    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
                    'if (!newFrameBuffer)',
                    'X265_FREE(frame_buffer);',
                    'frame_buffer = newFrameBuffer;',
                    'frame_size = requiredFrameSize;',
                )) + '\n',
                'source/input/avs.h': 'if (!h->library || !h->env)\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/avs.cpp': 'X265_FREE(frame_buffer);\n        frame_buffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));\n',
                'source/input/avs.h': 'if (!h->library || !h->env)\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden AVS buffer replace regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/avs.cpp': '\n'.join((
                    'h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);',
                    'if (!h->env)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");',
                    'avs_close();',
                    'return;',
                    'AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);',
                    'const char *err = h->func.avs_clip_get_error(h->clip);',
                    'if (err)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);',
                    'pic.width = _info.width;',
                    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
                    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
                    'if (!newFrameBuffer)',
                    'X265_FREE(frame_buffer);',
                    'frame_buffer = newFrameBuffer;',
                    'frame_size = requiredFrameSize;',
                )) + '\n',
                'source/input/avs.h': 'if (!h->library || !h->env)\n',
            },
        )
        expect_fail(run_checker(root), 'missing AVS buffer replace guardrail: if (!frm)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/avs.cpp': '\n'.join((
                    'h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);',
                    'if (!h->env)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");',
                    'return;',
                    'AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);',
                    'const char *err = h->func.avs_clip_get_error(h->clip);',
                    'if (err)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);',
                    'if (!frm)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\\n", h->next_frame);',
                    'b_fail = true;',
                    'return false;',
                    'pic.width = _info.width;',
                    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
                    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
                    'if (!newFrameBuffer)',
                    'X265_FREE(frame_buffer);',
                    'frame_buffer = newFrameBuffer;',
                    'frame_size = requiredFrameSize;',
                )) + '\n',
                'source/input/avs.h': 'if (!h->library || !h->env)\n',
            },
        )
        expect_fail(run_checker(root), 'AVSInput::load_avs must close the library and return when script environment creation fails')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/avs.cpp': '\n'.join((
                    'h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);',
                    'if (!h->env)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");',
                    'avs_close();',
                    'return;',
                    'const char *version = avs_as_string(ver);',
                    'h->func.avs_release_value(ver);',
                    'general_log(nullptr, "avs+", X265_LOG_INFO, "%s\\n", version ? version : "unknown");',
                    'h->clip = h->func.avs_take_clip(res, h->env);',
                    'FAIL_IF_ERROR(!h->clip, "Avisynth failed to open video clip\\n");',
                    'const AVS_VideoInfo* vi = h->func.avs_get_video_info(h->clip);',
                    'FAIL_IF_ERROR(!vi, "Avisynth video info unavailable\\n");',
                    'info.width = vi->width;',
                    'AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);',
                    'const char *err = h->func.avs_clip_get_error(h->clip);',
                    'if (err)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);',
                    'if (!frm)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\\n", h->next_frame);',
                    'if (!frm->vfb || !frm->vfb->data)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned an invalid frame buffer at frame %d\\n", h->next_frame);',
                    'b_fail = true;',
                    'return false;',
                    'pic.width = _info.width;',
                    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
                    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
                    'if (!newFrameBuffer)',
                    'X265_FREE(frame_buffer);',
                    'frame_buffer = newFrameBuffer;',
                    'frame_size = requiredFrameSize;',
                )) + '\n',
                'source/input/avs.h': 'if (!h->library || !h->env)\n',
            },
        )
        expect_fail(run_checker(root), 'AVSInput::info_avs must log the Avisynth version before releasing the VersionString value')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/avs.cpp': '\n'.join((
                    'h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);',
                    'if (!h->env)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");',
                    'avs_close();',
                    'return;',
                    'const char *version = avs_as_string(ver);',
                    'general_log(nullptr, "avs+", X265_LOG_INFO, "%s\\n", version ? version : "unknown");',
                    'h->func.avs_release_value(ver);',
                    'if (avs_is_error(res))',
                    'const char *errorText = avs_as_string(res);',
                    'general_log(nullptr, "avs+", X265_LOG_ERROR, "Error loading file: %s\\n", errorText ? errorText : "unknown Avisynth error");',
                    'if (!avs_is_clip(res))',
                    'general_log(nullptr, "avs+", X265_LOG_ERROR, "File didn\'t return a video clip\\n");',
                    'h->func.avs_release_value(res);',
                    'h->clip = h->func.avs_take_clip(res, h->env);',
                    'h->func.avs_release_value(res);',
                    'FAIL_IF_ERROR(!h->clip, "Avisynth failed to open video clip\\n");',
                    'const AVS_VideoInfo* vi = h->func.avs_get_video_info(h->clip);',
                    'FAIL_IF_ERROR(!vi, "Avisynth video info unavailable\\n");',
                    'info.width = vi->width;',
                    'AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);',
                    'const char *err = h->func.avs_clip_get_error(h->clip);',
                    'if (err)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);',
                    'if (!frm)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\\n", h->next_frame);',
                    'if (!frm->vfb || !frm->vfb->data)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned an invalid frame buffer at frame %d\\n", h->next_frame);',
                    'b_fail = true;',
                    'return false;',
                    'pic.width = _info.width;',
                    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
                    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
                    'if (!newFrameBuffer)',
                    'X265_FREE(frame_buffer);',
                    'frame_buffer = newFrameBuffer;',
                    'frame_size = requiredFrameSize;',
                )) + '\n',
                'source/input/avs.h': 'if (!h->library || !h->env)\n',
            },
        )
        expect_fail(run_checker(root), 'AVSInput::openfile must release Avisynth invoke results across error, non-clip, and clip-acquisition paths before dereferencing vi')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/avs.cpp': '\n'.join((
                    'h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);',
                    'if (!h->env)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");',
                    'avs_close();',
                    'return;',
                    'h->clip = h->func.avs_take_clip(res, h->env);',
                    'FAIL_IF_ERROR(!h->clip, "Avisynth failed to open video clip\\n");',
                    'const AVS_VideoInfo* vi = h->func.avs_get_video_info(h->clip);',
                    'FAIL_IF_ERROR(!vi, "Avisynth video info unavailable\\n");',
                    'info.width = vi->width;',
                    'AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);',
                    'const char *err = h->func.avs_clip_get_error(h->clip);',
                    'if (err)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);',
                    'if (!frm)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\\n", h->next_frame);',
                    'pic.width = _info.width;',
                    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
                    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
                    'if (!newFrameBuffer)',
                    'X265_FREE(frame_buffer);',
                    'frame_buffer = newFrameBuffer;',
                    'frame_size = requiredFrameSize;',
                )) + '\n',
                'source/input/avs.h': 'if (!h->library || !h->env)\n',
            },
        )
        expect_fail(run_checker(root), 'missing AVS buffer replace guardrail: if (!frm->vfb || !frm->vfb->data)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/avs.cpp': '\n'.join((
                    'h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);',
                    'if (!h->env)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");',
                    'avs_close();',
                    'return;',
                    'h->clip = h->func.avs_take_clip(res, h->env);',
                    'const AVS_VideoInfo* vi = h->func.avs_get_video_info(h->clip);',
                    'FAIL_IF_ERROR(!vi, "Avisynth video info unavailable\\n");',
                    'info.width = vi->width;',
                    'AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);',
                    'const char *err = h->func.avs_clip_get_error(h->clip);',
                    'if (err)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);',
                    'if (!frm)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\\n", h->next_frame);',
                    'b_fail = true;',
                    'return false;',
                    'pic.width = _info.width;',
                    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
                    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
                    'if (!newFrameBuffer)',
                    'X265_FREE(frame_buffer);',
                    'frame_buffer = newFrameBuffer;',
                    'frame_size = requiredFrameSize;',
                )) + '\n',
                'source/input/avs.h': 'if (!h->library || !h->env)\n',
            },
        )
        expect_fail(run_checker(root), 'missing AVS buffer replace guardrail: FAIL_IF_ERROR(!h->clip, "Avisynth failed to open video clip\\n");')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/avs.cpp': '\n'.join((
                    'h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);',
                    'if (!h->env)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");',
                    'avs_close();',
                    'return;',
                    'h->clip = h->func.avs_take_clip(res, h->env);',
                    'FAIL_IF_ERROR(!h->clip, "Avisynth failed to open video clip\\n");',
                    'const AVS_VideoInfo* vi = h->func.avs_get_video_info(h->clip);',
                    'info.width = vi->width;',
                    'AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);',
                    'const char *err = h->func.avs_clip_get_error(h->clip);',
                    'if (err)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);',
                    'if (!frm)',
                    '    general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\\n", h->next_frame);',
                    'b_fail = true;',
                    'return false;',
                    'pic.width = _info.width;',
                    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
                    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
                    'if (!newFrameBuffer)',
                    'X265_FREE(frame_buffer);',
                    'frame_buffer = newFrameBuffer;',
                    'frame_size = requiredFrameSize;',
                )) + '\n',
                'source/input/avs.h': 'if (!h->library || !h->env)\n',
            },
        )
        expect_fail(run_checker(root), 'missing AVS buffer replace guardrail: FAIL_IF_ERROR(!vi, "Avisynth video info unavailable\\n");')

    print('AVS buffer replace safety tests passed')


if __name__ == '__main__':
    main()
