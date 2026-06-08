#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET_CPP = Path('source/input/lavf.cpp')
TARGET_H = Path('source/input/lavf.h')
REQUIRED_CPP_SNIPPETS = (
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
    'failOpen("could not describe pixel format\\n");',
    'const char* formatName = (h->lavf->iformat && h->lavf->iformat->name) ? h->lavf->iformat->name : "unknown";',
    'const char* codecName = codec->name ? codec->name : "unknown";',
    'const char* codecLongName = codec->long_name ? codec->long_name : codecName;',
    'const char* pixDescName = pix_desc->name ? pix_desc->name : "unknown";',
)
FORBIDDEN_CPP_SNIPPETS = (
    'FAIL_IF_ERROR(avformat_open_input(&h->lavf, info.filename, nullptr, nullptr), "could not open input file\\n")',
    'FAIL_IF_ERROR(avformat_find_stream_info(h->lavf, nullptr) < 0, "could not find input stream info\\n")',
    'FAIL_IF_ERROR(i == h->lavf->nb_streams, "could not find video stream\\n")',
    'FAIL_IF_ERROR(!h->first_pic, "malloc failed\\n")',
)
REQUIRED_H_SNIPPETS = (
    'void cleanupState();',
)
READPICTURE_START = 'bool LavfInput::readPicture(x265_picture& p_pic, InputFileInfo* info)'
READPICTURE_REQUIRED_SNIPPETS = (
    'if (!h->cocon)',
    'const AVCodec *codec = avcodec_find_decoder(stream->codecpar->codec_id);',
    'if (!codec)',
    'general_log(nullptr, "lavf", X265_LOG_ERROR, "could not find decoder for video stream\\n");',
    'h->cocon = avcodec_alloc_context3(codec);',
    'if (!h->cocon)',
    'general_log(nullptr, "lavf", X265_LOG_ERROR, "could not allocate decoder context\\n");',
    'if (avcodec_parameters_to_context(h->cocon, stream->codecpar) < 0)',
    'general_log(nullptr, "lavf", X265_LOG_ERROR, "could not initialize decoder context\\n");',
    'avcodec_free_context(&h->cocon);',
    'AVDictionary *avcodec_opts = nullptr;',
    'av_dict_set(&avcodec_opts, "strict", "-2", 0);',
    'if (avcodec_open2(h->cocon, codec, &avcodec_opts))',
    'if (avcodec_opts)',
    'av_dict_free(&avcodec_opts);',
    'pkt = av_packet_alloc();',
    'if (!pkt)',
    'general_log(nullptr, "lavf", X265_LOG_ERROR, "could not allocate input packet\\n");',
    'b_fail = true;',
    'return false;',
)
READPICTURE_FORBIDDEN_SNIPPETS = (
    'avcodec_parameters_to_context(h->cocon, stream->codecpar);',
    'avcodec_open2(h->cocon, codec, nullptr);',
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


def check_repo(repo_root):
    repo_root = Path(repo_root)
    failures = []
    cpp_path = repo_root / TARGET_CPP
    failures.extend(check_file(cpp_path, REQUIRED_CPP_SNIPPETS, FORBIDDEN_CPP_SNIPPETS, 'Lavf openfile cleanup'))
    failures.extend(check_file(repo_root / TARGET_H, REQUIRED_H_SNIPPETS, (), 'Lavf openfile cleanup header'))
    if not cpp_path.is_file():
        return failures

    text = cpp_path.read_text(encoding='utf-8', errors='ignore')
    readpicture_pos = text.find(READPICTURE_START)
    if readpicture_pos == -1:
        failures.append((cpp_path.as_posix(), 0, f'missing Lavf readPicture guardrail: {READPICTURE_START}'))
        return failures

    for snippet in READPICTURE_FORBIDDEN_SNIPPETS:
        if text.find(snippet, readpicture_pos) != -1:
            failures.append((cpp_path.as_posix(), 0, f'forbidden Lavf readPicture regression: {snippet}'))

    pos = readpicture_pos
    for snippet in READPICTURE_REQUIRED_SNIPPETS:
        pos = text.find(snippet, pos)
        if pos == -1:
            failures.append((cpp_path.as_posix(), 0, f'missing Lavf readPicture guardrail: {snippet}'))
            break

    pix_desc_pos = text.find('const AVPixFmtDescriptor *pix_desc = av_pix_fmt_desc_get((AVPixelFormat)cp->format);')
    pix_desc_guard_pos = text.find('if (!pix_desc)', pix_desc_pos if pix_desc_pos != -1 else 0)
    pix_desc_fail_pos = text.find('failOpen("could not describe pixel format\\n");', pix_desc_guard_pos if pix_desc_guard_pos != -1 else 0)
    format_name_pos = text.find('const char* formatName = (h->lavf->iformat && h->lavf->iformat->name) ? h->lavf->iformat->name : "unknown";', pix_desc_fail_pos if pix_desc_fail_pos != -1 else 0)
    codec_name_pos = text.find('const char* codecName = codec->name ? codec->name : "unknown";', format_name_pos if format_name_pos != -1 else 0)
    codec_long_name_pos = text.find('const char* codecLongName = codec->long_name ? codec->long_name : codecName;', codec_name_pos if codec_name_pos != -1 else 0)
    pix_desc_name_pos = text.find('const char* pixDescName = pix_desc->name ? pix_desc->name : "unknown";', codec_long_name_pos if codec_long_name_pos != -1 else 0)
    general_log_pos = text.find('general_log(nullptr, "lavf", X265_LOG_INFO,', pix_desc_name_pos if pix_desc_name_pos != -1 else 0)
    if -1 in (pix_desc_pos, pix_desc_guard_pos, pix_desc_fail_pos, format_name_pos, codec_name_pos, codec_long_name_pos, pix_desc_name_pos, general_log_pos) or not (
        pix_desc_pos < pix_desc_guard_pos < pix_desc_fail_pos < format_name_pos < codec_name_pos < codec_long_name_pos < pix_desc_name_pos < general_log_pos
    ):
        failures.append((cpp_path.as_posix(), 0, 'LavfInput::openfile must sanitize format, codec, and pixel-format log metadata before reporting video info'))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check Lavf openfile cleanup guardrails')
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

    print('Lavf openfile cleanup validated')


if __name__ == '__main__':
    main()
