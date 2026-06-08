#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/input/avs.cpp')
REQUIRED_SNIPPETS = (
    'h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);',
    'if (!h->env)',
    'general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");',
    'avs_close();',
    'const char *version = avs_as_string(ver);',
    'general_log(nullptr, "avs+", X265_LOG_INFO, "%s\\n", version ? version : "unknown");',
    'h->func.avs_release_value(ver);',
    'if (avs_is_error(res))',
    'const char *errorText = avs_as_string(res);',
    'general_log(nullptr, "avs+", X265_LOG_ERROR, "Error loading file: %s\\n", errorText ? errorText : "unknown Avisynth error");',
    'if (!avs_is_clip(res))',
    'general_log(nullptr, "avs+", X265_LOG_ERROR, "File didn\'t return a video clip\\n");',
    'h->clip = h->func.avs_take_clip(res, h->env);',
    'h->func.avs_release_value(res);',
    'FAIL_IF_ERROR(!h->clip, "Avisynth failed to open video clip\\n");',
    'const AVS_VideoInfo* vi = h->func.avs_get_video_info(h->clip);',
    'FAIL_IF_ERROR(!vi, "Avisynth video info unavailable\\n");',
    'AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);',
    'const char *err = h->func.avs_clip_get_error(h->clip);',
    'if (err)',
    'general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);',
    'if (!frm)',
    'general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\\n", h->next_frame);',
    'if (!frm->vfb || !frm->vfb->data)',
    'general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned an invalid frame buffer at frame %d\\n", h->next_frame);',
    'b_fail = true;',
    'return false;',
    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
    'if (!newFrameBuffer)',
    'X265_FREE(frame_buffer);',
    'frame_buffer = newFrameBuffer;',
    'frame_size = requiredFrameSize;',
)
FORBIDDEN_SNIPPETS = (
    'X265_FREE(frame_buffer);\n        frame_buffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
    'frame_size = 0;',
    'FAIL_IF_ERROR(avs_is_error(res), "Error loading file: %s\\n", avs_as_string(res));',
    'FAIL_IF_ERROR(!avs_is_clip(res), "File didn\'t return a video clip\\n");',
)


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    header_path = repo_root / Path('source/input/avs.h')
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]
    if not header_path.is_file():
        return [('source/input/avs.h', 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    header_text = header_path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden AVS buffer replace regression: {snippet}'))
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing AVS buffer replace guardrail: {snippet}'))
    if 'if (!h->library || !h->env)' not in header_text:
        failures.append(('source/input/avs.h', 0, 'missing AVS buffer replace guardrail: if (!h->library || !h->env)'))

    env_create_pos = text.find('h->env = h->func.avs_create_script_environment(AVS_INTERFACE_26);')
    env_guard_pos = text.find('if (!h->env)', env_create_pos if env_create_pos != -1 else 0)
    env_log_pos = text.find('general_log(nullptr, "avs+", X265_LOG_ERROR, "failed to create AviSynth+ script environment\\n");', env_guard_pos if env_guard_pos != -1 else 0)
    env_close_pos = text.find('avs_close();', env_log_pos if env_log_pos != -1 else 0)
    env_return_pos = text.find('return;', env_close_pos if env_close_pos != -1 else 0)
    if -1 in (env_create_pos, env_guard_pos, env_log_pos, env_close_pos, env_return_pos) or not (
        env_create_pos < env_guard_pos < env_log_pos < env_close_pos < env_return_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'AVSInput::load_avs must close the library and return when script environment creation fails'))

    version_pos = text.find('const char *version = avs_as_string(ver);')
    version_log_pos = text.find('general_log(nullptr, "avs+", X265_LOG_INFO, "%s\\n", version ? version : "unknown");', version_pos if version_pos != -1 else 0)
    version_release_pos = text.find('h->func.avs_release_value(ver);', version_log_pos if version_log_pos != -1 else 0)
    clip_take_pos = text.find('h->clip = h->func.avs_take_clip(res, h->env);', version_release_pos if version_release_pos != -1 else 0)
    if -1 in (version_pos, version_log_pos, version_release_pos, clip_take_pos) or not (
        version_pos < version_log_pos < version_release_pos < clip_take_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'AVSInput::info_avs must log the Avisynth version before releasing the VersionString value'))

    error_guard_pos = text.find('if (avs_is_error(res))')
    error_text_pos = text.find('const char *errorText = avs_as_string(res);', error_guard_pos if error_guard_pos != -1 else 0)
    error_log_pos = text.find('general_log(nullptr, "avs+", X265_LOG_ERROR, "Error loading file: %s\\n", errorText ? errorText : "unknown Avisynth error");', error_text_pos if error_text_pos != -1 else 0)
    error_release_pos = text.find('h->func.avs_release_value(res);', error_log_pos if error_log_pos != -1 else 0)
    clip_type_guard_pos = text.find('if (!avs_is_clip(res))', error_release_pos if error_release_pos != -1 else 0)
    clip_type_log_pos = text.find('general_log(nullptr, "avs+", X265_LOG_ERROR, "File didn\'t return a video clip\\n");', clip_type_guard_pos if clip_type_guard_pos != -1 else 0)
    clip_type_release_pos = text.find('h->func.avs_release_value(res);', clip_type_log_pos if clip_type_log_pos != -1 else 0)
    clip_take_pos = text.find('h->clip = h->func.avs_take_clip(res, h->env);', clip_type_release_pos if clip_type_release_pos != -1 else 0)
    clip_release_pos = text.find('h->func.avs_release_value(res);', clip_take_pos if clip_take_pos != -1 else 0)
    clip_guard_pos = text.find('FAIL_IF_ERROR(!h->clip, "Avisynth failed to open video clip\\n");', clip_take_pos if clip_take_pos != -1 else 0)
    video_info_pos = text.find('const AVS_VideoInfo* vi = h->func.avs_get_video_info(h->clip);', clip_guard_pos if clip_guard_pos != -1 else 0)
    video_info_guard_pos = text.find('FAIL_IF_ERROR(!vi, "Avisynth video info unavailable\\n");', video_info_pos if video_info_pos != -1 else 0)
    info_width_pos = text.find('info.width = vi->width;', video_info_guard_pos if video_info_guard_pos != -1 else 0)
    if -1 in (error_guard_pos, error_text_pos, error_log_pos, error_release_pos, clip_type_guard_pos, clip_type_log_pos, clip_type_release_pos, clip_take_pos, clip_release_pos, clip_guard_pos, video_info_pos, video_info_guard_pos, info_width_pos) or not (
        error_guard_pos < error_text_pos < error_log_pos < error_release_pos < clip_type_guard_pos < clip_type_log_pos < clip_type_release_pos < clip_take_pos < clip_release_pos < clip_guard_pos < video_info_pos < video_info_guard_pos < info_width_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'AVSInput::openfile must release Avisynth invoke results across error, non-clip, and clip-acquisition paths before dereferencing vi'))

    frame_pos = text.find('AVS_VideoFrame *frm = h->func.avs_get_frame(h->clip, h->next_frame);')
    err_pos = text.find('const char *err = h->func.avs_clip_get_error(h->clip);', frame_pos if frame_pos != -1 else 0)
    err_guard_pos = text.find('if (err)', err_pos if err_pos != -1 else 0)
    err_log_pos = text.find('general_log(nullptr, "avs+", X265_LOG_ERROR, "%s occurred while reading frame %d\\n", err, h->next_frame);', err_guard_pos if err_guard_pos != -1 else 0)
    null_guard_pos = text.find('if (!frm)', err_log_pos if err_log_pos != -1 else 0)
    null_log_pos = text.find('general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned a null frame at frame %d\\n", h->next_frame);', null_guard_pos if null_guard_pos != -1 else 0)
    buffer_guard_pos = text.find('if (!frm->vfb || !frm->vfb->data)', null_log_pos if null_log_pos != -1 else 0)
    buffer_log_pos = text.find('general_log(nullptr, "avs+", X265_LOG_ERROR, "Avisynth returned an invalid frame buffer at frame %d\\n", h->next_frame);', buffer_guard_pos if buffer_guard_pos != -1 else 0)
    width_pos = text.find('pic.width = _info.width;', buffer_log_pos if buffer_log_pos != -1 else 0)
    if -1 in (frame_pos, err_pos, err_guard_pos, err_log_pos, null_guard_pos, null_log_pos, buffer_guard_pos, buffer_log_pos, width_pos) or not (
        frame_pos < err_pos < err_guard_pos < err_log_pos < null_guard_pos < null_log_pos < buffer_guard_pos < buffer_log_pos < width_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'AVSInput::readPicture must fail on null or invalid Avisynth frame buffers before dereferencing frm'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check AVS input buffer replace safety guardrails')
    parser.add_argument('repo_root', nargs='?', default='.')
    args = parser.parse_args()

    failures = check_repo(args.repo_root)
    if failures:
        for path, line, message in failures:
            if line:
                print(f'::error file={path},line={line}::{message}')
            else:
                print(f'::error file={path}::{message}')
        raise SystemExit(1)

    print('AVS buffer replace safety validated')


if __name__ == '__main__':
    main()
