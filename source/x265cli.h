/*****************************************************************************
 * Copyright (C) 2013-2020 MulticoreWare, Inc
 *
 * Authors: Steve Borho <steve@borho.org>
 *          Min Chen <chenm003@163.com>
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

#ifndef X265CLI_H
#define X265CLI_H 1

#include "common.h"
#include "param.h"
#include "input/input.h"
#include "output/output.h"
#include "output/reconplay.h"
#include "filters/filters.h"

#include <cstring>
#include <getopt.h>

#ifdef _WIN32
#include <windows.h>
#define SetThreadExecutionState(es)
#else
#define GetConsoleTitle(t, n)
#define SetConsoleTitle(t)
#define SetThreadExecutionState(es)
#endif

#ifdef __cplusplus
namespace X265_NS {
#endif

template <typename Char, typename MissingToken, typename BeginToken, typename EmitChar, typename EndToken, typename UnterminatedToken, typename EmptyToken>
static inline bool walkConfigTokens(Char* start, MissingToken&& missingToken, BeginToken&& beginToken, EmitChar&& emitChar, EndToken&& endToken, UnterminatedToken&& unterminatedToken, EmptyToken&& emptyToken)
{
    while (start && std::isspace((unsigned char)*start))
        start++;

    if (!start || !*start)
        return missingToken();

    while (*start)
    {
        if (*start == '#')
            break;

        Char* tokenStart = start;
        Char* cursor = start;
        if (!beginToken(tokenStart))
            return false;

        bool inQuotes = false;
        size_t tokenLength = 0;
        while (*cursor)
        {
            if (*cursor == '"')
            {
                inQuotes = !inQuotes;
                cursor++;
                continue;
            }
            if (!inQuotes && std::isspace((unsigned char)*cursor))
                break;
            if (!emitChar(tokenStart, *cursor, tokenLength))
                return false;
            tokenLength++;
            cursor++;
        }

        if (inQuotes)
            return unterminatedToken();
        if (!tokenLength)
            return emptyToken();
        Char* next = cursor;
        bool endedOnWhitespace = *cursor && std::isspace((unsigned char)*cursor);
        if (!endToken(tokenStart, tokenLength))
            return false;

        if (endedOnWhitespace)
            next++;
        while (*next && std::isspace((unsigned char)*next))
            next++;
        start = next;
    }

    return true;
}

static inline bool validateConfigFileLine(FILE* file, const char* context, int lineNumber, const char* line, size_t lineCapacity)
{
    if (!file || !context || !line || lineCapacity < 2)
        return false;

    size_t length = std::strlen(line);
    if (length + 1 < lineCapacity || (length && line[length - 1] == '\n') || std::feof(file))
        return true;

    if (lineNumber > 0)
        x265_log(nullptr, X265_LOG_ERROR, "%s line %d exceeds supported length\n", context, lineNumber);
    else
        x265_log(nullptr, X265_LOG_ERROR, "%s contains a line exceeding supported length\n", context);
    return false;
}

static const char short_options[] = "o:D:P:p:f:F:r:I:i:b:s:t:q:m:hwV?";
static const struct option long_options[] =
{
    { "help",                 no_argument, nullptr, 'h' },
    { "fullhelp",             no_argument, nullptr, 0 },
    { "version",              no_argument, nullptr, 'V' },
    { "asm",            required_argument, nullptr, 0 },
    { "no-asm",               no_argument, nullptr, 0 },
    { "pools",          required_argument, nullptr, 0 },
    { "numa-pools",     required_argument, nullptr, 0 },
    { "preset",         required_argument, nullptr, 'p' },
    { "tune",           required_argument, nullptr, 't' },
    { "frame-threads",  required_argument, nullptr, 'F' },
    { "no-pmode",             no_argument, nullptr, 0 },
    { "pmode",                no_argument, nullptr, 0 },
    { "no-pme",               no_argument, nullptr, 0 },
    { "pme",                  no_argument, nullptr, 0 },
    { "log-level",           required_argument, nullptr, 0 },
    { "log-file",            required_argument, nullptr, 0 },
    { "log-file-level",      required_argument, nullptr, 0 },
    { "level-idc",      required_argument, nullptr, 0 },
    { "high-tier",            no_argument, nullptr, 0 },
    { "uhd-bd",               no_argument, nullptr, 0 },
    { "no-high-tier",         no_argument, nullptr, 0 },
    { "allow-non-conformance",no_argument, nullptr, 0 },
    { "no-allow-non-conformance",no_argument, nullptr, 0 },
    { "csv",            required_argument, nullptr, 0 },
    { "csv-log-level",  required_argument, nullptr, 0 },
    { "progress-file",  required_argument, nullptr, 0 },
    { "y4m",                  no_argument, nullptr, 0 },
    { "no-progress",          no_argument, nullptr, 0 },
    { "stylish",              no_argument, nullptr, 0 },
    { "output",         required_argument, nullptr, 'o' },
    { "output-depth",   required_argument, nullptr, 'D' },
    { "input",          required_argument, nullptr, 0 },
    { "input-depth",    required_argument, nullptr, 0 },
    { "input-res",      required_argument, nullptr, 0 },
    { "input-csp",      required_argument, nullptr, 0 },
    { "vf",             required_argument, nullptr, 0 },
    { "interlace",      required_argument, nullptr, 0 },
    { "no-interlace",         no_argument, nullptr, 0 },
    { "field",                no_argument, nullptr, 0 },
    { "no-field",             no_argument, nullptr, 0 },
    { "fps",            required_argument, nullptr, 0 },
    { "seek",           required_argument, nullptr, 0 },
    { "frames",         required_argument, nullptr, 'f' },
    { "recon",          required_argument, nullptr, 'r' },
    { "recon-depth",    required_argument, nullptr, 0 },
    { "no-wpp",               no_argument, nullptr, 0 },
    { "wpp",                  no_argument, nullptr, 0 },
    { "ctu",            required_argument, nullptr, 's' },
    { "min-cu-size",    required_argument, nullptr, 0 },
    { "max-tu-size",    required_argument, nullptr, 0 },
    { "tu-intra-depth", required_argument, nullptr, 0 },
    { "tu-inter-depth", required_argument, nullptr, 0 },
    { "limit-tu",       required_argument, nullptr, 0 },
    { "me",             required_argument, nullptr, 0 },
    { "subme",          required_argument, nullptr, 'm' },
    { "merange",        required_argument, nullptr, 0 },
    { "max-merge",      required_argument, nullptr, 0 },
    { "no-temporal-mvp",      no_argument, nullptr, 0 },
    { "temporal-mvp",         no_argument, nullptr, 0 },
    { "hme",                  no_argument, nullptr, 0 },
    { "no-hme",               no_argument, nullptr, 0 },
    { "hme-search",     required_argument, nullptr, 0 },
    { "rdpenalty",      required_argument, nullptr, 0 },
    { "no-rect",              no_argument, nullptr, 0 },
    { "rect",                 no_argument, nullptr, 0 },
    { "no-amp",               no_argument, nullptr, 0 },
    { "amp",                  no_argument, nullptr, 0 },
    { "no-early-skip",        no_argument, nullptr, 0 },
    { "early-skip",           no_argument, nullptr, 0 },
    { "rskip",                required_argument, nullptr, 0 },
    { "rskip-edge-threshold", required_argument, nullptr, 0 },
    { "no-fast-cbf",          no_argument, nullptr, 0 },
    { "fast-cbf",             no_argument, nullptr, 0 },
    { "no-tskip",             no_argument, nullptr, 0 },
    { "tskip",                no_argument, nullptr, 0 },
    { "no-tskip-fast",        no_argument, nullptr, 0 },
    { "tskip-fast",           no_argument, nullptr, 0 },
    { "cu-lossless",          no_argument, nullptr, 0 },
    { "no-cu-lossless",       no_argument, nullptr, 0 },
    { "no-constrained-intra", no_argument, nullptr, 0 },
    { "constrained-intra",    no_argument, nullptr, 0 },
    { "fast-intra",           no_argument, nullptr, 0 },
    { "no-fast-intra",        no_argument, nullptr, 0 },
    { "no-open-gop",          no_argument, nullptr, 0 },
    { "open-gop",             no_argument, nullptr, 0 },
    { "cra-nal",              no_argument, nullptr, 0 },
    { "keyint",         required_argument, nullptr, 'I' },
    { "min-keyint",     required_argument, nullptr, 'i' },
    { "gop-lookahead",  required_argument, nullptr, 0 },
    { "scenecut",       required_argument, nullptr, 0 },
    { "no-scenecut",          no_argument, nullptr, 0 },
    { "scenecut-bias",  required_argument, nullptr, 0 },
    { "hist-scenecut",        no_argument, nullptr, 0},
    { "no-hist-scenecut",     no_argument, nullptr, 0},
    { "fades",                no_argument, nullptr, 0 },
    { "no-fades",             no_argument, nullptr, 0 },
    { "scenecut-aware-qp", required_argument, nullptr, 0 },
    { "masking-strength",  required_argument, nullptr, 0 },
    { "radl",           required_argument, nullptr, 0 },
    { "ctu-info",       required_argument, nullptr, 0 },
    { "intra-refresh",        no_argument, nullptr, 0 },
    { "rc-lookahead",   required_argument, nullptr, 0 },
    { "lookahead-slices", required_argument, nullptr, 0 },
    { "lookahead-threads", required_argument, nullptr, 0 },
    { "bframes",        required_argument, nullptr, 'b' },
    { "bframe-bias",    required_argument, nullptr, 0 },
    { "b-adapt",        required_argument, nullptr, 0 },
    { "no-b-adapt",           no_argument, nullptr, 0 },
    { "no-b-pyramid",         no_argument, nullptr, 0 },
    { "b-pyramid",            no_argument, nullptr, 0 },
    { "ref",            required_argument, nullptr, 0 },
    { "limit-refs",     required_argument, nullptr, 0 },
    { "no-limit-modes",       no_argument, nullptr, 0 },
    { "limit-modes",          no_argument, nullptr, 0 },
    { "no-weightp",           no_argument, nullptr, 0 },
    { "weightp",              no_argument, nullptr, 'w' },
    { "no-weightb",           no_argument, nullptr, 0 },
    { "weightb",              no_argument, nullptr, 0 },
    { "crf",            required_argument, nullptr, 0 },
    { "crf-max",        required_argument, nullptr, 0 },
    { "crf-min",        required_argument, nullptr, 0 },
    { "vbv-maxrate",    required_argument, nullptr, 0 },
    { "vbv-bufsize",    required_argument, nullptr, 0 },
    { "vbv-init",       required_argument, nullptr, 0 },
    { "vbv-end",        required_argument, nullptr, 0 },
    { "vbv-end-fr-adj", required_argument, nullptr, 0 },
    { "chunk-start",    required_argument, nullptr, 0 },
    { "chunk-end",      required_argument, nullptr, 0 },
    { "bitrate",        required_argument, nullptr, 0 },
    { "qp",             required_argument, nullptr, 'q' },
    { "aq-mode",        required_argument, nullptr, 0 },
    { "limit-aq1",            no_argument, nullptr, 0 },
    { "no-limit-aq1",         no_argument, nullptr, 0 },
    { "aq-strength",    required_argument, nullptr, 0 },
    { "aq-bias-strength", required_argument, nullptr, 0 },
    { "limit-aq1-strength", required_argument, nullptr, 0 },
    { "sbrc",                 no_argument, nullptr, 0 },
    { "no-sbrc",              no_argument, nullptr, 0 },
    { "rc-grain",             no_argument, nullptr, 0 },
    { "no-rc-grain",          no_argument, nullptr, 0 },
    { "ipratio",        required_argument, nullptr, 0 },
    { "pbratio",        required_argument, nullptr, 0 },
    { "qcomp",          required_argument, nullptr, 0 },
    { "cutree-strength",required_argument, nullptr, 0 },
    { "cutree-minqpoffs",required_argument, nullptr, 0 },
    { "cutree-maxqpoffs",required_argument, nullptr, 0 },
    { "qscale-mode",    required_argument, nullptr, 0 },
    { "qpstep",         required_argument, nullptr, 0 },
    { "qpmin",          required_argument, nullptr, 0 },
    { "qpmax",          required_argument, nullptr, 0 },
    { "const-vbv",            no_argument, nullptr, 0 },
    { "no-const-vbv",         no_argument, nullptr, 0 },
    { "ratetol",        required_argument, nullptr, 0 },
    { "cplxblur",       required_argument, nullptr, 0 },
    { "qblur",          required_argument, nullptr, 0 },
    { "cbqpoffs",       required_argument, nullptr, 0 },
    { "crqpoffs",       required_argument, nullptr, 0 },
    { "rd",             required_argument, nullptr, 0 },
    { "rdoq-level",     required_argument, nullptr, 0 },
    { "no-rdoq-level",        no_argument, nullptr, 0 },
    { "dynamic-rd",     required_argument, nullptr, 0 },
    { "psy-rd",         required_argument, nullptr, 0 },
    { "psy-rdoq",       required_argument, nullptr, 0 },
    { "psy-bscale",     required_argument, nullptr, 0 },
    { "psy-pscale",     required_argument, nullptr, 0 },
    { "psy-iscale",     required_argument, nullptr, 0 },
    { "no-psy-rd",            no_argument, nullptr, 0 },
    { "no-psy-rdoq",          no_argument, nullptr, 0 },
    { "rd-refine",            no_argument, nullptr, 0 },
    { "no-rd-refine",         no_argument, nullptr, 0 },
    { "scaling-list",   required_argument, nullptr, 0 },
    { "lossless",             no_argument, nullptr, 0 },
    { "no-lossless",          no_argument, nullptr, 0 },
    { "no-signhide",          no_argument, nullptr, 0 },
    { "signhide",             no_argument, nullptr, 0 },
    { "no-deblock",           no_argument, nullptr, 0 },
    { "deblock",        required_argument, nullptr, 0 },
    { "no-sao",               no_argument, nullptr, 0 },
    { "selective-sao",  required_argument, nullptr, 0 },
    { "sao",                  no_argument, nullptr, 0 },
    { "no-sao-non-deblock",   no_argument, nullptr, 0 },
    { "sao-non-deblock",      no_argument, nullptr, 0 },
    { "no-ssim",              no_argument, nullptr, 0 },
    { "ssim",                 no_argument, nullptr, 0 },
    { "no-psnr",              no_argument, nullptr, 0 },
    { "psnr",                 no_argument, nullptr, 0 },
    { "hash",           required_argument, nullptr, 0 },
    { "no-strong-intra-smoothing", no_argument, nullptr, 0 },
    { "strong-intra-smoothing",    no_argument, nullptr, 0 },
    { "no-cutree",                 no_argument, nullptr, 0 },
    { "cutree",                    no_argument, nullptr, 0 },
    { "no-hrd",               no_argument, nullptr, 0 },
    { "hrd",                  no_argument, nullptr, 0 },
    { "sar",            required_argument, nullptr, 0 },
    { "overscan",       required_argument, nullptr, 0 },
    { "videoformat",    required_argument, nullptr, 0 },
    { "range",          required_argument, nullptr, 0 },
    { "colorprim",      required_argument, nullptr, 0 },
    { "transfer",       required_argument, nullptr, 0 },
    { "colormatrix",    required_argument, nullptr, 0 },
    { "chromaloc",      required_argument, nullptr, 0 },
    { "display-window", required_argument, nullptr, 0 },
    { "master-display", required_argument, nullptr, 0 },
    { "max-cll",        required_argument, nullptr, 0 },
    {"video-signal-type-preset", required_argument, nullptr, 0 },
    { "min-luma",       required_argument, nullptr, 0 },
    { "max-luma",       required_argument, nullptr, 0 },
    { "log2-max-poc-lsb", required_argument, nullptr, 8 },
    { "vui-timing-info",      no_argument, nullptr, 0 },
    { "no-vui-timing-info",   no_argument, nullptr, 0 },
    { "vui-hrd-info",         no_argument, nullptr, 0 },
    { "no-vui-hrd-info",      no_argument, nullptr, 0 },
    { "opt-qp-pps",           no_argument, nullptr, 0 },
    { "no-opt-qp-pps",        no_argument, nullptr, 0 },
    { "opt-ref-list-length-pps",         no_argument, nullptr, 0 },
    { "no-opt-ref-list-length-pps",      no_argument, nullptr, 0 },
    { "opt-cu-delta-qp",      no_argument, nullptr, 0 },
    { "no-opt-cu-delta-qp",   no_argument, nullptr, 0 },
    { "no-dither",            no_argument, nullptr, 0 },
    { "dither",               no_argument, nullptr, 0 },
    { "no-repeat-headers",    no_argument, nullptr, 0 },
    { "repeat-headers",       no_argument, nullptr, 0 },
    { "aud",                  no_argument, nullptr, 0 },
    { "no-aud",               no_argument, nullptr, 0 },
    { "eob",                  no_argument, nullptr, 0 },
    { "no-eob",               no_argument, nullptr, 0 },
    { "eos",                  no_argument, nullptr, 0 },
    { "no-eos",               no_argument, nullptr, 0 },
    { "info",                 no_argument, nullptr, 0 },
    { "no-info",              no_argument, nullptr, 0 },
    { "zones",          required_argument, nullptr, 0 },
    { "qpfile",         required_argument, nullptr, 0 },
    { "zonefile",       required_argument, nullptr, 0 },
    { "no-zonefile-rc-init",  no_argument, nullptr, 0 },
    { "lambda-file",    required_argument, nullptr, 0 },
    { "b-intra",              no_argument, nullptr, 0 },
    { "no-b-intra",           no_argument, nullptr, 0 },
    { "nr-intra",       required_argument, nullptr, 0 },
    { "nr-inter",       required_argument, nullptr, 0 },
    { "stats",          required_argument, nullptr, 0 },
    { "pass",           required_argument, nullptr, 0 },
    { "multi-pass-opt-analysis", no_argument, nullptr, 0 },
    { "no-multi-pass-opt-analysis",    no_argument, nullptr, 0 },
    { "multi-pass-opt-distortion",     no_argument, nullptr, 0 },
    { "no-multi-pass-opt-distortion",  no_argument, nullptr, 0 },
    { "vbv-live-multi-pass",           no_argument, nullptr, 0 },
    { "no-vbv-live-multi-pass",        no_argument, nullptr, 0 },
    { "slow-firstpass",       no_argument, nullptr, 0 },
    { "no-slow-firstpass",    no_argument, nullptr, 0 },
    { "multi-pass-opt-rps",   no_argument, nullptr, 0 },
    { "no-multi-pass-opt-rps", no_argument, nullptr, 0 },
    { "analysis-reuse-file", required_argument, nullptr, 0 },
    { "analysis-save-reuse-level", required_argument, nullptr, 0 },
    { "analysis-load-reuse-level", required_argument, nullptr, 0 },
    { "analysis-save",  required_argument, nullptr, 0 },
    { "analysis-load",  required_argument, nullptr, 0 },
    { "scale-factor",   required_argument, nullptr, 0 },
    { "refine-intra",   required_argument, nullptr, 0 },
    { "refine-inter",   required_argument, nullptr, 0 },
    { "dynamic-refine",       no_argument, nullptr, 0 },
    { "no-dynamic-refine",    no_argument, nullptr, 0 },
    { "strict-cbr",           no_argument, nullptr, 0 },
    { "temporal-layers",      required_argument, nullptr, 0 },
    { "qg-size",        required_argument, nullptr, 0 },
    { "recon-y4m-exec", required_argument, nullptr, 0 },
    { "analyze-src-pics", no_argument, nullptr, 0 },
    { "no-analyze-src-pics", no_argument, nullptr, 0 },
    { "slices",         required_argument, nullptr, 0 },
    { "aq-motion",            no_argument, nullptr, 0 },
    { "no-aq-motion",         no_argument, nullptr, 0 },
    { "ssim-rd",              no_argument, nullptr, 0 },
    { "no-ssim-rd",           no_argument, nullptr, 0 },
    { "hdr",                  no_argument, nullptr, 0 },
    { "no-hdr",               no_argument, nullptr, 0 },
    { "hdr10",                no_argument, nullptr, 0 },
    { "no-hdr10",             no_argument, nullptr, 0 },
    { "hdr10-opt",            no_argument, nullptr, 0 },
    { "no-hdr10-opt",         no_argument, nullptr, 0 },
    { "limit-sao",            no_argument, nullptr, 0 },
    { "no-limit-sao",         no_argument, nullptr, 0 },
    { "dhdr10-info",    required_argument, nullptr, 0 },
    { "dhdr10-opt",           no_argument, nullptr, 0},
    { "no-dhdr10-opt",        no_argument, nullptr, 0},
    { "dolby-vision-profile",  required_argument, nullptr, 0 },
    { "refine-mv",      required_argument, nullptr, 0 },
    { "refine-ctu-distortion", required_argument, nullptr, 0 },
    { "force-flush",    required_argument, nullptr, 0 },
    { "splitrd-skip",         no_argument, nullptr, 0 },
    { "no-splitrd-skip",      no_argument, nullptr, 0 },
    { "lowpass-dct",          no_argument, nullptr, 0 },
    { "refine-analysis-type", required_argument, nullptr, 0 },
    { "copy-pic",             no_argument, nullptr, 0 },
    { "no-copy-pic",          no_argument, nullptr, 0 },
    { "max-ausize-factor", required_argument, nullptr, 0 },
    { "idr-recovery-sei",     no_argument, nullptr, 0 },
    { "no-idr-recovery-sei",  no_argument, nullptr, 0 },
    { "single-sei", no_argument, nullptr, 0 },
    { "no-single-sei", no_argument, nullptr, 0 },
    { "atc-sei", required_argument, nullptr, 0 },
    { "pic-struct", required_argument, nullptr, 0 },
    { "nalu-file", required_argument, nullptr, 0 },
    { "dolby-vision-rpu", required_argument, nullptr, 0 },
    { "hrd-concat",          no_argument, nullptr, 0},
    { "no-hrd-concat",       no_argument, nullptr, 0 },
    { "hevc-aq", no_argument, nullptr, 0 },
    { "no-hevc-aq", no_argument, nullptr, 0 },
    { "qp-adaptation-range", required_argument, nullptr, 0 },
    { "frame-dup",            no_argument, nullptr, 0 },
    { "no-frame-dup", no_argument, nullptr, 0 },
    { "dup-threshold", required_argument, nullptr, 0 },
    { "mcstf",                 no_argument, nullptr, 0 },
    { "no-mcstf",              no_argument, nullptr, 0 },
#if ENABLE_ALPHA
    { "alpha",                 no_argument, nullptr, 0 },
#endif
#if ENABLE_MULTIVIEW
    { "num-views", required_argument, nullptr, 0 },
    { "multiview-config", required_argument, nullptr, 0 },
    { "format", required_argument, nullptr, 0 },
#endif
#if ENABLE_SCC_EXT
    { "scc",        required_argument, nullptr, 0 },
#endif
#ifdef SVT_HEVC
    { "svt",     no_argument, nullptr, 0 },
    { "no-svt",  no_argument, nullptr, 0 },
    { "svt-hme",     no_argument, nullptr, 0 },
    { "no-svt-hme",  no_argument, nullptr, 0 },
    { "svt-search-width",      required_argument, nullptr, 0 },
    { "svt-search-height",     required_argument, nullptr, 0 },
    { "svt-compressed-ten-bit-format",    no_argument, nullptr, 0 },
    { "no-svt-compressed-ten-bit-format", no_argument, nullptr, 0 },
    { "svt-speed-control",     no_argument  , nullptr, 0 },
    { "no-svt-speed-control",  no_argument  , nullptr, 0 },
    { "svt-preset-tuner",  required_argument  , nullptr, 0 },
    { "svt-hierarchical-level",  required_argument  , nullptr, 0 },
    { "svt-base-layer-switch-mode",  required_argument  , nullptr, 0 },
    { "svt-pred-struct",  required_argument  , nullptr, 0 },
    { "svt-fps-in-vps",  no_argument  , nullptr, 0 },
    { "no-svt-fps-in-vps",  no_argument  , nullptr, 0 },
#endif
    { "cll", no_argument, nullptr, 0 },
    { "no-cll", no_argument, nullptr, 0 },
    { "hme-range", required_argument, nullptr, 0 },
    { "abr-ladder", required_argument, nullptr, 0 },
    { "min-vbv-fullness", required_argument, nullptr, 0 },
    { "max-vbv-fullness", required_argument, nullptr, 0 },
    { "scenecut-qp-config", required_argument, nullptr, 0 },
    { "film-grain", required_argument, nullptr, 0 },
    { "aom-film-grain", required_argument, nullptr, 0 },
    { "frame-rc",no_argument, nullptr, 0 },
    { "no-frame-rc",no_argument, nullptr, 0 },
    { "threaded-me", no_argument, nullptr, 0 },
    { "no-threaded-me", no_argument, nullptr, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 }
};

static inline bool hasCliExitRequest(int argc, char** argv)
{
    const int savedOpterr = opterr;
    opterr = 0;
    for (optind = 0;;)
    {
        int long_options_index = -1;
        int c = getopt_long(argc, argv, short_options, long_options, &long_options_index);
        if (c == -1)
            break;
        if (c == 'h' || c == 'V')
        {
            opterr = savedOpterr;
            return true;
        }
        if (long_options_index >= 0 && !std::strcmp(long_options[long_options_index].name, "fullhelp"))
        {
            opterr = savedOpterr;
            return true;
        }
    }
    opterr = savedOpterr;
    return false;
}

static inline bool rejectCliExitRequest(int argc, char** argv, const char* context, int lineNumber)
{
    if (!hasCliExitRequest(argc, argv))
        return false;

    x265_log(nullptr, X265_LOG_ERROR, "%s at line %d cannot request CLI help or version output\n", context, lineNumber);
    return true;
}

    struct CLIOptions
    {
        InputFile* input[MAX_VIEWS];
        ReconFile* recon[MAX_LAYERS];
        OutputFile* output;
        FILE*       qpfile;
        FILE*       zoneFile;
        FILE*    dolbyVisionRpu;    /* File containing Dolby Vision BL RPU metadata */
        FILE*    scenecutAwareQpConfig; /* File containing scenecut aware frame quantization related CLI options */
