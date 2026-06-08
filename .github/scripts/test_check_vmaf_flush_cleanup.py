#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_flush_cleanup.py')


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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);',
                    'if (err) {',
                    'printf("problem flushing context\\n");',
                    '\tgoto free_data;',
                    '}',
                    'free_data:',
                    'delete[] ref_data;',
                    'delete[] main_data;',
                    'delete[] temp_data;',
                    'end:',
                    'vmaf_model_destroy(model);',
                    'vmaf_model_collection_destroy(model_collection);',
                    'vmaf_close(vmaf);',
                    'return err;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': 'printf("problem flushing context\\n");\n\t\treturn err;\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden VMAF flush cleanup regression: printf("problem flushing context\\n");\n\t\treturn err;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);',
                    'if (err) {',
                    'printf("problem flushing context\\n");',
                    '}',
                    'free_data:',
                    'delete[] ref_data;',
                    'delete[] main_data;',
                    'delete[] temp_data;',
                    'end:',
                    'vmaf_model_destroy(model);',
                    'vmaf_model_collection_destroy(model_collection);',
                    'vmaf_close(vmaf);',
                    'return err;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing VMAF flush cleanup guardrail: goto free_data;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);',
                    'if (err) {',
                    'printf("problem flushing context\\n");',
                    '\tgoto free_data;',
                    '}',
                    'end:',
                    'vmaf_model_destroy(model);',
                    'vmaf_model_collection_destroy(model_collection);',
                    'vmaf_close(vmaf);',
                    'free_data:',
                    'delete[] ref_data;',
                    'delete[] main_data;',
                    'delete[] temp_data;',
                    'return err;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF flush failure must flow through free_data before the final model and context teardown')

    print('VMAF flush cleanup tests passed')


if __name__ == '__main__':
    main()
