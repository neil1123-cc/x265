#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_vmaf_file_cleanup_state.py')


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
                'source/x265cli.cpp': '\n'.join((
                    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after open failure");',
                    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after open failure");',
                    'closeVmafInputFile(param, vmafData->reference_file, "reference", "after output open failure");',
                    'closeVmafInputFile(param, vmafData->distorted_file, "distorted", "after output open failure");',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(root, {'source/x265cli.cpp': 'fclose(vmafData->reference_file);\n'})
        expect_fail(run_checker(root), 'missing VMAF cleanup guardrail: closeVmafInputFile(param, vmafData->reference_file, "reference", "after open failure");')

    print('VMAF cleanup-state guard tests passed')


if __name__ == '__main__':
    main()
