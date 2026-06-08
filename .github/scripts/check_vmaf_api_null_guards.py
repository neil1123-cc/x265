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


def check_function(func_text, label, snippets, ordering, ordering_message):
    failures = []
    if not func_text:
        failures.append((TARGET.as_posix(), 0, f'missing {label} function'))
        return failures

    for snippet in snippets:
        if snippet not in func_text:
            failures.append((TARGET.as_posix(), 0, f'missing {label} null guardrail: {snippet}'))

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
    encoder_log_text = extract_braced_block(text, 'void x265_vmaf_encoder_log(x265_encoder* enc, int argc, char **argv, x265_param *param, x265_vmaf_data *vmafdata)')
    score_text = extract_braced_block(text, 'double x265_calculate_vmafscore(x265_param *param, x265_vmaf_data *data)')
    framelevel_text = extract_braced_block(text, 'double x265_calculate_vmaf_framelevelscore(x265_param *param, x265_vmaf_framedata *vmafframedata)')

    failures = []
    failures.extend(check_function(
        encoder_log_text,
        'x265_vmaf_encoder_log',
        (
            'if (!enc || !param || !vmafdata)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_vmaf_encoder_log requires non-null encoder, param, and VMAF data\\n");',
            'return;',
            'Encoder *encoder = static_cast<Encoder*>(enc);',
        ),
        (
            'if (!enc || !param || !vmafdata)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_vmaf_encoder_log requires non-null encoder, param, and VMAF data\\n");',
            'return;',
            'Encoder *encoder = static_cast<Encoder*>(enc);',
        ),
        'x265_vmaf_encoder_log must reject null encoder/param/vmafdata before touching encoder state',
    ))
    failures.extend(check_function(
        score_text,
        'x265_calculate_vmafscore',
        (
            'if (!param || !data)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmafscore requires non-null param and VMAF data\\n");',
            'return 0.0;',
            'if (!data->reference_file || !data->distorted_file)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmafscore requires non-null VMAF input files\\n");',
            'data->width = param->sourceWidth;',
        ),
        (
            'if (!param || !data)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmafscore requires non-null param and VMAF data\\n");',
            'return 0.0;',
            'if (!data->reference_file || !data->distorted_file)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmafscore requires non-null VMAF input files\\n");',
            'data->width = param->sourceWidth;',
        ),
        'x265_calculate_vmafscore must reject null param/data/files before populating VMAF dimensions',
    ))
    failures.extend(check_function(
        framelevel_text,
        'x265_calculate_vmaf_framelevelscore',
        (
            'if (!param || !vmafframedata)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmaf_framelevelscore requires non-null param and frame data\\n");',
            'return 0.0;',
            'if (!vmafframedata->reference_frame || !vmafframedata->distorted_frame)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmaf_framelevelscore requires non-null reference and distorted frames\\n");',
            'if (param->internalCsp == X265_CSP_I420)',
        ),
        (
            'if (!param || !vmafframedata)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmaf_framelevelscore requires non-null param and frame data\\n");',
            'return 0.0;',
            'if (!vmafframedata->reference_frame || !vmafframedata->distorted_frame)',
            'x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmaf_framelevelscore requires non-null reference and distorted frames\\n");',
            'if (param->internalCsp == X265_CSP_I420)',
        ),
        'x265_calculate_vmaf_framelevelscore must reject null inputs before reading frame pointers or colorspace',
    ))
    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF API null guards')
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

    print('VMAF API null guards validated')


if __name__ == '__main__':
    main()
