#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_picture_read_failure.py')


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
                    'err = vmaf_read_pictures(vmaf, &pic_ref, &pic_dist, picture_index);',
                    'if (err) {',
                    '    printf("problem reading pictures\\n");',
                    '    goto free_data;',
                    '}',
                    'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'err = vmaf_read_pictures(vmaf, &pic_ref, &pic_dist, picture_index);',
                    'if (err) {',
                    '    printf("problem reading pictures\\n");',
                    '            break;',
                    '}',
                    'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'forbidden VMAF picture-read failure regression: printf("problem reading pictures\\n");\n            break;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'err = vmaf_read_pictures(vmaf, &pic_ref, &pic_dist, picture_index);',
                    'if (err) {',
                    '    printf("problem reading pictures\\n");',
                    '}',
                    'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'missing VMAF picture-read failure guardrail: goto free_data;')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/api.cpp': '\n'.join((
                    'err = vmaf_read_pictures(vmaf, &pic_ref, &pic_dist, picture_index);',
                    'if (err) {',
                    '    printf("problem reading pictures\\n");',
                    '}',
                    'err = vmaf_read_pictures(vmaf, nullptr, nullptr, 0);',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'VMAF compute path must abort before flush/scoring when vmaf_read_pictures fails')

    print('VMAF picture-read failure tests passed')


if __name__ == '__main__':
    main()
