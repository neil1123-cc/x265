#!/usr/bin/env python3
import argparse
from pathlib import Path


TARGET = Path('source/encoder/api.cpp')


def check_repo(repo_root):
    repo_root = Path(repo_root)
    path = repo_root / TARGET
    if not path.is_file():
        return [(TARGET.as_posix(), 0, 'missing file')]

    text = path.read_text(encoding='utf-8', errors='ignore')
    failures = []
    required = (
        'float *ref_data = new (std::nothrow) float[totalValues];',
        'float *main_data = new (std::nothrow) float[totalValues];',
        'float *temp_data = new (std::nothrow) float[totalValues];',
        'free_data:',
        'delete[] ref_data;',
        'delete[] main_data;',
        'delete[] temp_data;',
        'printf("problem loading model file: %s\\n", model_path);',
        'printf("problem loading feature extractors from model file: %s\\n", model_path);',
        'err = load_feature(vmaf, "psnr", d);',
        'err = load_feature(vmaf, "float_ssim", nullptr);',
        'err = load_feature(vmaf, "float_ms_ssim", nullptr);',
    )
    for snippet in required:
        if snippet not in text:
            failures.append((TARGET.as_posix(), 0, f'missing VMAF temp-buffer cleanup guardrail: {snippet}'))

    forbidden = (
        'printf("problem loading model file: %s\\n", model_path);\n\t\tgoto end;',
        'printf("problem loading feature extractors from model file: %s\\n", model_path);\n\t\tgoto end;',
        'err = load_feature(vmaf, "psnr", d);\n\t\tif (err) goto end;',
        'err = load_feature(vmaf, "float_ssim", nullptr);\n\t\tif (err) goto end;',
        'err = load_feature(vmaf, "float_ms_ssim", nullptr);\n\t\tif (err) goto end;',
    )
    for snippet in forbidden:
        if snippet in text:
            failures.append((TARGET.as_posix(), 0, f'forbidden VMAF temp-buffer cleanup regression: {snippet.splitlines()[-1]}'))

    model_log_pos = text.find('printf("problem loading model file: %s\\n", model_path);')
    model_free_pos = text.find('goto free_data;', model_log_pos if model_log_pos != -1 else 0)
    feature_log_pos = text.find('printf("problem loading feature extractors from model file: %s\\n", model_path);', model_free_pos if model_free_pos != -1 else 0)
    feature_free_pos = text.find('goto free_data;', feature_log_pos if feature_log_pos != -1 else 0)
    psnr_pos = text.find('err = load_feature(vmaf, "psnr", d);', feature_free_pos if feature_free_pos != -1 else 0)
    psnr_free_pos = text.find('if (err) goto free_data;', psnr_pos if psnr_pos != -1 else 0)
    ssim_pos = text.find('err = load_feature(vmaf, "float_ssim", nullptr);', psnr_free_pos if psnr_free_pos != -1 else 0)
    ssim_free_pos = text.find('if (err) goto free_data;', ssim_pos if ssim_pos != -1 else 0)
    ms_ssim_pos = text.find('err = load_feature(vmaf, "float_ms_ssim", nullptr);', ssim_free_pos if ssim_free_pos != -1 else 0)
    ms_ssim_free_pos = text.find('if (err) goto free_data;', ms_ssim_pos if ms_ssim_pos != -1 else 0)
    cleanup_pos = text.find('free_data:', ms_ssim_free_pos if ms_ssim_free_pos != -1 else 0)
    if -1 in (model_log_pos, model_free_pos, feature_log_pos, feature_free_pos, psnr_pos, psnr_free_pos, ssim_pos, ssim_free_pos, ms_ssim_pos, ms_ssim_free_pos, cleanup_pos) or not (
        model_log_pos < model_free_pos < feature_log_pos < feature_free_pos < psnr_pos < psnr_free_pos < ssim_pos < ssim_free_pos < ms_ssim_pos < ms_ssim_free_pos < cleanup_pos
    ):
        failures.append((TARGET.as_posix(), 0, 'compute_vmaf must route model and feature setup failures through free_data before leaving the function'))

    return failures


def main():
    parser = argparse.ArgumentParser(description='Check VMAF temp buffer cleanup')
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

    print('VMAF temp buffer cleanup validated')


if __name__ == '__main__':
    main()
