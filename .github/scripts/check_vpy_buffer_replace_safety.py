#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET_CPP = Path('source/input/vpy.cpp')
TARGET_H = Path('source/input/vpy.h')
CPP_REQUIRED_SNIPPETS = (
    'if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
    'uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
    'if (!newFrameBuffer)',
    'X265_FREE(frame_buffer);',
    'frame_buffer = newFrameBuffer;',
    'frame_size = requiredFrameSize;',
)
CPP_FORBIDDEN_SNIPPETS = (
    'X265_FREE(frame_buffer);\n        frame_buffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
    'frame_size = 0;',
    'while (!!!vpyCallbackData.reorderMap[nextFrame])',
    'currentFrame = vpyCallbackData.reorderMap[nextFrame];',
    'currentFrame = vpyCallbackData.reorderMap[frame];',
)
HEADER_REQUIRED_SNIPPETS = (
    '#include <mutex>',
    'std::mutex reorderMapMutex;',
    'bool isEof() const { return nextFrame >= vpyCallbackData.totalFrames; }',
)
ASYNC_REQUIRED_SNIPPETS = (
    'vpyCallbackData.vsapi = vsapi = vss_func.getVSApi2(VAPOURSYNTH_API_VERSION);',
    'if(!vsapi)',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth API\\n");',
    'const char* scriptError = vss_func.getError(script);',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "Can\'t evaluate script: %s\\n", scriptError ? scriptError : "unknown VapourSynth script error");',
    'VSCore* core = vss_func.getCore(script);',
    'if(!core)',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth core\\n");',
    'const VSCoreInfo* core_info = vsapi->getCoreInfo(core);',
    'if(!core_info)',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to query VapourSynth core info\\n");',
    'const VSVideoInfo* vi = vsapi->getVideoInfo(node);',
    'if(!vi)',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth video info\\n");',
    'if(!vi->format)',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "VapourSynth returned a null video format\\n");',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "only constant video formats are supported\\n");',
    'frame0 = vsapi->getFrame(nextFrame, node, errbuf, sizeof(errbuf));',
    'if(!frame0)',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "%s occurred while getting frame 0\\n", errbuf);',
    'const VSMap* frameProps0 = vsapi->getFramePropsRO(frame0);',
    'if(!frameProps0)',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth frame properties for frame 0\\n");',
    'const char* pixelType = vi->format->name ? vi->format->name : "unknown";',
    'bool supportedFormat = false;',
    'supportedFormat = true;',
    'if (!supportedFormat)',
    'general_log(nullptr, "vpy", X265_LOG_ERROR, "not supported pixel type: %s\\n", pixelType);',
    'vpyCallbackData.reorderMap[nextFrame] = frame0;',
    '++vpyCallbackData.completedFrames;',
    'std::lock_guard<std::mutex> lock(vpyCallbackData->reorderMapMutex);',
    'vpyCallbackData->reorderMap[n] = f;',
    'if(!f)',
    'vpyCallbackData->isRunning = false;',
    'auto currentFrameItr = vpyCallbackData.reorderMap.find(frame);',
    'auto currentFrameItr = vpyCallbackData.reorderMap.find(nextFrame);',
    'if (currentFrameItr != vpyCallbackData.reorderMap.end())',
    'currentFrame = currentFrameItr->second;',
    'vpyCallbackData.reorderMap.erase(currentFrameItr);',
    'if(!currentFrame)',
    'if (currentFrame == frame0)',
    'frame0 = nullptr;',
    'const int intitalRequestSize = std::min<int>(vpyCallbackData.parallelRequests, vpyCallbackData.totalFrames - requestStart);',
    'if(nextFrame >= vpyCallbackData.totalFrames)',
    'if(frame0 && vsapi)',
    'if(node && vsapi)',
    'node = nullptr;',
    'if (vss_func.freeScript)',
    'vss_func.freeScript(script);',
    'script = nullptr;',
    'if (vss_func.finalize)',
    'vss_func.finalize();',
)


