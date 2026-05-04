#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).with_name('check_compile_commands.py')


def write_compile_commands(build_dir, command, file_path='source/common/common.cpp'):
    write_compile_commands_entries(build_dir, [(command, file_path)])


def write_compile_commands_entries(build_dir, entries):
    build = Path(build_dir)
    build.mkdir(parents=True, exist_ok=True)
    (build / 'compile_commands.json').write_text(json.dumps([
        {
            'directory': str(build),
            'command': command,
            'file': str(build.parent / file_path),
        }
        for command, file_path in entries
    ]))


def write_compile_commands_records(build_dir, records):
    build = Path(build_dir)
    build.mkdir(parents=True, exist_ok=True)
    (build / 'compile_commands.json').write_text(json.dumps(records))


def run_checker(build_dir, *args):
    return subprocess.run(
        [sys.executable, str(CHECKER), str(build_dir), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def ci_shape_records(build_dir, root, overrides=None):
    overrides = overrides or {}
    entries = (
        ('source/common/x86/asm-primitives.cpp', ['-DX265_ARCH_X86=1', '-DX265_DEPTH=8']),
        ('CMakeFiles/common.dir/Unity/unity_0_cxx.cxx', ['-DX265_DEPTH=8']),
        ('source/encoder/api.cpp', ['-DEXPORT_C_API=1', '-DX265_DEPTH=8']),
        ('source/output/output.cpp', ['-DLINKED_8BIT=1', '-DLINKED_12BIT=1', '-DX265_DEPTH=10']),
        ('source/common/winxp.cpp', ['-D_WIN32_WINNT=_WIN32_WINNT_WINXP', '-DX265_DEPTH=8']),
        ('source/common/cpu.cpp', ['-march=znver5', '-DX265_DEPTH=8']),
    )
    records = []
    for file_path, flags in entries:
        override = overrides.get(file_path, {})
        command_flags = override.get('command_flags', flags)
        argument_flags = override.get('argument_flags', flags)
        records.append({
            'directory': str(build_dir),
            'command': f"c++ -std=gnu++20 {' '.join(command_flags)} -c {file_path}",
            'arguments': ['c++', '-std=gnu++20', *argument_flags, '-c', file_path],
            'file': str(root / file_path),
        })
    return records


CI_SHAPE_ARGS = (
    '--min-cpp-commands=6',
    '--required-file-substring=source/common/x86/asm-primitives.cpp',
    '--required-file-substring=CMakeFiles/common.dir/Unity/unity_0_cxx.cxx',
    '--required-file-substring=source/encoder/api.cpp',
    '--required-file-substring=source/output/output.cpp',
    '--required-file-substring=source/common/winxp.cpp',
    '--required-file-substring=source/common/cpu.cpp',
    '--required-file-flag=source/common/x86/asm-primitives.cpp=-DX265_ARCH_X86=1',
    '--required-file-flag=source/common/x86/asm-primitives.cpp=-DX265_DEPTH=8',
    '--required-file-flag=CMakeFiles/common.dir/Unity/unity_0_cxx.cxx=-DX265_DEPTH=8',
    '--required-file-flag=source/encoder/api.cpp=-DEXPORT_C_API=1',
    '--required-file-flag=source/encoder/api.cpp=-DX265_DEPTH=8',
    '--required-file-flag=source/output/output.cpp=-DLINKED_8BIT=1',
    '--required-file-flag=source/output/output.cpp=-DLINKED_12BIT=1',
    '--required-file-flag=source/output/output.cpp=-DX265_DEPTH=10',
    '--required-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WINXP',
    '--required-file-flag=source/common/winxp.cpp=-DX265_DEPTH=8',
    '--required-file-flag=source/common/cpu.cpp=-march=znver5',
    '--required-file-flag=source/common/cpu.cpp=-DX265_DEPTH=8',
    '--forbidden-file-flag=source/common/x86/asm-primitives.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/common/x86/asm-primitives.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=CMakeFiles/common.dir/Unity/unity_0_cxx.cxx=-DX265_DEPTH=10',
    '--forbidden-file-flag=CMakeFiles/common.dir/Unity/unity_0_cxx.cxx=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/encoder/api.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/encoder/api.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/common/winxp.cpp=-D_WIN32_WINNT=_WIN32_WINNT_WIN7',
    '--forbidden-file-flag=source/common/winxp.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/common/winxp.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/common/cpu.cpp=-DX265_DEPTH=10',
    '--forbidden-file-flag=source/common/cpu.cpp=-DX265_DEPTH=12',
    '--forbidden-file-flag=source/output/output.cpp=-DX265_DEPTH=8',
    '--forbidden-file-flag=source/output/output.cpp=-DX265_DEPTH=12',
)


def run_ci_shape_checker(build_dir):
    return run_checker(build_dir, *CI_SHAPE_ARGS)


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
        write_compile_commands(root / 'pass', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp')
        expect_pass(run_checker(root / 'pass', '--required-flag=-Wdeprecated', '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8', '--min-cpp-commands=1', '--required-file-substring=source/common/'))

        missing_commands_dir = root / 'missing-compile-commands'
        missing_commands_dir.mkdir()
        expect_fail(run_checker(missing_commands_dir), 'missing compile_commands.json')

        invalid_json_dir = root / 'invalid-json'
        invalid_json_dir.mkdir()
        (invalid_json_dir / 'compile_commands.json').write_text('{')
        expect_fail(run_checker(invalid_json_dir), 'invalid compile_commands.json')

        object_json_dir = root / 'object-json'
        object_json_dir.mkdir()
        (object_json_dir / 'compile_commands.json').write_text('{}')
        expect_fail(run_checker(object_json_dir), 'compile_commands.json must contain a list')

        missing_file_field_dir = root / 'missing-file-field'
        write_compile_commands_records(missing_file_field_dir, [{
            'directory': str(missing_file_field_dir),
            'command': 'c++ -std=gnu++20 -c source/common/common.cpp',
        }])
        expect_fail(run_checker(missing_file_field_dir), 'compile command entry #1 is missing file field')

        missing_command_fields_dir = root / 'missing-command-fields'
        write_compile_commands_records(missing_command_fields_dir, [{
            'directory': str(missing_command_fields_dir),
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_command_fields_dir), 'compile command entry #1 is missing command or arguments field')

        nonstring_command_dir = root / 'nonstring-command-field'
        write_compile_commands_records(nonstring_command_dir, [{
            'directory': str(nonstring_command_dir),
            'command': ['c++', '-std=gnu++20', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(nonstring_command_dir), 'compile command entry #1 command field must be a string')

        nonlist_arguments_dir = root / 'nonlist-arguments-field'
        write_compile_commands_records(nonlist_arguments_dir, [{
            'directory': str(nonlist_arguments_dir),
            'arguments': 'c++ -std=gnu++20 -c source/common/common.cpp',
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(nonlist_arguments_dir), 'compile command entry #1 arguments field must be a list')

        ci_shape_dir = root / 'ci-shape-dual-field-pass'
        write_compile_commands_records(ci_shape_dir, ci_shape_records(ci_shape_dir, root))
        expect_pass(run_ci_shape_checker(ci_shape_dir))

        asm_shape_missing_dir = root / 'ci-shape-asm-arguments-missing-arch'
        write_compile_commands_records(asm_shape_missing_dir, ci_shape_records(asm_shape_missing_dir, root, {
            'source/common/x86/asm-primitives.cpp': {
                'argument_flags': ['-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(asm_shape_missing_dir), 'missing required flag -DX265_ARCH_X86=1 for file substring source/common/x86/asm-primitives.cpp')

        unity_shape_missing_dir = root / 'ci-shape-unity-command-missing-depth'
        write_compile_commands_records(unity_shape_missing_dir, ci_shape_records(unity_shape_missing_dir, root, {
            'CMakeFiles/common.dir/Unity/unity_0_cxx.cxx': {
                'command_flags': [],
            },
        }))
        expect_fail(run_ci_shape_checker(unity_shape_missing_dir), 'missing required flag -DX265_DEPTH=8 for file substring CMakeFiles/common.dir/Unity/unity_0_cxx.cxx')

        shared_api_missing_dir = root / 'ci-shape-shared-api-command-missing-export'
        write_compile_commands_records(shared_api_missing_dir, ci_shape_records(shared_api_missing_dir, root, {
            'source/encoder/api.cpp': {
                'command_flags': ['-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(shared_api_missing_dir), 'missing required flag -DEXPORT_C_API=1 for file substring source/encoder/api.cpp')

        all_depth_forbidden_dir = root / 'ci-shape-all-bit-depth-arguments-forbidden-depth'
        write_compile_commands_records(all_depth_forbidden_dir, ci_shape_records(all_depth_forbidden_dir, root, {
            'source/output/output.cpp': {
                'argument_flags': ['-DLINKED_8BIT=1', '-DLINKED_12BIT=1', '-DX265_DEPTH=10', '-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(all_depth_forbidden_dir), 'forbidden flag -DX265_DEPTH=8 for file substring source/output/output.cpp')

        winxp_forbidden_dir = root / 'ci-shape-winxp-arguments-forbidden-target'
        write_compile_commands_records(winxp_forbidden_dir, ci_shape_records(winxp_forbidden_dir, root, {
            'source/common/winxp.cpp': {
                'argument_flags': ['-D_WIN32_WINNT=_WIN32_WINNT_WINXP', '-D_WIN32_WINNT=_WIN32_WINNT_WIN7', '-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(winxp_forbidden_dir), 'forbidden flag -D_WIN32_WINNT=_WIN32_WINNT_WIN7 for file substring source/common/winxp.cpp')

        cpu_target_missing_dir = root / 'ci-shape-cpu-target-command-missing-march'
        write_compile_commands_records(cpu_target_missing_dir, ci_shape_records(cpu_target_missing_dir, root, {
            'source/common/cpu.cpp': {
                'command_flags': ['-DX265_DEPTH=8'],
            },
        }))
        expect_fail(run_ci_shape_checker(cpu_target_missing_dir), 'missing required flag -march=znver5 for file substring source/common/cpu.cpp')

        write_compile_commands(root / 'profiling-flags', 'c++ -std=gnu++20 -fprofile-instr-generate -fprofile-update=atomic -c source/common/common.cpp')
        expect_pass(run_checker(root / 'profiling-flags', '--required-flag=-fprofile-instr-generate', '--required-flag=-fprofile-update=atomic'))

        write_compile_commands(root / 'missing-profiling-flag', 'c++ -std=gnu++20 -fprofile-instr-generate -c source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-profiling-flag', '--required-flag=-fprofile-instr-generate', '--required-flag=-fprofile-update=atomic'), 'missing required flag -fprofile-update=atomic')

        profiling_mixed_fields_dir = root / 'profiling-mixed-fields'
        write_compile_commands_records(profiling_mixed_fields_dir, [{
            'directory': str(profiling_mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -fprofile-instr-generate -fprofile-update=atomic -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-fprofile-instr-generate', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(profiling_mixed_fields_dir, '--required-flag=-fprofile-instr-generate', '--required-flag=-fprofile-update=atomic'), 'missing required flag -fprofile-update=atomic')

        write_compile_commands(root / 'pgo-consume-flag', 'c++ -std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata -c source/common/common.cpp')
        expect_pass(run_checker(root / 'pgo-consume-flag', '--required-flag-prefix=-fprofile-instr-use='))

        write_compile_commands(root / 'pgo-consume-missing', 'c++ -std=gnu++20 -fprofile-sample-use=/tmp/x265.profdata -c source/common/common.cpp')
        expect_fail(run_checker(root / 'pgo-consume-missing', '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        write_compile_commands(root / 'pgo-consume-substring', 'c++ -std=gnu++20 -fprofile-instr-use-wrong=/tmp/x265.profdata -c source/common/common.cpp')
        expect_fail(run_checker(root / 'pgo-consume-substring', '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        write_compile_commands(root / 'pgo-consume-generate-leak', 'c++ -std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata -fprofile-instr-generate -fprofile-update=atomic -c source/common/common.cpp')
        expect_fail(run_checker(root / 'pgo-consume-generate-leak', '--required-flag-prefix=-fprofile-instr-use=', '--forbidden-flag=-fprofile-instr-generate', '--forbidden-flag=-fprofile-update=atomic'), 'forbidden flag -fprofile-instr-generate')

        pgo_consume_arguments_leak_dir = root / 'pgo-consume-arguments-generate-leak'
        write_compile_commands_records(pgo_consume_arguments_leak_dir, [{
            'directory': str(pgo_consume_arguments_leak_dir),
            'command': 'c++ -std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-fprofile-instr-use=/tmp/x265.profdata', '-fprofile-update=atomic', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(pgo_consume_arguments_leak_dir, '--required-flag-prefix=-fprofile-instr-use=', '--forbidden-flag=-fprofile-update=atomic'), 'forbidden flag -fprofile-update=atomic')

        pgo_consume_response_dir = root / 'pgo-consume-response-file'
        pgo_consume_response_dir.mkdir()
        (pgo_consume_response_dir / 'pgo.rsp').write_text('-std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata')
        write_compile_commands(pgo_consume_response_dir, 'c++ @pgo.rsp -c source/common/common.cpp')
        expect_pass(run_checker(pgo_consume_response_dir, '--required-flag-prefix=-fprofile-instr-use='))

        pgo_consume_response_missing_dir = root / 'pgo-consume-response-file-missing-prefix'
        pgo_consume_response_missing_dir.mkdir()
        (pgo_consume_response_missing_dir / 'pgo.rsp').write_text('-std=gnu++20 -fprofile-sample-use=/tmp/x265.profdata')
        write_compile_commands(pgo_consume_response_missing_dir, 'c++ @pgo.rsp -c source/common/common.cpp')
        expect_fail(run_checker(pgo_consume_response_missing_dir, '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        pgo_consume_mixed_fields_dir = root / 'pgo-consume-mixed-fields'
        write_compile_commands_records(pgo_consume_mixed_fields_dir, [{
            'directory': str(pgo_consume_mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -fprofile-instr-use=/tmp/x265.profdata -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(pgo_consume_mixed_fields_dir, '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        pgo_consume_command_missing_dir = root / 'pgo-consume-command-missing-prefix'
        write_compile_commands_records(pgo_consume_command_missing_dir, [{
            'directory': str(pgo_consume_command_missing_dir),
            'command': 'c++ -std=gnu++20 -fprofile-sample-use=/tmp/x265.profdata -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-fprofile-instr-use=/tmp/x265.profdata', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(pgo_consume_command_missing_dir, '--required-flag-prefix=-fprofile-instr-use='), 'missing required flag prefix -fprofile-instr-use=')

        write_compile_commands(root / 'pass-msvc-std', 'cl /std:c++20 /c source/common/common.cpp')
        expect_pass(run_checker(root / 'pass-msvc-std', '--min-cpp-commands=1'))

        msvc_arguments_dir = root / 'pass-msvc-arguments'
        write_compile_commands_records(msvc_arguments_dir, [{
            'directory': str(msvc_arguments_dir),
            'arguments': ['clang-cl', '/std:c++20', '/c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(msvc_arguments_dir, '--min-cpp-commands=1'))

        both_fields_dir = root / 'pass-command-arguments-same-std'
        write_compile_commands_records(both_fields_dir, [{
            'directory': str(both_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(both_fields_dir, '--required-flag=-Wdeprecated', '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        missing_argument_flag_dir = root / 'command-arguments-missing-required-flag'
        write_compile_commands_records(missing_argument_flag_dir, [{
            'directory': str(missing_argument_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_argument_flag_dir, '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        missing_command_flag_dir = root / 'command-field-missing-required-flag'
        write_compile_commands_records(missing_command_flag_dir, [{
            'directory': str(missing_command_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_command_flag_dir, '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        forbidden_argument_flag_dir = root / 'command-arguments-forbidden-flag'
        write_compile_commands_records(forbidden_argument_flag_dir, [{
            'directory': str(forbidden_argument_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-Wno-deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(forbidden_argument_flag_dir, '--forbidden-flag-substring=-Wno-deprecated'), 'forbidden flag substring -Wno-deprecated')

        forbidden_command_flag_dir = root / 'command-field-forbidden-flag'
        write_compile_commands_records(forbidden_command_flag_dir, [{
            'directory': str(forbidden_command_flag_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -Wno-deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(forbidden_command_flag_dir, '--forbidden-flag-substring=-Wno-deprecated'), 'forbidden flag substring -Wno-deprecated')

        missing_argument_depth_dir = root / 'command-arguments-missing-depth'
        write_compile_commands_records(missing_argument_depth_dir, [{
            'directory': str(missing_argument_depth_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_argument_depth_dir, '--required-depth-define=-DX265_DEPTH=8'), 'missing -DX265_DEPTH=8')

        missing_command_depth_dir = root / 'command-field-missing-depth'
        write_compile_commands_records(missing_command_depth_dir, [{
            'directory': str(missing_command_depth_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DX265_DEPTH=8', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_command_depth_dir, '--required-depth-define=-DX265_DEPTH=8'), 'missing -DX265_DEPTH=8')

        windows_path_dir = root / 'windows-path-substring'
        write_compile_commands_records(windows_path_dir, [{
            'directory': str(windows_path_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/input/lavf.cpp',
            'file': str(root / 'source\\input\\lavf.cpp'),
        }])
        expect_pass(run_checker(windows_path_dir, '--required-file-substring=source/input/lavf.cpp', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'))

        mixed_fields_dir = root / 'mixed-command-arguments-std'
        write_compile_commands_records(mixed_fields_dir, [{
            'directory': str(mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=c++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(mixed_fields_dir), 'duplicate standard flags -std=c++20,-std=gnu++20')

        mixed_msvc_fields_dir = root / 'mixed-msvc-command-arguments-std'
        write_compile_commands_records(mixed_msvc_fields_dir, [{
            'directory': str(mixed_msvc_fields_dir),
            'command': 'cl /std:c++20 /c source/common/common.cpp',
            'arguments': ['clang-cl', '-std=gnu++20', '/c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(mixed_msvc_fields_dir), 'duplicate standard flags -std=gnu++20,/std:c++20')

        missing_argument_std_dir = root / 'command-arguments-missing-std'
        write_compile_commands_records(missing_argument_std_dir, [{
            'directory': str(missing_argument_std_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_argument_std_dir), 'missing GNU++20 dialect')

        missing_command_std_dir = root / 'command-field-missing-std'
        write_compile_commands_records(missing_command_std_dir, [{
            'directory': str(missing_command_std_dir),
            'command': 'c++ -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(missing_command_std_dir), 'missing GNU++20 dialect')

        arguments_dir = root / 'pass-arguments'
        write_compile_commands_records(arguments_dir, [{
            'directory': str(arguments_dir),
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DX265_DEPTH=8', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(arguments_dir, '--required-flag=-Wdeprecated', '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8', '--min-cpp-commands=1'))

        write_compile_commands(root / 'gnu20-double-dash', 'c++ --std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_pass(run_checker(root / 'gnu20-double-dash', '--min-cpp-commands=1'))

        write_compile_commands(root / 'gnu20-split-std', 'c++ -std gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_pass(run_checker(root / 'gnu20-split-std', '--min-cpp-commands=1'))

        split_std_arguments_dir = root / 'split-std-arguments'
        write_compile_commands_records(split_std_arguments_dir, [{
            'directory': str(split_std_arguments_dir),
            'arguments': ['c++', '--std', 'gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(split_std_arguments_dir, '--min-cpp-commands=1'))

        write_compile_commands(root / 'plain-cxx20-split-std', 'c++ -std c++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'plain-cxx20-split-std'), 'non-GNU C++20 dialect flag -std=c++20')

        write_compile_commands(root / 'old-gnu17-split-std', 'c++ --std gnu++17 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-gnu17-split-std'), 'old standard flag --std=gnu++17')

        write_compile_commands(root / 'plain-cxx20-double-dash', 'c++ --std=c++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'plain-cxx20-double-dash'), 'non-GNU C++20 dialect flag --std=c++20')

        write_compile_commands(root / 'old-gnu17-double-dash', 'c++ --std=gnu++17 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-gnu17-double-dash'), 'old standard flag --std=gnu++17')

        write_compile_commands(root / 'old-gnu', 'c++ -std=gnu++17 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-gnu'), 'old standard flag -std=gnu++17')

        write_compile_commands(root / 'old-gnu2a', 'c++ -std=gnu++2a -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-gnu2a'), 'old standard flag -std=gnu++2a')

        write_compile_commands(root / 'old-cxx2a', 'c++ -std=c++2a -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-cxx2a'), 'old standard flag -std=c++2a')

        write_compile_commands(root / 'plain-cxx20', 'c++ -std=c++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'plain-cxx20'), 'non-GNU C++20 dialect flag -std=c++20')

        write_compile_commands(root / 'mixed-plain-cxx20', 'c++ -std=gnu++20 -std=c++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'mixed-plain-cxx20'), 'duplicate standard flags -std=gnu++20,-std=c++20')

        write_compile_commands(root / 'mixed-old-std', 'c++ -std=gnu++20 -std=gnu++2a -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'mixed-old-std'), 'duplicate standard flags -std=gnu++20,-std=gnu++2a')

        write_compile_commands(root / 'duplicate-gnu20', 'c++ -std=gnu++20 -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'duplicate-gnu20'), 'duplicate standard flags -std=gnu++20,-std=gnu++20')

        write_compile_commands(root / 'old-msvc', 'cl /std:c++17 /c source/common/common.cpp')
        expect_fail(run_checker(root / 'old-msvc'), 'old standard flag /std:c++17')

        write_compile_commands(root / 'missing-std', 'c++ -Wdeprecated -Werror=deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-std'), 'missing GNU++20 dialect')

        write_compile_commands(root / 'missing-flag', 'c++ -std=gnu++20 -Wdeprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-flag', '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        write_compile_commands(root / 'required-flag-substring', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated-extra -c source/common/common.cpp')
        expect_fail(run_checker(root / 'required-flag-substring', '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        write_compile_commands(root / 'forbidden', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -Wno-deprecated -c source/common/common.cpp')
        expect_fail(run_checker(root / 'forbidden', '--forbidden-flag-substring=-Wno-deprecated'), 'forbidden flag substring -Wno-deprecated')

        write_compile_commands(root / 'forbidden-volatile', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -Wno-volatile -c source/common/common.cpp')
        expect_fail(run_checker(root / 'forbidden-volatile', '--forbidden-flag-substring=-Wno-volatile'), 'forbidden flag substring -Wno-volatile')

        write_compile_commands(root / 'forbidden-exact-flag', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=12 -c source/common/common.cpp')
        expect_fail(run_checker(root / 'forbidden-exact-flag', '--forbidden-flag=-DX265_DEPTH=12'), 'forbidden flag -DX265_DEPTH=12')

        write_compile_commands(root / 'forbidden-exact-flag-no-prefix-match', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=12 -c source/common/common.cpp')
        expect_pass(run_checker(root / 'forbidden-exact-flag-no-prefix-match', '--forbidden-flag=-DX265_DEPTH=10'))

        write_compile_commands(root / 'missing-depth', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=10 -c source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-depth', '--required-depth-define=-DX265_DEPTH=12'), 'missing -DX265_DEPTH=12')

        write_compile_commands(root / 'mixed-depth', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -DX265_DEPTH=10 -c source/common/common.cpp')
        expect_fail(run_checker(root / 'mixed-depth', '--required-depth-define=-DX265_DEPTH=8'), 'mixed depth defines -DX265_DEPTH=10')

        mixed_depth_arguments_dir = root / 'mixed-depth-arguments'
        write_compile_commands_records(mixed_depth_arguments_dir, [{
            'directory': str(mixed_depth_arguments_dir),
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DX265_DEPTH=8', '-DX265_DEPTH=12', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(mixed_depth_arguments_dir, '--required-depth-define=-DX265_DEPTH=8'), 'mixed depth defines -DX265_DEPTH=12')

        mixed_depth_fields_dir = root / 'mixed-depth-fields'
        write_compile_commands_records(mixed_depth_fields_dir, [{
            'directory': str(mixed_depth_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DX265_DEPTH=8', '-DX265_DEPTH=10', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(mixed_depth_fields_dir, '--required-depth-define=-DX265_DEPTH=8'), 'mixed depth defines -DX265_DEPTH=10')

        write_compile_commands(root / 'missing-file', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/encoder/api.cpp', 'source/encoder/api.cpp')
        expect_fail(run_checker(root / 'missing-file', '--required-file-substring=source/common/'), 'missing compile command for file substring source/common/')

        write_compile_commands_entries(root / 'forbidden-file-substring', [
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp', 'source/common/common.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/output/mkv.cpp', 'source/output/mkv.cpp'),
        ])
        expect_fail(run_checker(root / 'forbidden-file-substring', '--forbidden-file-substring=source/output/mkv.cpp'), 'forbidden compile command for file substring source/output/mkv.cpp')

        write_compile_commands(root / 'forbidden-windows-file-substring', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/output/mp4.cpp', 'source\\output\\mp4.cpp')
        expect_fail(run_checker(root / 'forbidden-windows-file-substring', '--forbidden-file-substring=source/output/mp4.cpp'), 'forbidden compile command for file substring source/output/mp4.cpp')

        write_compile_commands(root / 'file-flag', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/input/lavf.cpp', 'source/input/lavf.cpp')
        expect_pass(run_checker(root / 'file-flag', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF', '--forbidden-file-flag=source/input/lavf.cpp=-DENABLE_MKV'))

        write_compile_commands(root / 'file-flag-no-prefix-match', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF_EXTRA -c source/input/lavf.cpp', 'source/input/lavf.cpp')
        expect_fail(run_checker(root / 'file-flag-no-prefix-match', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing required flag -DENABLE_LAVF for file substring source/input/lavf.cpp')

        file_flag_mixed_fields_dir = root / 'file-flag-mixed-fields'
        write_compile_commands_records(file_flag_mixed_fields_dir, [{
            'directory': str(file_flag_mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/input/lavf.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/input/lavf.cpp'],
            'file': str(root / 'source/input/lavf.cpp'),
        }])
        expect_fail(run_checker(file_flag_mixed_fields_dir, '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing required flag -DENABLE_LAVF for file substring source/input/lavf.cpp')

        file_forbidden_mixed_fields_dir = root / 'file-forbidden-mixed-fields'
        write_compile_commands_records(file_forbidden_mixed_fields_dir, [{
            'directory': str(file_forbidden_mixed_fields_dir),
            'command': 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-DENABLE_LAVF', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(file_forbidden_mixed_fields_dir, '--forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF'), 'forbidden flag -DENABLE_LAVF for file substring source/common/common.cpp')

        write_compile_commands(root / 'missing-file-flag', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/input/lavf.cpp', 'source/input/lavf.cpp')
        expect_fail(run_checker(root / 'missing-file-flag', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing required flag -DENABLE_LAVF for file substring source/input/lavf.cpp')

        write_compile_commands(root / 'missing-file-flag-match', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/common/common.cpp', 'source/common/common.cpp')
        expect_fail(run_checker(root / 'missing-file-flag-match', '--required-file-flag=source/input/lavf.cpp=-DENABLE_LAVF'), 'missing compile command for file substring source/input/lavf.cpp required by file flag -DENABLE_LAVF')

        write_compile_commands(root / 'forbidden-file-flag', 'c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DENABLE_LAVF -c source/common/common.cpp', 'source/common/common.cpp')
        expect_fail(run_checker(root / 'forbidden-file-flag', '--forbidden-file-flag=source/common/common.cpp=-DENABLE_LAVF'), 'forbidden flag -DENABLE_LAVF for file substring source/common/common.cpp')

        write_compile_commands_entries(root / 'mixed-c-cpp', [
            ('cc -std=c11 -c source/common/pixel.c', 'source/common/pixel.c'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp', 'source/common/common.cpp'),
        ])
        expect_pass(run_checker(root / 'mixed-c-cpp', '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8', '--min-cpp-commands=1'))

        write_compile_commands(root / 'only-c', 'cc -std=c11 -c source/common/pixel.c', 'source/common/pixel.c')
        expect_fail(run_checker(root / 'only-c'), 'no C++ compile commands')

        response_dir = root / 'response-file'
        response_dir.mkdir()
        (response_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands(response_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_pass(run_checker(response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        quoted_response_dir = root / 'quoted-response-file'
        quoted_response_dir.mkdir()
        (quoted_response_dir / 'args file.rsp').write_text('"-std=gnu++20" "-Wdeprecated" "-Werror=deprecated" "-DX265_DEPTH=8"')
        write_compile_commands(quoted_response_dir, 'c++ @"args file.rsp" -c "source/common/common.cpp"')
        expect_pass(run_checker(quoted_response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        quoted_arguments_response_dir = root / 'quoted-response-file-arguments'
        quoted_arguments_response_dir.mkdir()
        (quoted_arguments_response_dir / 'args file.rsp').write_text('"-std=gnu++20" "-Wdeprecated" "-Werror=deprecated" "-DX265_DEPTH=8"')
        write_compile_commands_records(quoted_arguments_response_dir, [{
            'directory': str(quoted_arguments_response_dir),
            'arguments': ['c++', '@args file.rsp', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(quoted_arguments_response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        missing_response_dir = root / 'missing-response-file'
        missing_response_dir.mkdir()
        write_compile_commands(missing_response_dir, 'c++ @missing.rsp -c source/common/common.cpp')
        expect_fail(run_checker(missing_response_dir), 'missing GNU++20 dialect')

        uppercase_suffix_dir = root / 'uppercase-cpp-suffix'
        write_compile_commands_records(uppercase_suffix_dir, [{
            'directory': str(uppercase_suffix_dir),
            'arguments': ['c++', '-std=gnu++20', '-Wdeprecated', '-Werror=deprecated', '-c', 'source/common/COMMON.CPP'],
            'file': str(root / 'source/common/COMMON.CPP'),
        }])
        expect_pass(run_checker(uppercase_suffix_dir, '--required-flag=-Werror=deprecated', '--min-cpp-commands=1'))

        nested_response_dir = root / 'nested-response-file'
        nested_response_dir.mkdir()
        (nested_response_dir / 'std.rsp').write_text('-std=gnu++20 -Wdeprecated')
        (nested_response_dir / 'args.rsp').write_text('@std.rsp -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands(nested_response_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_pass(run_checker(nested_response_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        nested_arguments_dir = root / 'nested-response-file-arguments'
        nested_arguments_dir.mkdir()
        (nested_arguments_dir / 'std.rsp').write_text('-std=gnu++20 -Wdeprecated')
        (nested_arguments_dir / 'args.rsp').write_text('@std.rsp -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands_records(nested_arguments_dir, [{
            'directory': str(nested_arguments_dir),
            'arguments': ['c++', '@args.rsp', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_pass(run_checker(nested_arguments_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'))

        response_mixed_fields_dir = root / 'response-file-mixed-fields'
        response_mixed_fields_dir.mkdir()
        (response_mixed_fields_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8')
        write_compile_commands_records(response_mixed_fields_dir, [{
            'directory': str(response_mixed_fields_dir),
            'command': 'c++ @args.rsp -c source/common/common.cpp',
            'arguments': ['c++', '-std=gnu++20', '-c', 'source/common/common.cpp'],
            'file': str(root / 'source/common/common.cpp'),
        }])
        expect_fail(run_checker(response_mixed_fields_dir, '--required-flag=-Werror=deprecated', '--required-depth-define=-DX265_DEPTH=8'), 'missing required flag -Werror=deprecated')

        response_missing_flag_dir = root / 'response-file-missing-required-flag'
        response_missing_flag_dir.mkdir()
        (response_missing_flag_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated')
        write_compile_commands(response_missing_flag_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_fail(run_checker(response_missing_flag_dir, '--required-flag=-Werror=deprecated'), 'missing required flag -Werror=deprecated')

        response_forbidden_flag_dir = root / 'response-file-forbidden-flag'
        response_forbidden_flag_dir.mkdir()
        (response_forbidden_flag_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -Wno-volatile')
        write_compile_commands(response_forbidden_flag_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_fail(run_checker(response_forbidden_flag_dir, '--forbidden-flag-substring=-Wno-volatile'), 'forbidden flag substring -Wno-volatile')

        response_mixed_depth_dir = root / 'response-file-mixed-depth'
        response_mixed_depth_dir.mkdir()
        (response_mixed_depth_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -DX265_DEPTH=10')
        write_compile_commands(response_mixed_depth_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_fail(run_checker(response_mixed_depth_dir, '--required-depth-define=-DX265_DEPTH=8'), 'mixed depth defines -DX265_DEPTH=10')

        response_cycle_dir = root / 'response-file-cycle'
        response_cycle_dir.mkdir()
        (response_cycle_dir / 'args.rsp').write_text('-std=gnu++20 -Wdeprecated -Werror=deprecated @args.rsp')
        write_compile_commands(response_cycle_dir, 'c++ @args.rsp -c source/common/common.cpp')
        expect_pass(run_checker(response_cycle_dir, '--required-flag=-Werror=deprecated'))

        write_compile_commands_entries(root / 'depth-exclude', [
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -c source/dynamicHDR10/json11.cpp', 'source/dynamicHDR10/json11.cpp'),
            ('c++ -std=gnu++20 -Wdeprecated -Werror=deprecated -DX265_DEPTH=8 -c source/common/common.cpp', 'source/common/common.cpp'),
        ])
        expect_pass(run_checker(root / 'depth-exclude', '--required-depth-define=-DX265_DEPTH=8', '--depth-exclude-path=dynamicHDR10/'))

        expect_fail(run_checker(root / 'pass', '--min-cpp-commands=2'), 'expected at least 2 C++ compile commands')

    print('compile command guardrails validated')


if __name__ == '__main__':
    main()
