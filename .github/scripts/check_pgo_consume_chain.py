#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from ci_guard_script_runner import run_python_script_main

SCRIPT_DIR = Path(__file__).resolve().parent
METADATA_CHECKER = SCRIPT_DIR / 'check_profdata_metadata.py'
COMPILE_COMMANDS_CHECKER = SCRIPT_DIR / 'check_compile_commands.py'
PGO_GENERATE_FLAGS = ('-fprofile-instr-generate', '-fprofile-update=atomic')
PGO_CONFLICTING_CONSUME_FLAG_SUBSTRINGS = ('-fprofile-sample-use', '-fprofile-use')
PGO_FORBIDDEN_CONSUME_FLAGS = ('/std:c++20',)


def fail(message):
    raise SystemExit(message)


def check_nonempty_file(path, label):
    if not path.is_file() or path.stat().st_size == 0:
        fail(f'missing {label}: {path}')


def run_checker(label, command):
    result = run_python_checker(command)
    if result.stdout:
        print(result.stdout, end='' if result.stdout.endswith('\n') else '\n')
    if result.returncode != 0:
        fail(f'{label} failed')


def run_python_checker(command):
    script = Path(command[1]).resolve()
    if script not in (METADATA_CHECKER.resolve(), COMPILE_COMMANDS_CHECKER.resolve()):
        fail(f'unsupported checker command: {command}')
    return run_python_script_main(script, command[2:], module_name=f'_pgo_chain_{script.stem}')


def main():
    parser = argparse.ArgumentParser(description='Check x265 PGO metadata, profdata, and consume compile commands')
    parser.add_argument('--metadata', required=True, type=Path)
    parser.add_argument('--profdata', required=True, type=Path)
    parser.add_argument('--build-dir', required=True, type=Path)
    parser.add_argument('--expected-cpu')
    parser.add_argument('--expected-target', required=True)
    parser.add_argument('--expected-branch', required=True)
    parser.add_argument('--expected-toolchain')
    parser.add_argument('--current-toolchain')
    parser.add_argument('--current-commit')
    parser.add_argument('--required-ffmpeg-cache-suffix')
    parser.add_argument('--required-obuparse-cache-suffix')
    parser.add_argument('--required-lsmash-cache-suffix')
    parser.add_argument('--required-gop-muxer-cache-suffix')
    parser.add_argument('--require-dependency-fields', action='store_true')
    parser.add_argument('--require-fresh-slot', action='store_true')
    parser.add_argument('--min-cpp-commands', type=int)
    parser.add_argument('--profdata-flag-path')
    args = parser.parse_args()

    check_nonempty_file(args.metadata, 'PGO metadata')
    check_nonempty_file(args.profdata, 'PGO profdata')

    metadata_args = [
        sys.executable,
        str(METADATA_CHECKER),
        str(args.metadata),
        f'--expected-target={args.expected_target}',
        f'--expected-branch={args.expected_branch}',
    ]
    if args.expected_cpu:
        metadata_args.append(f'--expected-cpu={args.expected_cpu}')
    if args.expected_toolchain:
        metadata_args.append(f'--expected-toolchain={args.expected_toolchain}')
    if args.current_toolchain:
        metadata_args.append(f'--current-toolchain={args.current_toolchain}')
    if args.current_commit:
        metadata_args.append(f'--current-commit={args.current_commit}')
    if args.required_ffmpeg_cache_suffix:
        metadata_args.append(f'--required-ffmpeg-cache-suffix={args.required_ffmpeg_cache_suffix}')
    if args.required_obuparse_cache_suffix:
        metadata_args.append(f'--required-obuparse-cache-suffix={args.required_obuparse_cache_suffix}')
    if args.required_lsmash_cache_suffix:
        metadata_args.append(f'--required-lsmash-cache-suffix={args.required_lsmash_cache_suffix}')
    if args.required_gop_muxer_cache_suffix:
        metadata_args.append(f'--required-gop-muxer-cache-suffix={args.required_gop_muxer_cache_suffix}')
    if args.require_dependency_fields:
        metadata_args.append('--require-dependency-fields')
    if args.require_fresh_slot:
        metadata_args.append('--require-fresh-slot')
    run_checker('PGO metadata check', metadata_args)

    profdata_flag_path = args.profdata_flag_path or args.profdata.as_posix()
    consume_flag = f'-fprofile-instr-use={profdata_flag_path}'
    compile_args = [
        sys.executable,
        str(COMPILE_COMMANDS_CHECKER),
        str(args.build_dir),
        f'--required-flag={consume_flag}',
    ]
    for flag in PGO_GENERATE_FLAGS:
        compile_args.append(f'--forbidden-flag={flag}')
    for flag_substring in PGO_CONFLICTING_CONSUME_FLAG_SUBSTRINGS:
        compile_args.append(f'--forbidden-flag-substring={flag_substring}')
    for flag in PGO_FORBIDDEN_CONSUME_FLAGS:
        compile_args.append(f'--forbidden-flag={flag}')
    if args.min_cpp_commands is not None:
        compile_args.append(f'--min-cpp-commands={args.min_cpp_commands}')
    run_checker('PGO consume compile command check', compile_args)

    print(f'Validated PGO metadata/consume chain: metadata={args.metadata} profdata={args.profdata} build_dir={args.build_dir} consume_flag={consume_flag}')


if __name__ == '__main__':
    main()