def check_file(path, required, forbidden, label):
    if not path.is_file():
        return [(path.as_posix(), 0, f'missing {label} file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    for snippet in forbidden:
        if snippet in text:
            failures.append((path.as_posix(), 0, f'forbidden {label} regression: {snippet}'))
    for snippet in required:
        if snippet not in text:
            failures.append((path.as_posix(), 0, f'missing {label} guardrail: {snippet}'))
    return failures


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return text
    brace_start = text.find('{', start)
    if brace_start == -1:
        return text[start:]
    depth = 0
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return text[start:]


def check_async_flow(path):
    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []

    load_text = extract_braced_block(text, 'void VPYInput::load_vs()')
    vsapi_get_pos = load_text.find('vpyCallbackData.vsapi = vsapi = vss_func.getVSApi2(VAPOURSYNTH_API_VERSION);')
    vsapi_guard_pos = load_text.find('if(!vsapi)', vsapi_get_pos if vsapi_get_pos != -1 else 0)
    vsapi_log_pos = load_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth API\\n");', vsapi_guard_pos if vsapi_guard_pos != -1 else 0)
    vpy_failed_clear_pos = load_text.find('vpyFailed = false;', vsapi_log_pos if vsapi_log_pos != -1 else 0)
    if -1 in (vsapi_get_pos, vsapi_guard_pos, vsapi_log_pos, vpy_failed_clear_pos) or not (
        vsapi_get_pos < vsapi_guard_pos < vsapi_log_pos < vpy_failed_clear_pos
    ):
        failures.append((path.as_posix(), 0, 'VPYInput::load_vs must guard VapourSynth API discovery before clearing vpyFailed'))

    ctor_text = extract_braced_block(text, 'VPYInput::VPYInput(InputFileInfo& info)')
    evaluate_file_pos = ctor_text.find('if(vss_func.evaluateFile(&script, real_filename, efSetWorkingDir))')
    script_error_pos = ctor_text.find('const char* scriptError = vss_func.getError(script);', evaluate_file_pos if evaluate_file_pos != -1 else 0)
    script_log_pos = ctor_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "Can\'t evaluate script: %s\\n", scriptError ? scriptError : "unknown VapourSynth script error");', script_error_pos if script_error_pos != -1 else 0)
    script_fail_pos = ctor_text.find('vpyFailed = true;', script_log_pos if script_log_pos != -1 else 0)
    script_return_pos = ctor_text.find('return;', script_fail_pos if script_fail_pos != -1 else 0)
    node_pos = ctor_text.find('node = vss_func.getOutput(script, 0);', script_return_pos if script_return_pos != -1 else 0)
    evaluate_fail_text = ctor_text[evaluate_file_pos:node_pos if node_pos != -1 else None]
    if -1 in (evaluate_file_pos, script_error_pos, script_log_pos, script_fail_pos, script_return_pos, node_pos) or not (
        evaluate_file_pos < script_error_pos < script_log_pos < script_fail_pos < script_return_pos < node_pos
    ):
        failures.append((path.as_posix(), 0, 'VPYInput::VPYInput must sanitize evaluateFile error text before logging script-load failures'))
    if 'vss_func.freeScript(script);' in evaluate_fail_text or 'vss_func.finalize();' in evaluate_fail_text:
        failures.append((path.as_posix(), 0, 'VPYInput::VPYInput must leave script cleanup to the destructor after evaluateFile failures'))

    core_get_pos = ctor_text.find('VSCore* core = vss_func.getCore(script);')
    core_guard_pos = ctor_text.find('if(!core)', core_get_pos if core_get_pos != -1 else 0)
    core_log_pos = ctor_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth core\\n");', core_guard_pos if core_guard_pos != -1 else 0)
    core_info_pos = ctor_text.find('const VSCoreInfo* core_info = vsapi->getCoreInfo(core);', core_log_pos if core_log_pos != -1 else 0)
    core_info_guard_pos = ctor_text.find('if(!core_info)', core_info_pos if core_info_pos != -1 else 0)
    core_info_log_pos = ctor_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to query VapourSynth core info\\n");', core_info_guard_pos if core_info_guard_pos != -1 else 0)
    parallel_requests_pos = ctor_text.find('vpyCallbackData.parallelRequests = core_info->numThreads;', core_info_log_pos if core_info_log_pos != -1 else 0)
    video_info_pos = ctor_text.find('const VSVideoInfo* vi = vsapi->getVideoInfo(node);', parallel_requests_pos if parallel_requests_pos != -1 else 0)
    video_info_guard_pos = ctor_text.find('if(!vi)', video_info_pos if video_info_pos != -1 else 0)
    video_info_log_pos = ctor_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth video info\\n");', video_info_guard_pos if video_info_guard_pos != -1 else 0)
    constant_format_pos = ctor_text.find('if(!isConstantFormat(vi))', video_info_log_pos if video_info_log_pos != -1 else 0)
    constant_format_log_pos = ctor_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "only constant video formats are supported\\n");', constant_format_pos if constant_format_pos != -1 else 0)
    constant_format_fail_pos = ctor_text.find('vpyFailed = true;', constant_format_log_pos if constant_format_log_pos != -1 else 0)
    constant_format_return_pos = ctor_text.find('return;', constant_format_fail_pos if constant_format_fail_pos != -1 else 0)
    format_guard_pos = ctor_text.find('if(!vi->format)', constant_format_return_pos if constant_format_return_pos != -1 else 0)
    format_log_pos = ctor_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "VapourSynth returned a null video format\\n");', format_guard_pos if format_guard_pos != -1 else 0)
    frame0_pos = ctor_text.find('frame0 = vsapi->getFrame(nextFrame, node, errbuf, sizeof(errbuf));', format_log_pos if format_log_pos != -1 else 0)
    frame0_guard_pos = ctor_text.find('if(!frame0)', frame0_pos if frame0_pos != -1 else 0)
    frame0_log_pos = ctor_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "%s occurred while getting frame 0\\n", errbuf);', frame0_guard_pos if frame0_guard_pos != -1 else 0)
    frame_props_pos = ctor_text.find('const VSMap* frameProps0 = vsapi->getFramePropsRO(frame0);', frame0_log_pos if frame0_log_pos != -1 else 0)
    frame_props_guard_pos = ctor_text.find('if(!frameProps0)', frame_props_pos if frame_props_pos != -1 else 0)
    frame_props_log_pos = ctor_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth frame properties for frame 0\\n");', frame_props_guard_pos if frame_props_guard_pos != -1 else 0)
    sar_width_pos = ctor_text.find('info.sarWidth = vsapi->propNumElements(frameProps0, "_SARNum") > 0 ? vsapi->propGetInt(frameProps0, "_SARNum", 0, nullptr) : 0;', frame_props_log_pos if frame_props_log_pos != -1 else 0)
    depth_pos = ctor_text.find('info.depth = vi->format->bitsPerSample;', sar_width_pos if sar_width_pos != -1 else 0)
    pixel_type_pos = ctor_text.find('const char* pixelType = vi->format->name ? vi->format->name : "unknown";', depth_pos if depth_pos != -1 else 0)
    format_support_pos = ctor_text.find('bool supportedFormat = false;', pixel_type_pos if pixel_type_pos != -1 else 0)
    unsupported_guard_pos = ctor_text.find('if (!supportedFormat)', format_support_pos if format_support_pos != -1 else 0)
    unsupported_log_pos = ctor_text.find('general_log(nullptr, "vpy", X265_LOG_ERROR, "not supported pixel type: %s\\n", pixelType);', unsupported_guard_pos if unsupported_guard_pos != -1 else 0)
    frame_store_pos = ctor_text.find('vpyCallbackData.reorderMap[nextFrame] = frame0;', unsupported_log_pos if unsupported_log_pos != -1 else 0)
    frame_complete_pos = ctor_text.find('++vpyCallbackData.completedFrames;', frame_store_pos if frame_store_pos != -1 else 0)
    info_store_pos = ctor_text.find('_info = info;', frame_complete_pos if frame_complete_pos != -1 else 0)
    if -1 in (
        core_get_pos,
        core_guard_pos,
        core_log_pos,
        core_info_pos,
        core_info_guard_pos,
        core_info_log_pos,
        parallel_requests_pos,
        video_info_pos,
        video_info_guard_pos,
        video_info_log_pos,
        constant_format_pos,
        constant_format_log_pos,
        constant_format_fail_pos,
        constant_format_return_pos,
        format_guard_pos,
        format_log_pos,
        frame0_pos,
        frame0_guard_pos,
        frame0_log_pos,
        frame_props_pos,
        frame_props_guard_pos,
        frame_props_log_pos,
        sar_width_pos,
        depth_pos,
        pixel_type_pos,
        format_support_pos,
        unsupported_guard_pos,
        unsupported_log_pos,
        frame_store_pos,
        frame_complete_pos,
        info_store_pos,
    ) or not (
        core_get_pos < core_guard_pos < core_log_pos < core_info_pos < core_info_guard_pos < core_info_log_pos <
        parallel_requests_pos < video_info_pos < video_info_guard_pos < video_info_log_pos < constant_format_pos <
        constant_format_log_pos < constant_format_fail_pos < constant_format_return_pos < format_guard_pos < format_log_pos < frame0_pos < frame0_guard_pos < frame0_log_pos < frame_props_pos <
        frame_props_guard_pos < frame_props_log_pos < sar_width_pos < depth_pos < pixel_type_pos < format_support_pos <
        unsupported_guard_pos < unsupported_log_pos < frame_store_pos <
        frame_complete_pos < info_store_pos
    ):
        failures.append((path.as_posix(), 0, 'VPYInput::VPYInput must fail fast on non-constant VapourSynth formats before bootstrapping frame 0 state'))

    callback_text = extract_braced_block(text, 'static void frameDoneCallback(')
    callback_lock_pos = callback_text.find('std::lock_guard<std::mutex> lock(vpyCallbackData->reorderMapMutex);')
    callback_store_pos = callback_text.find('vpyCallbackData->reorderMap[n] = f;', callback_lock_pos if callback_lock_pos != -1 else 0)
    callback_complete_pos = callback_text.find('++vpyCallbackData->completedFrames;', callback_store_pos if callback_store_pos != -1 else 0)
    callback_fail_guard_pos = callback_text.find('if(!f)', callback_complete_pos if callback_complete_pos != -1 else 0)
    callback_stop_pos = callback_text.find('vpyCallbackData->isRunning = false;', callback_fail_guard_pos if callback_fail_guard_pos != -1 else 0)
    callback_return_pos = callback_text.find('return;', callback_stop_pos if callback_stop_pos != -1 else 0)
    if -1 in (
        callback_lock_pos,
        callback_store_pos,
        callback_complete_pos,
        callback_fail_guard_pos,
        callback_stop_pos,
        callback_return_pos,
    ) or not (
        callback_lock_pos < callback_store_pos < callback_complete_pos <
        callback_fail_guard_pos < callback_stop_pos < callback_return_pos
    ):
        failures.append((path.as_posix(), 0, 'frameDoneCallback must publish async frame completion before handling null-frame failure'))

    dtor_text = extract_braced_block(text, 'VPYInput::~VPYInput()')
    dtor_frame_pos = dtor_text.find('if(frame0 && vsapi)')
    dtor_frame_free_pos = dtor_text.find('vsapi->freeFrame(frame0);', dtor_frame_pos if dtor_frame_pos != -1 else 0)
    dtor_frame_clear_pos = dtor_text.find('frame0 = nullptr;', dtor_frame_free_pos if dtor_frame_free_pos != -1 else 0)
    dtor_node_pos = dtor_text.find('if(node && vsapi)', dtor_frame_clear_pos if dtor_frame_clear_pos != -1 else 0)
    dtor_node_free_pos = dtor_text.find('vsapi->freeNode(node);', dtor_node_pos if dtor_node_pos != -1 else 0)
    dtor_node_clear_pos = dtor_text.find('node = nullptr;', dtor_node_free_pos if dtor_node_free_pos != -1 else 0)
    dtor_script_guard_pos = dtor_text.find('if (vss_func.freeScript)', dtor_node_clear_pos if dtor_node_clear_pos != -1 else 0)
    dtor_script_free_pos = dtor_text.find('vss_func.freeScript(script);', dtor_script_guard_pos if dtor_script_guard_pos != -1 else 0)
    dtor_script_clear_pos = dtor_text.find('script = nullptr;', dtor_script_free_pos if dtor_script_free_pos != -1 else 0)
    dtor_finalize_guard_pos = dtor_text.find('if (vss_func.finalize)', dtor_script_clear_pos if dtor_script_clear_pos != -1 else 0)
    dtor_finalize_pos = dtor_text.find('vss_func.finalize();', dtor_finalize_guard_pos if dtor_finalize_guard_pos != -1 else 0)
    if -1 in (
        dtor_frame_pos,
        dtor_frame_free_pos,
        dtor_frame_clear_pos,
        dtor_node_pos,
        dtor_node_free_pos,
        dtor_node_clear_pos,
        dtor_script_guard_pos,
        dtor_script_free_pos,
        dtor_script_clear_pos,
        dtor_finalize_guard_pos,
        dtor_finalize_pos,
    ) or not (
        dtor_frame_pos < dtor_frame_free_pos < dtor_frame_clear_pos < dtor_node_pos < dtor_node_free_pos <
        dtor_node_clear_pos < dtor_script_guard_pos < dtor_script_free_pos < dtor_script_clear_pos <
        dtor_finalize_guard_pos < dtor_finalize_pos
    ):
        failures.append((path.as_posix(), 0, 'VPYInput::~VPYInput must guard partially initialized VapourSynth state before releasing it'))

    release_text = extract_braced_block(text, 'void VPYInput::release()')
    release_lock_pos = release_text.find('std::lock_guard<std::mutex> lock(vpyCallbackData.reorderMapMutex);')
    release_find_pos = release_text.find('auto currentFrameItr = vpyCallbackData.reorderMap.find(frame);', release_lock_pos if release_lock_pos != -1 else 0)
    release_erase_pos = release_text.find('vpyCallbackData.reorderMap.erase(currentFrameItr);', release_find_pos if release_find_pos != -1 else 0)
    release_frame0_pos = release_text.find('if (currentFrame == frame0)', release_erase_pos if release_erase_pos != -1 else 0)
    release_free_pos = release_text.find('vsapi->freeFrame(currentFrame);', release_frame0_pos if release_frame0_pos != -1 else 0)
    if -1 in (
        release_lock_pos,
        release_find_pos,
        release_erase_pos,
        release_frame0_pos,
        release_free_pos,
    ) or not (
        release_lock_pos < release_find_pos < release_erase_pos < release_frame0_pos < release_free_pos
    ):
        failures.append((path.as_posix(), 0, 'VPYInput::release must drain reorderMap under lock and clear frame0 before freeing it'))

    read_text = extract_braced_block(text, 'bool VPYInput::readPicture(x265_picture& pic)')
    wait_pos = read_text.find('while (true)')
    read_lock_pos = read_text.find('std::lock_guard<std::mutex> lock(vpyCallbackData.reorderMapMutex);', wait_pos if wait_pos != -1 else 0)
    next_find_pos = read_text.find('auto currentFrameItr = vpyCallbackData.reorderMap.find(nextFrame);', read_lock_pos if read_lock_pos != -1 else 0)
    current_assign_pos = read_text.find('currentFrame = currentFrameItr->second;', next_find_pos if next_find_pos != -1 else 0)
    next_erase_pos = read_text.find('vpyCallbackData.reorderMap.erase(currentFrameItr);', current_assign_pos if current_assign_pos != -1 else 0)
    output_pos = read_text.find('++vpyCallbackData.outputFrames;', next_erase_pos if next_erase_pos != -1 else 0)
    null_guard_pos = read_text.find('if(!currentFrame)', output_pos if output_pos != -1 else 0)
    null_fail_pos = read_text.find('vpyFailed = true;', null_guard_pos if null_guard_pos != -1 else 0)
    null_stop_pos = read_text.find('vpyCallbackData.isRunning = false;', null_fail_pos if null_fail_pos != -1 else 0)
    null_return_pos = read_text.find('return false;', null_stop_pos if null_stop_pos != -1 else 0)
    final_frame0_pos = read_text.rfind('if (currentFrame == frame0)')
    final_free_pos = read_text.rfind('vsapi->freeFrame(currentFrame);')
    if -1 in (
        wait_pos,
        read_lock_pos,
        next_find_pos,
        current_assign_pos,
        next_erase_pos,
        output_pos,
        null_guard_pos,
        null_fail_pos,
        null_stop_pos,
        null_return_pos,
        final_frame0_pos,
        final_free_pos,
    ) or not (
        wait_pos < read_lock_pos < next_find_pos < current_assign_pos < next_erase_pos < output_pos <
        null_guard_pos < null_fail_pos < null_stop_pos < null_return_pos < final_frame0_pos < final_free_pos
    ):
        failures.append((path.as_posix(), 0, 'VPYInput::readPicture must wait on reorderMap entries, fail fast on null frames, and clear frame0 before freeing'))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    failures.extend(check_file(repo_root / TARGET_CPP, CPP_REQUIRED_SNIPPETS, CPP_FORBIDDEN_SNIPPETS, 'VPY buffer replace safety'))
    failures.extend(check_file(repo_root / TARGET_H, HEADER_REQUIRED_SNIPPETS, (), 'VPY async frame header'))

    cpp_path = repo_root / TARGET_CPP
    if cpp_path.is_file():
        failures.extend(check_file(cpp_path, ASYNC_REQUIRED_SNIPPETS, (), 'VPY async frame'))
        failures.extend(check_async_flow(cpp_path))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VPY input buffer replace safety guardrails')
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

    print('VPY buffer replace safety validated')


if __name__ == '__main__':
    main()
