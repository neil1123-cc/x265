#!/usr/bin/env python3
import argparse
import shlex
from pathlib import Path


HARNESS_LISTS = {
    'alpha.txt',
    'multiview.txt',
    'rate-control-tests.txt',
    'regression-tests.txt',
    'save-load-tests.txt',
    'scc.txt',
    'smoke-tests.txt',
}

PLAIN_TEXT_LISTS = {
    'CMakeLists.txt',
}


class TestVectorError(Exception):
    def __init__(self, message, path=None, line=None):
        super().__init__(message)
        self.message = message
        self.path = path
        self.line = line


def fail(message, path=None, line=None):
    raise TestVectorError(message, path, line)


def report_failure(exc):
    if exc.path is not None:
        location = f' file={exc.path.as_posix()}'
        if exc.line is not None:
            location += f',line={exc.line}'
        print(f'::error{location}::{exc.message}')
        raise SystemExit(f'{exc.message}: {exc.path.as_posix()}')
    print(f'::error::{exc.message}')
    raise SystemExit(exc.message)


def split_test_line(line, path, line_number):
    if ',' not in line:
        fail('test vector line must contain an input/options comma separator', path, line_number)
    input_name, command = line.split(',', 1)
    input_name = input_name.strip()
    command = command.strip()
    if not input_name:
        fail('test vector input name must not be empty', path, line_number)
    if not command:
        fail('test vector options must not be empty', path, line_number)
    return input_name, command


def validate_stage(stage, path, line_number):
    stage = stage.strip()
    if not stage:
        fail('test vector stage must not be empty', path, line_number)
    try:
        tokens = shlex.split(stage, posix=True)
    except ValueError as exc:
        fail(f'test vector options are not shell-parseable: {exc}', path, line_number)
    if not tokens:
        fail('test vector options must contain at least one token', path, line_number)
    return tokens


def validate_harness_list(path):
    text = path.read_text(encoding='utf-8')
    if not text.strip():
        fail('source test vector file must not be empty', path)
    if '\r' in text:
        fail('source test vector file must use LF line endings', path)

    active_count = 0
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if raw_line.rstrip(' \t') != raw_line:
            fail('source test vector line must not have trailing whitespace', path, line_number)
        if '\t' in raw_line:
            fail('source test vector line must not contain tabs', path, line_number)

        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue

        active_count += 1
        input_name, command = split_test_line(line, path, line_number)
        if input_name.startswith('-'):
            fail('test vector input name must look like an input asset, not an option', path, line_number)
        for stage in command.split('::'):
            validate_stage(stage, path, line_number)

    if active_count == 0:
        fail('source test vector file must contain at least one active test vector', path)
    return active_count


def validate_plain_text(path):
    text = path.read_text(encoding='utf-8')
    if not text.strip():
        fail('source test text file must not be empty', path)
    if '\r' in text:
        fail('source test text file must use LF line endings', path)
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if raw_line.rstrip(' \t') != raw_line:
            fail('source test text line must not have trailing whitespace', path, line_number)
        if '\t' in raw_line:
            fail('source test text line must not contain tabs', path, line_number)


def main():
    parser = argparse.ArgumentParser(description='Validate source/test/*.txt harness vector files')
    parser.add_argument('test_dir', nargs='?', type=Path, default=Path('source/test'))
    args = parser.parse_args()

    test_dir = args.test_dir
    if not test_dir.is_dir():
        fail('source test directory does not exist', test_dir)

    txt_files = sorted(test_dir.glob('*.txt'))
    if not txt_files:
        fail('source test directory has no .txt files', test_dir)

    total_vectors = 0
    for path in txt_files:
        if path.name in HARNESS_LISTS:
            count = validate_harness_list(path)
            total_vectors += count
            print(f'{path.as_posix()}: {count} active vectors')
        elif path.name in PLAIN_TEXT_LISTS:
            validate_plain_text(path)
            print(f'{path.as_posix()}: plain text validated')
        else:
            fail(
                f'unknown source test text file; classify it in HARNESS_LISTS or PLAIN_TEXT_LISTS: {path.name}',
                path,
            )

    print(f'source/test vector files validated: {len(txt_files)} files, {total_vectors} active vectors')


if __name__ == '__main__':
    try:
        main()
    except TestVectorError as exc:
        report_failure(exc)
