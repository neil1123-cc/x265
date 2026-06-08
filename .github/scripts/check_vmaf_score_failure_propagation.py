#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')


def extract_braced_block(text, signature):
    start = text.find(signature)
    if start == -1:
        return ''
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


def check_function(func_text, label, required_snippets, forbidden_snippets, ordering, ordering_message):
    failures = []
    if not func_text:
        failures.append((TARGET.as_posix(), 0, f'missing {label} function'))
        return failures

    for snippet in forbidden_snippets:
        if snippet in func_text:
            failures.append((TARGET.as_posix(), 0, f'forbidden {label} failure-propagation regression: {snippet}'))
    for snippet in required_snippets:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing {label} failure-propagation guardrail: {snippet}'))

    positions = []
    search_from = 0
    for snippet in ordering:
        pos = func_text.find(snippet, search_from)
        positions.append(pos)
        if pos != -1:
            search_from = pos
    if any(pos == -1 for pos in positions) or positions != sorted(positions):
        failures.append((TARGET.as_posix(), 0, ordering_message))

    return failures


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    score_text = extract_braced_block(text, 'double x265_calculate_vmafscore(x265_param *param, x265_vmaf_data *data)')
    framelevel_text = extract_braced_block(text, 'double x265_calculate_vmaf_framelevelscore(x265_param *param, x265_vmaf_framedata *vmafframedata)')

    failures = []
    failures.extend(check_function(
        score_text,
        'x265_calculate_vmafscore',
        (
            'double score = 0.0;',
            'const char* pix_format = nullptr;',
            'x265_log(nullptr, X265_LOG_ERROR, "Invalid format\\n");',
            'if (compute_vmaf(&score, (char*)pix_format',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmafscore failed to compute VMAF score\\n");',
            'return 0.0;',
        ),
        (
            'double score;',
            'const char* pix_format;',
            'compute_vmaf(&score, (char*)pix_format, data->width, data->height, param->sourceBitDepth, read_frame, data, vcd->model_path, vcd->log_path, vcd->log_fmt, vcd->disable_clip, vcd->disable_avx, vcd->enable_transform, vcd->phone_model, vcd->psnr, vcd->ssim, vcd->ms_ssim, vcd->pool, vcd->thread, vcd->subsample);\n',
        ),
        (
            'double score = 0.0;',
            'const char* pix_format = nullptr;',
            'x265_log(nullptr, X265_LOG_ERROR, "Invalid format\\n");',
            'return 0.0;',
            'if (compute_vmaf(&score, (char*)pix_format',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmafscore failed to compute VMAF score\\n");',
            'return 0.0;',
            'return score;',
        ),
        'x265_calculate_vmafscore must initialize score/pix_format and fail fast on invalid format or compute_vmaf() errors before returning a score',
    ))
    failures.extend(check_function(
        framelevel_text,
        'x265_calculate_vmaf_framelevelscore',
        (
            'double score = 0.0;',
            'const char* pix_format = nullptr;',
            'x265_log(nullptr, X265_LOG_ERROR, "Invalid format\\n");',
            'if (compute_vmaf(&score, (char*)pix_format',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmaf_framelevelscore failed to compute VMAF score\\n");',
            'return 0.0;',
        ),
        (
            'double score;',
            'const char* pix_format;',
            'compute_vmaf(&score, (char*)pix_format, vmafframedata->width, vmafframedata->height, param->sourceBitDepth, read_frame, vmafframedata, vcd->model_path, vcd->log_path, vcd->log_fmt, vcd->disable_clip, vcd->disable_avx, vcd->enable_transform, vcd->phone_model, vcd->psnr, vcd->ssim, vcd->ms_ssim, vcd->pool, vcd->thread, vcd->subsample);\n',
            'else\n        pix_format = "yuv444p10le";',
        ),
        (
            'double score = 0.0;',
            'const char* pix_format = nullptr;',
            'x265_log(nullptr, X265_LOG_ERROR, "Invalid format\\n");',
            'return 0.0;',
            'if (compute_vmaf(&score, (char*)pix_format',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmaf_framelevelscore failed to compute VMAF score\\n");',
            'return 0.0;',
            'return score;',
        ),
        'x265_calculate_vmaf_framelevelscore must initialize score/pix_format and fail fast on invalid format or compute_vmaf() errors before returning a score',
    ))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF score failure propagation')
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

    print('VMAF score failure propagation validated')


if __name__ == '__main__':
    main()
