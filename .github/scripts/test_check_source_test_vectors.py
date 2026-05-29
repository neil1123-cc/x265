#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


CHECKER = Path(__file__).with_name('check_source_test_vectors.py')


def run_checker(test_dir):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(test_dir)],
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


def write_vectors(test_dir, body):
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / 'smoke-tests.txt').write_text(body, encoding='utf-8')


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_dir = Path(tmp) / 'source' / 'test'
        write_vectors(
            test_dir,
            '# smoke\n'
            'clip.y4m,--preset medium --frames 1\n'
            'clip2.y4m,--pass 1::--pass 2 --bitrate 1000\n',
        )
        expect_pass(run_checker(test_dir))

    with tempfile.TemporaryDirectory() as tmp:
        test_dir = Path(tmp) / 'source' / 'test'
        write_vectors(test_dir, 'clip.y4m --preset medium\n')
        expect_fail(run_checker(test_dir), 'test vector line must contain an input/options comma separator')

    with tempfile.TemporaryDirectory() as tmp:
        test_dir = Path(tmp) / 'source' / 'test'
        write_vectors(test_dir, 'clip.y4m,--preset "unterminated\n')
        expect_fail(run_checker(test_dir), 'test vector options are not shell-parseable')

    with tempfile.TemporaryDirectory() as tmp:
        test_dir = Path(tmp) / 'source' / 'test'
        write_vectors(test_dir, 'clip.y4m,--pass 1::\n')
        expect_fail(run_checker(test_dir), 'test vector stage must not be empty')

    with tempfile.TemporaryDirectory() as tmp:
        test_dir = Path(tmp) / 'source' / 'test'
        write_vectors(test_dir, 'clip.y4m,--preset medium \n')
        expect_fail(run_checker(test_dir), 'source test vector line must not have trailing whitespace')

    print('source/test vector guardrails validated')


if __name__ == '__main__':
    main()
