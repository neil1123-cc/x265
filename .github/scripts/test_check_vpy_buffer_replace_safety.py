#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vpy_buffer_replace_safety.py')

# Coverage probes used by the scan for VPY buffer replacement guardrails.
NORMALIZED_PROBES = (
    'VPYInput::load_vs must guard VapourSynth API discovery before clearing vpyFailed',
    'VPYInput::VPYInput must sanitize evaluateFile error text before logging script-load failures',
    'frameDoneCallback must publish async frame completion before handling null-frame failure',
    'VPYInput::release must drain reorderMap under lock and clear frame0 before freeing it',
    'VPYInput::readPicture must wait on reorderMap entries, fail fast on null frames, and clear frame0 before freeing',
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


def valid_cpp_text():
    return '\n'.join((
        'void VPYInput::load_vs()',
        '{',
        '    vpyCallbackData.vsapi = vsapi = vss_func.getVSApi2(VAPOURSYNTH_API_VERSION);',
        '    if(!vsapi)',
        '    {',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth API\\n");',
        '        return;',
        '    }',
        '    vpyFailed = false;',
        '}',
        'VPYInput::VPYInput(InputFileInfo& info)',
        '{',
        '    if(vss_func.evaluateFile(&script, real_filename, efSetWorkingDir))',
        '    {',
        '        const char* scriptError = vss_func.getError(script);',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "Can\'t evaluate script: %s\\n", scriptError ? scriptError : "unknown VapourSynth script error");',
        '        vpyFailed = true;',
        '        return;',
        '    }',
        '    node = vss_func.getOutput(script, 0);',
        '    VSCore* core = vss_func.getCore(script);',
        '    if(!core)',
        '    {',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth core\\n");',
        '        vpyFailed = true;',
        '        return;',
        '    }',
        '    const VSCoreInfo* core_info = vsapi->getCoreInfo(core);',
        '    if(!core_info)',
        '    {',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to query VapourSynth core info\\n");',
        '        vpyFailed = true;',
        '        return;',
        '    }',
        '    vpyCallbackData.parallelRequests = core_info->numThreads;',
        '    const VSVideoInfo* vi = vsapi->getVideoInfo(node);',
        '    if(!vi)',
        '    {',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth video info\\n");',
        '        vpyFailed = true;',
        '        return;',
        '    }',
        '    if(!isConstantFormat(vi))',
        '    {',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "only constant video formats are supported\\n");',
        '        vpyFailed = true;',
        '        return;',
        '    }',
        '    if(!vi->format)',
        '    {',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "VapourSynth returned a null video format\\n");',
        '        vpyFailed = true;',
        '        return;',
        '    }',
        '    frame0 = vsapi->getFrame(nextFrame, node, errbuf, sizeof(errbuf));',
        '    if(!frame0)',
        '    {',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "%s occurred while getting frame 0\\n", errbuf);',
        '        vpyFailed = true;',
        '        return;',
        '    }',
        '    const VSMap* frameProps0 = vsapi->getFramePropsRO(frame0);',
        '    if(!frameProps0)',
        '    {',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth frame properties for frame 0\\n");',
        '        vpyFailed = true;',
        '        return;',
        '    }',
        '    info.sarWidth = vsapi->propNumElements(frameProps0, "_SARNum") > 0 ? vsapi->propGetInt(frameProps0, "_SARNum", 0, nullptr) : 0;',
        '    info.depth = vi->format->bitsPerSample;',
        '    const char* pixelType = vi->format->name ? vi->format->name : "unknown";',
        '    bool supportedFormat = false;',
        '    supportedFormat = true;',
        '    if (!supportedFormat)',
        '    {',
        '        general_log(nullptr, "vpy", X265_LOG_ERROR, "not supported pixel type: %s\\n", pixelType);',
        '        vpyFailed = true;',
        '        return;',
        '    }',
        '    vpyCallbackData.reorderMap[nextFrame] = frame0;',
        '    ++vpyCallbackData.completedFrames;',
        '    _info = info;',
        '}',
        'static void frameDoneCallback(void* userData, const VSFrameRef* f, const int n, VSNodeRef* node, const char*)',
        '{',
        '    std::lock_guard<std::mutex> lock(vpyCallbackData->reorderMapMutex);',
        '    vpyCallbackData->reorderMap[n] = f;',
        '    ++vpyCallbackData->completedFrames;',
        '    if(!f)',
        '    {',
        '        vpyCallbackData->isRunning = false;',
        '        return;',
        '    }',
        '}',
        'VPYInput::~VPYInput()',
        '{',
        '    if(frame0 && vsapi)',
        '    {',
        '        vsapi->freeFrame(frame0);',
        '        frame0 = nullptr;',
        '    }',
        '    if(node && vsapi)',
        '    {',
        '        vsapi->freeNode(node);',
        '        node = nullptr;',
        '    }',
        '    if (vss_func.freeScript)',
        '        vss_func.freeScript(script);',
        '    script = nullptr;',
        '    if (vss_func.finalize)',
        '        vss_func.finalize();',
        '}',
        'void VPYInput::startReader()',
        '{',
        '    const int intitalRequestSize = std::min<int>(vpyCallbackData.parallelRequests, vpyCallbackData.totalFrames - requestStart);',
        '}',
        'void VPYInput::release()',
        '{',
        '    std::lock_guard<std::mutex> lock(vpyCallbackData.reorderMapMutex);',
        '    auto currentFrameItr = vpyCallbackData.reorderMap.find(frame);',
        '    currentFrame = currentFrameItr->second;',
        '    vpyCallbackData.reorderMap.erase(currentFrameItr);',
        '    if (currentFrame == frame0)',
        '        frame0 = nullptr;',
        '    vsapi->freeFrame(currentFrame);',
        '}',
        'bool VPYInput::readPicture(x265_picture& pic)',
        '{',
        '    if(nextFrame >= vpyCallbackData.totalFrames)',
        '        return false;',
        '    while (true)',
        '    {',
        '        std::lock_guard<std::mutex> lock(vpyCallbackData.reorderMapMutex);',
        '        auto currentFrameItr = vpyCallbackData.reorderMap.find(nextFrame);',
        '        if (currentFrameItr != vpyCallbackData.reorderMap.end())',
        '        {',
        '            currentFrame = currentFrameItr->second;',
        '            vpyCallbackData.reorderMap.erase(currentFrameItr);',
        '            break;',
        '        }',
        '    }',
        '    ++vpyCallbackData.outputFrames;',
        '    if(!currentFrame)',
        '    {',
        '        vpyFailed = true;',
        '        vpyCallbackData.isRunning = false;',
        '        return false;',
        '    }',
        '    if (requiredFrameSize > frame_size || frame_buffer == nullptr)',
        '    {',
        '        uint8_t* newFrameBuffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));',
        '        if (!newFrameBuffer)',
        '            return false;',
        '        X265_FREE(frame_buffer);',
        '        frame_buffer = newFrameBuffer;',
        '        frame_size = requiredFrameSize;',
        '    }',
        '    if (currentFrame == frame0)',
        '        frame0 = nullptr;',
        '    vsapi->freeFrame(currentFrame);',
        '}',
    )) + '\n'


