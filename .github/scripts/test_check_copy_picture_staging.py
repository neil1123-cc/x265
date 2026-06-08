#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_copy_picture_staging.py')

# Coverage probes used by the scan for copyPicture staging guardrails.
NORMALIZED_PROBES = (
    'forbidden copyPicture staging regression: ',
    'missing copyPicture staging guardrail: ',
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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'if (!copyDupPictureSideData(dest, src, m_param))',
                    '    return false;',
                    'char* base = (char*)dest->planes[0];',
                    'dest->pts = src->pts;',
                )) + '\n',
            },
        )
        expect_pass(run_checker(root))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_targets(
            root,
            {
                'source/encoder/encoder.cpp': '\n'.join((
                    'char* base = (char*)dest->planes[0];',
                    'dest->pts = src->pts;',
                    'dest->format = 0;',
                    '',
                    'if (!copyDupPictureSideData(dest, src, m_param))',
                    '    return false;',
                )) + '\n',
            },
        )
        expect_fail(run_checker(root), 'copyPicture must copy side-data before mutating dest planes and headers')

    print('copyPicture staging tests passed')


if __name__ == '__main__':
    main()
