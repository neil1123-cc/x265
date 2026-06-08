#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_lavf_openfile_cleanup.py')

# Coverage probes used by the scan for LAVF openfile cleanup guardrails.
NORMALIZED_PROBES = (
    'LavfInput::openfile must sanitize format, codec, and pixel-format log metadata before reporting video info',
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
        'void LavfInput::cleanupState()',
        'cleanupState();',
        'if (h->first_pic)',
        'std::free(h->first_pic);',
        'h->first_pic = nullptr;',
        'avcodec_free_context(&h->cocon);',
        'avformat_close_input(&h->lavf);',
        'av_frame_free(&h->frame);',
        'auto failOpen = [&](const char *message)',
        'general_log(nullptr, "lavf", X265_LOG_ERROR, "%s", message);',
        'failOpen("could not open input file\\n");',
        'failOpen("could not find input stream info\\n");',
        'failOpen("could not find video stream\\n");',
        'failOpen("could not find decoder for video stream\\n");',
        'failOpen("could not allocate decoder context\\n");',
        'failOpen("could not initialize decoder context\\n");',
        'failOpen("malloc failed\\n");',
        'const AVPixFmtDescriptor *pix_desc = av_pix_fmt_desc_get((AVPixelFormat)cp->format);',
        'if (!pix_desc)',
        '    failOpen("could not describe pixel format\\n");',
        'const char* formatName = (h->lavf->iformat && h->lavf->iformat->name) ? h->lavf->iformat->name : "unknown";',
        'const char* codecName = codec->name ? codec->name : "unknown";',
        'const char* codecLongName = codec->long_name ? codec->long_name : codecName;',
        'const char* pixDescName = pix_desc->name ? pix_desc->name : "unknown";',
        'general_log(nullptr, "lavf", X265_LOG_INFO,',
        'bool LavfInput::readPicture(x265_picture& p_pic, InputFileInfo* info)',
        'if (!h->cocon)',
        '{',
        '    const AVCodec *codec = avcodec_find_decoder(stream->codecpar->codec_id);',
        '    if (!codec)',
        '    {',
        '        general_log(nullptr, "lavf", X265_LOG_ERROR, "could not find decoder for video stream\\n");',
        '        b_fail = true;',
        '        return false;',
        '    }',
        '    h->cocon = avcodec_alloc_context3(codec);',
        '    if (!h->cocon)',
        '    {',
        '        general_log(nullptr, "lavf", X265_LOG_ERROR, "could not allocate decoder context\\n");',
        '        b_fail = true;',
        '        return false;',
        '    }',
        '    if (avcodec_parameters_to_context(h->cocon, stream->codecpar) < 0)',
        '    {',
        '        general_log(nullptr, "lavf", X265_LOG_ERROR, "could not initialize decoder context\\n");',
        '        avcodec_free_context(&h->cocon);',
        '        b_fail = true;',
        '        return false;',
        '    }',
        '    AVDictionary *avcodec_opts = nullptr;',
        '    av_dict_set(&avcodec_opts, "strict", "-2", 0);',
        '    if (avcodec_open2(h->cocon, codec, &avcodec_opts))',
        '    {',
        '        if (avcodec_opts)',
        '            av_dict_free(&avcodec_opts);',
        '        general_log(nullptr, "lavf", X265_LOG_ERROR, "could not find decoder for video stream\\n");',
        '        avcodec_free_context(&h->cocon);',
        '        b_fail = true;',
        '        return false;',
        '    }',
        '    if (avcodec_opts)',
        '        av_dict_free(&avcodec_opts);',
        '}',
        'pkt = av_packet_alloc();',
        'if (!pkt)',
        '{',
        '    general_log(nullptr, "lavf", X265_LOG_ERROR, "could not allocate input packet\\n");',
        '    b_fail = true;',
        '    return false;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': valid_cpp_text(),
                'source/input/lavf.h': 'void cleanupState();\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': 'FAIL_IF_ERROR(avformat_open_input(&h->lavf, info.filename, nullptr, nullptr), "could not open input file\\n")\n',
                'source/input/lavf.h': 'void cleanupState();\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden Lavf openfile cleanup regression')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': '\n'.join((
                    'void LavfInput::cleanupState()',
                    'cleanupState();',
                    'if (h->first_pic)',
                    'std::free(h->first_pic);',
                    'h->first_pic = nullptr;',
                    'avcodec_free_context(&h->cocon);',
                    'avformat_close_input(&h->lavf);',
                    'av_frame_free(&h->frame);',
                    'auto failOpen = [&](const char *message)',
                    'general_log(nullptr, "lavf", X265_LOG_ERROR, "%s", message);',
                    'failOpen("could not open input file\\n");',
                    'failOpen("could not find input stream info\\n");',
                    'failOpen("could not find video stream\\n");',
                    'failOpen("could not find decoder for video stream\\n");',
                    'failOpen("could not allocate decoder context\\n");',
                    'failOpen("could not initialize decoder context\\n");',
                    'failOpen("malloc failed\\n");',
                    'bool LavfInput::readPicture(x265_picture& p_pic, InputFileInfo* info)',
                    'if (!h->cocon)',
                    '{',
                    '    const AVCodec *codec = avcodec_find_decoder(stream->codecpar->codec_id);',
                    '    if (!codec)',
                    '    {',
                    '        general_log(nullptr, "lavf", X265_LOG_ERROR, "could not find decoder for video stream\\n");',
                    '        b_fail = true;',
                    '        return false;',
                    '    }',
                    '    h->cocon = avcodec_alloc_context3(codec);',
                    '    if (!h->cocon)',
                    '    {',
                    '        general_log(nullptr, "lavf", X265_LOG_ERROR, "could not allocate decoder context\\n");',
                    '        b_fail = true;',
                    '        return false;',
                    '    }',
                    '    if (avcodec_parameters_to_context(h->cocon, stream->codecpar) < 0)',
                    '    {',
                    '        general_log(nullptr, "lavf", X265_LOG_ERROR, "could not initialize decoder context\\n");',
                    '        avcodec_free_context(&h->cocon);',
                    '        b_fail = true;',
                    '        return false;',
                    '    }',
                    '    AVDictionary *avcodec_opts = nullptr;',
                    '    av_dict_set(&avcodec_opts, "strict", "-2", 0);',
                    '    if (avcodec_open2(h->cocon, codec, &avcodec_opts))',
                    '    {',
                    '        if (avcodec_opts)',
                    '            av_dict_free(&avcodec_opts);',
                    '        general_log(nullptr, "lavf", X265_LOG_ERROR, "could not find decoder for video stream\\n");',
                    '        avcodec_free_context(&h->cocon);',
                    '        b_fail = true;',
                    '        return false;',
                    '    }',
                    '    if (avcodec_opts)',
                    '        av_dict_free(&avcodec_opts);',
                    '}',
                    'pkt = av_packet_alloc();',
                )) + '\n',
                'source/input/lavf.h': 'void cleanupState();\n',
            },
        )
        expect_fail(run_checker(root), 'missing Lavf readPicture guardrail: if (!pkt)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': valid_cpp_text().replace(
                    'if (avcodec_open2(h->cocon, codec, &avcodec_opts))',
                    'avcodec_open2(h->cocon, codec, nullptr);\nif (avcodec_open2(h->cocon, codec, &avcodec_opts))',
                    1,
                ),
                'source/input/lavf.h': 'void cleanupState();\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden Lavf readPicture regression: avcodec_open2(h->cocon, codec, nullptr);')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': valid_cpp_text().replace(
                    'if (!pix_desc)\n'
                    '    failOpen("could not describe pixel format\\n");\n',
                    '',
                    1,
                ),
                'source/input/lavf.h': 'void cleanupState();\n',
            },
        )
        expect_fail(run_checker(root), 'missing Lavf openfile cleanup guardrail: if (!pix_desc)')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/input/lavf.cpp': valid_cpp_text().replace(
                    'const char* codecLongName = codec->long_name ? codec->long_name : codecName;\n',
                    '',
                    1,
                ),
                'source/input/lavf.h': 'void cleanupState();\n',
            },
        )
        expect_fail(run_checker(root), 'missing Lavf openfile cleanup guardrail: const char* codecLongName = codec->long_name ? codec->long_name : codecName;')

    print('Lavf openfile cleanup tests passed')


if __name__ == '__main__':
    main()