#if ENABLE_MULTIVIEW
        FILE* multiViewConfig; /* File containing multi-view related CLI options */
#endif
        const char* reconPlayCmd;
        const x265_api* api;
        x265_param* param;
        x265_vmaf_data* vmafData;
        bool bProgress;
        bool bForceY4m;
        bool bDither;
        uint32_t seek;              // number of frames to skip from the beginning
        uint32_t framesToBeEncoded; // number of frames to encode
        uint64_t totalbytes;
        int64_t startTime;
        int64_t prevUpdateTime;
        int64_t prevUpdateTimeFile;

        int argCnt;
        int parseExitCode;
        char** orgArgv;
        char** argString;
        char *stringPool;
        char* inputfn[MAX_VIEWS];
        char* vf;
        std::vector<Filter*> filters;

        /* ABR ladder settings */
        bool isAbrLadderConfig;
        bool enableScaler;
        char     encName[X265_MAX_STRING_SIZE];
        char     reuseName[X265_MAX_STRING_SIZE];
        uint32_t encId;
        int      refId;
        uint32_t loadLevel;
        uint32_t saveLevel;
        uint32_t numRefs;

        /* in microseconds */
        static const int UPDATE_INTERVAL = 250000;
        static const int UPDATE_INTERVAL_FILE = 1000000;
        CLIOptions()
        {
            for (int i = 0; i < MAX_VIEWS; i++)
                input[i] = nullptr;
            for (int i = 0; i < MAX_LAYERS; i++)
                recon[i] = nullptr;
            for (int i = 0; i < MAX_VIEWS; i++)
                inputfn[i] = nullptr;
            output = nullptr;
            qpfile = nullptr;
            zoneFile = nullptr;
            dolbyVisionRpu = nullptr;
            scenecutAwareQpConfig = nullptr;
#if ENABLE_MULTIVIEW
            multiViewConfig = nullptr;
#endif
            reconPlayCmd = nullptr;
            api = nullptr;
            param = nullptr;
            vmafData = nullptr;
            framesToBeEncoded = seek = 0;
            totalbytes = 0;
            bProgress = true;
            bForceY4m = false;
            startTime = x265_mdate();
            prevUpdateTime = 0;
            prevUpdateTimeFile = 0;
            bDither = false;
            isAbrLadderConfig = false;
            enableScaler = false;
            encName[0] = 0;
            reuseName[0] = 0;
            encId = 0;
            refId = -1;
            loadLevel = 0;
            saveLevel = 0;
            numRefs = 0;
            argCnt = 0;
            parseExitCode = -1;
            orgArgv = nullptr;
            argString = nullptr;
            stringPool = nullptr;
            vf = nullptr;
        }

        bool destroy();
        void printStatus(uint32_t frameNum);
        bool parse(int argc, char **argv);
        bool parseZoneParam(int argc, char **argv, x265_param* globalParam, int zonefileCount);
        bool parseQPFile(x265_picture &pic_org);
        bool parseZoneFile();
        int rpuParser(x265_picture * pic);
        bool parseScenecutAwareQpConfig();
        bool parseScenecutAwareQpParam(int argc, char **argv, x265_param* globalParam);
#if ENABLE_MULTIVIEW
        bool parseMultiViewConfig(char** fn);
#endif
    };
#ifdef __cplusplus
}
#endif

#endif
