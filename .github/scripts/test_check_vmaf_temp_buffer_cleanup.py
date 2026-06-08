#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_temp_buffer_cleanup.py')


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


def valid_text():
    return '\n'.join((
        'float *ref_data = new (std::nothrow) float[totalValues];',
        'float *main_data = new (std::nothrow) float[totalValues];',
        'float *temp_data = new (std::nothrow) float[totalValues];',
        'printf("problem loading model file: %s\\n", model_path);',
        '\t\tgoto free_data;',
        'printf("problem loading feature extractors from model file: %s\\n", model_path);',
        '\t\tgoto free_data;',
        'err = load_feature(vmaf, "psnr", d);',
        '\t\tif (err) goto free_data;',
        'err = load_feature(vmaf, "float_ssim", nullptr);',
        '\t\tif (err) goto free_data;',
        'err = load_feature(vmaf, "float_ms_ssim", nullptr);',
        '\t\tif (err) goto free_data;',
        'free_data:',
        'delete[] ref_data;',
        'delete[] main_data;',
        'delete[] temp_data;',
    )) + '\n'


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text()})
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text().replace('\t\tgoto free_data;', '\t\tgoto end;', 1)})
        expect_fail(run_checker(root), 'forbidden VMAF temp-buffer cleanup regression: \t\tgoto end;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text().replace('\t\tif (err) goto free_data;', '\t\tif (err) goto end;', 1)})
        expect_fail(run_checker(root), 'compute_vmaf must route model and feature setup failures through free_data before leaving the function')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/encoder/api.cpp': valid_text().replace('delete[] temp_data;', '', 1)})
        expect_fail(run_checker(root), 'missing VMAF temp-buffer cleanup guardrail: delete[] temp_data;')

    print('VMAF temp-buffer cleanup tests passed')


if __name__ == '__main__':
    main()
