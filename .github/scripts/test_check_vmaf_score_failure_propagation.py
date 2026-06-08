#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_score_failure_propagation.py')

# Normalized checker probes used by the coverage scan for label-formatted failures.
NORMALIZED_PROBES = (
    'missing  function',
    'forbidden  failure-propagation regression: ',
    'missing  failure-propagation guardrail: ',
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


def replace_in_framelevel(text, old, new):
    signature = 'double x265_calculate_vmaf_framelevelscore(x265_param *param, x265_vmaf_framedata *vmafframedata)'
    prefix, marker, suffix = text.partition(signature)
    if not marker:
        raise AssertionError('framelevel signature missing from test fixture')
    if old not in suffix:
        raise AssertionError(f'missing framelevel snippet {old!r}')
    return prefix + marker + suffix.replace(old, new, 1)


def valid_text():
    return '\n'.join((
        'double x265_calculate_vmafscore(x265_param *param, x265_vmaf_data *data)',
        '{',
        '    double score = 0.0;',
        '    const char* pix_format = nullptr;',
        '    x265_log(nullptr, X265_LOG_ERROR, "Invalid format\\n");',
        '    return 0.0;',
        '    if (compute_vmaf(&score, (char*)pix_format, data->width, data->height, param->sourceBitDepth, read_frame, data, vcd->model_path, vcd->log_path, vcd->log_fmt, vcd->disable_clip, vcd->disable_avx, vcd->enable_transform, vcd->phone_model, vcd->psnr, vcd->ssim, vcd->ms_ssim, vcd->pool, vcd->thread, vcd->subsample) != 0)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmafscore failed to compute VMAF score\\n");',
        '        return 0.0;',
        '    }',
        '    return score;',
        '}',
        'double x265_calculate_vmaf_framelevelscore(x265_param *param, x265_vmaf_framedata *vmafframedata)',
        '{',
        '    double score = 0.0;',
        '    const char* pix_format = nullptr;',
        '    x265_log(nullptr, X265_LOG_ERROR, "Invalid format\\n");',
        '    return 0.0;',
        '    if (compute_vmaf(&score, (char*)pix_format, vmafframedata->width, vmafframedata->height, param->sourceBitDepth, read_frame, vmafframedata, vcd->model_path, vcd->log_path, vcd->log_fmt, vcd->disable_clip, vcd->disable_avx, vcd->enable_transform, vcd->phone_model, vcd->psnr, vcd->ssim, vcd->ms_ssim, vcd->pool, vcd->thread, vcd->subsample) != 0)',
        '    {',
        '        x265_log(nullptr, X265_LOG_ERROR, "x265_calculate_vmaf_framelevelscore failed to compute VMAF score\\n");',
        '        return 0.0;',
        '    }',
        '    return score;',
        '}',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': ''})
        expect_fail(run_checker(root), 'missing x265_calculate_vmafscore function')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text().replace('double score = 0.0;', 'double score;', 1)})
        expect_fail(run_checker(root), 'missing x265_calculate_vmafscore failure-propagation guardrail: double score = 0.0;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text().replace('const char* pix_format = nullptr;', 'const char* pix_format;', 1)})
        expect_fail(run_checker(root), 'forbidden x265_calculate_vmafscore failure-propagation regression: const char* pix_format;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text().replace('if (compute_vmaf(&score, (char*)pix_format, data->width, data->height, param->sourceBitDepth, read_frame, data, vcd->model_path, vcd->log_path, vcd->log_fmt, vcd->disable_clip, vcd->disable_avx, vcd->enable_transform, vcd->phone_model, vcd->psnr, vcd->ssim, vcd->ms_ssim, vcd->pool, vcd->thread, vcd->subsample) != 0)', 'compute_vmaf(&score, (char*)pix_format, data->width, data->height, param->sourceBitDepth, read_frame, data, vcd->model_path, vcd->log_path, vcd->log_fmt, vcd->disable_clip, vcd->disable_avx, vcd->enable_transform, vcd->phone_model, vcd->psnr, vcd->ssim, vcd->ms_ssim, vcd->pool, vcd->thread, vcd->subsample);', 1)})
        expect_fail(run_checker(root), 'x265_calculate_vmafscore must initialize score/pix_format and fail fast on invalid format or compute_vmaf() errors before returning a score')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': replace_in_framelevel(
            valid_text(),
            '    x265_log(nullptr, X265_LOG_ERROR, "Invalid format\\n");\n'
            '    return 0.0;\n',
            '',
        )})
        expect_fail(run_checker(root), 'missing x265_calculate_vmaf_framelevelscore failure-propagation guardrail: x265_log(nullptr, X265_LOG_ERROR, "Invalid format\\n");')

    print('VMAF score failure propagation tests passed')


if __name__ == '__main__':
    main()