def valid_header_text():
    return '\n'.join((
        '#include <mutex>',
        'std::mutex reorderMapMutex;',
        'bool isEof() const { return nextFrame >= vpyCallbackData.totalFrames; }',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text(),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': 'X265_FREE(frame_buffer);\n        frame_buffer = reinterpret_cast<uint8_t*>(x265_malloc(requiredFrameSize));\n',
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'forbidden VPY buffer replace safety regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace('while (true)\n', 'while (!!!vpyCallbackData.reorderMap[nextFrame])\n', 1),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'forbidden VPY buffer replace safety regression: while (!!!vpyCallbackData.reorderMap[nextFrame])')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '    if(!currentFrame)\n'
                    '    {\n'
                    '        vpyFailed = true;\n'
                    '        vpyCallbackData.isRunning = false;\n'
                    '        return false;\n'
                    '    }\n',
                    '',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'missing VPY async frame guardrail: if(!currentFrame)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace('#include <mutex>\n', '', 1),
                'source/input/vpy.h': 'std::mutex reorderMapMutex;\n',
            },
        )
        expect_fail(run_checker(root), 'missing VPY async frame header guardrail: #include <mutex>')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '    if (vss_func.freeScript)\n'
                    '        vss_func.freeScript(script);\n'
                    '    script = nullptr;\n'
                    '    if (vss_func.finalize)\n'
                    '        vss_func.finalize();\n',
                    '    vss_func.freeScript(script);\n'
                    '    vss_func.finalize();\n',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'VPYInput::~VPYInput must guard partially initialized VapourSynth state before releasing it')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '    if(!vsapi)\n'
                    '    {\n'
                    '        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth API\\n");\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'missing VPY async frame guardrail: if(!vsapi)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '    if(!core)\n'
                    '    {\n'
                    '        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth core\\n");\n'
                    '        vpyFailed = true;\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'missing VPY async frame guardrail: if(!core)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '    if(!vi->format)\n'
                    '    {\n'
                    '        general_log(nullptr, "vpy", X265_LOG_ERROR, "VapourSynth returned a null video format\\n");\n'
                    '        vpyFailed = true;\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'missing VPY async frame guardrail: if(!vi->format)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '    if(!isConstantFormat(vi))\n'
                    '    {\n'
                    '        general_log(nullptr, "vpy", X265_LOG_ERROR, "only constant video formats are supported\\n");\n'
                    '        vpyFailed = true;\n'
                    '        return;\n'
                    '    }\n',
                    '    if(!isConstantFormat(vi))\n'
                    '    {\n'
                    '        general_log(nullptr, "vpy", X265_LOG_ERROR, "only constant video formats are supported\\n");\n'
                    '        vpyFailed = true;\n'
                    '    }\n',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'VPYInput::VPYInput must fail fast on non-constant VapourSynth formats before bootstrapping frame 0 state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '        const char* scriptError = vss_func.getError(script);\n',
                    '',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'missing VPY async frame guardrail: const char* scriptError = vss_func.getError(script);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '        vpyFailed = true;\n'
                    '        return;\n',
                    '        vpyFailed = true;\n'
                    '        vss_func.freeScript(script);\n'
                    '        vss_func.finalize();\n'
                    '        return;\n',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'VPYInput::VPYInput must leave script cleanup to the destructor after evaluateFile failures')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '    if(!frameProps0)\n'
                    '    {\n'
                    '        general_log(nullptr, "vpy", X265_LOG_ERROR, "failed to get VapourSynth frame properties for frame 0\\n");\n'
                    '        vpyFailed = true;\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'missing VPY async frame guardrail: if(!frameProps0)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '    const char* pixelType = vi->format->name ? vi->format->name : "unknown";\n'
                    '    bool supportedFormat = false;\n'
                    '    supportedFormat = true;\n'
                    '    if (!supportedFormat)\n'
                    '    {\n'
                    '        general_log(nullptr, "vpy", X265_LOG_ERROR, "not supported pixel type: %s\\n", pixelType);\n'
                    '        vpyFailed = true;\n'
                    '        return;\n'
                    '    }\n'
                    '    vpyCallbackData.reorderMap[nextFrame] = frame0;\n'
                    '    ++vpyCallbackData.completedFrames;\n'
                    '    _info = info;\n',
                    '    vpyCallbackData.reorderMap[nextFrame] = frame0;\n'
                    '    ++vpyCallbackData.completedFrames;\n'
                    '    const char* pixelType = vi->format->name ? vi->format->name : "unknown";\n'
                    '    bool supportedFormat = false;\n'
                    '    supportedFormat = true;\n'
                    '    if (!supportedFormat)\n'
                    '    {\n'
                    '        general_log(nullptr, "vpy", X265_LOG_ERROR, "not supported pixel type: %s\\n", pixelType);\n'
                    '        vpyFailed = true;\n'
                    '        return;\n'
                    '    }\n'
                    '    _info = info;\n',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'VPYInput::VPYInput must fail fast on non-constant VapourSynth formats before bootstrapping frame 0 state')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/vpy.cpp': valid_cpp_text().replace(
                    '    if (!supportedFormat)\n'
                    '    {\n'
                    '        general_log(nullptr, "vpy", X265_LOG_ERROR, "not supported pixel type: %s\\n", pixelType);\n'
                    '        vpyFailed = true;\n'
                    '        return;\n'
                    '    }\n',
                    '',
                    1,
                ),
                'source/input/vpy.h': valid_header_text(),
            },
        )
        expect_fail(run_checker(root), 'missing VPY async frame guardrail: if (!supportedFormat)')

    print('VPY buffer replace safety tests passed')


if __name__ == '__main__':
    main()
